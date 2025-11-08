"""
Blockchain Validator
Валидация конфигурации блокчейнов и whale мониторинга

Проверяет:
- Наличие включенных блокчейнов
- Корректность whale thresholds для каждой сети
- Логичность порогов (mega_whale > whale > min_usd)
- Наличие эксплореров и метаданных
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

from .base_validator import BaseValidator

if TYPE_CHECKING:
    from .. import Config

logger = logging.getLogger(__name__)


class BlockchainValidator(BaseValidator):
    """
    Валидатор конфигурации блокчейнов
    
    Выполняет комплексную проверку настроек блокчейнов:
    - Список включенных сетей
    - Пороги для классификации транзакций
    - Наличие необходимых метаданных
    - Корректность значений порогов
    """
    
    def validate(self) -> list:
        """
        Выполнить валидацию блокчейнов
        
        Returns:
            Список всех сообщений валидации
        """
        logger.debug("Запуск валидации блокчейнов...")
        
        # Очистка предыдущих результатов
        self.clear_messages()
        
        # Проверка наличия включенных chains
        if not self._validate_enabled_chains():
            # Если нет включенных chains, дальнейшая валидация бессмысленна
            return self.get_all_messages()
        
        # Проверка каждого включенного блокчейна
        for chain in self.config.blockchain.enabled_chains:
            self._validate_single_blockchain(chain)
        
        # Проверка глобальных настроек
        self._validate_global_settings()
        
        logger.debug(f"Валидация блокчейнов завершена: {len(self.errors)} ошибок, {len(self.warnings)} предупреждений")
        
        return self.get_all_messages()
    
    def _validate_enabled_chains(self) -> bool:
        """
        Проверка списка включенных блокчейнов
        
        Returns:
            True если есть хотя бы один включенный блокчейн
        """
        enabled_count = len(self.config.blockchain.enabled_chains)
        
        if enabled_count == 0:
            self._add_error(
                "Нет включенных блокчейнов для мониторинга. "
                "Whale мониторинг будет полностью отключен. "
                "Установите переменную окружения ENABLED_CHAINS"
            )
            return False
        
        # Успешное сообщение
        chains_list = ', '.join(self.config.blockchain.enabled_chains)
        self._add_info(
            f"Включено блокчейнов: {enabled_count} ({chains_list})"
        )
        
        # Проверка что все включенные chains поддерживаются
        supported_chains = self.config.blockchain.get_all_supported_chains()
        for chain in self.config.blockchain.enabled_chains:
            if chain not in supported_chains:
                self._add_warning(
                    f"Блокчейн '{chain}' включен, но не поддерживается системой. "
                    f"Поддерживаемые: {', '.join(supported_chains)}"
                )
        
        return True
    
    def _validate_single_blockchain(self, chain: str) -> None:
        """
        Валидация конфигурации одного блокчейна
        
        Args:
            chain: Название блокчейна для проверки
        """
        logger.debug(f"Валидация блокчейна: {chain}")
        
        # Получение thresholds для блокчейна
        thresholds = self.config.blockchain.get_whale_threshold(chain)
        
        # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ:
        # Используем ПРАВИЛЬНЫЕ ключи из blockchain_config.py
        required_keys = [
            'min_native_value',           # Минимум нативной валюты
            'min_usd_value',              # Минимум в USD
            'whale_threshold_usd',        # ✅ НЕ 'whale'!
            'mega_whale_threshold_usd'    # ✅ НЕ 'mega_whale'!
        ]
        
        # Проверка наличия всех необходимых ключей
        missing_keys = [key for key in required_keys if key not in thresholds]
        if missing_keys:
            self._add_error(
                f"Блокчейн '{chain}': отсутствуют обязательные ключи в thresholds: "
                f"{', '.join(missing_keys)}. "
                f"Доступные ключи: {', '.join(thresholds.keys())}"
            )
            return  # Нет смысла продолжать без ключей
        
        # Извлечение значений для удобства
        whale_threshold = thresholds['whale_threshold_usd']
        mega_whale_threshold = thresholds['mega_whale_threshold_usd']
        min_usd = thresholds['min_usd_value']
        min_native = thresholds['min_native_value']
        
        # Валидация каждого порога
        self._validate_threshold_value(chain, 'whale_threshold_usd', whale_threshold)
        self._validate_threshold_value(chain, 'mega_whale_threshold_usd', mega_whale_threshold)
        self._validate_threshold_value(chain, 'min_usd_value', min_usd)
        self._validate_threshold_value(chain, 'min_native_value', min_native)
        
        # Проверка логической связи между порогами
        self._validate_threshold_hierarchy(chain, min_usd, whale_threshold, mega_whale_threshold)
        
        # Проверка метаданных блокчейна
        self._validate_chain_metadata(chain)
    
    def _validate_threshold_value(
        self,
        chain: str,
        threshold_name: str,
        value: float
    ) -> bool:
        """
        Валидация значения одного порога
        
        Args:
            chain: Название блокчейна
            threshold_name: Название порога
            value: Значение для проверки
            
        Returns:
            True если значение валидно
        """
        if value <= 0:
            self._add_error(
                f"Блокчейн '{chain}': {threshold_name} должен быть > 0. "
                f"Текущее значение: {value}"
            )
            return False
        
        # Предупреждения о подозрительных значениях
        if threshold_name == 'min_usd_value' and value < 1000:
            self._add_warning(
                f"Блокчейн '{chain}': {threshold_name} очень мал (${value}). "
                f"Рекомендуется минимум $1,000"
            )
        
        if threshold_name == 'whale_threshold_usd' and value < 100000:
            self._add_warning(
                f"Блокчейн '{chain}': {threshold_name} ниже стандартного (${value}). "
                f"Типичное значение: $100,000+"
            )
        
        return True
    
    def _validate_threshold_hierarchy(
        self,
        chain: str,
        min_usd: float,
        whale_threshold: float,
        mega_whale_threshold: float
    ) -> None:
        """
        Валидация иерархии порогов
        
        Проверяет что: min_usd <= whale_threshold < mega_whale_threshold
        
        Args:
            chain: Название блокчейна
            min_usd: Минимальный порог
            whale_threshold: Порог whale
            mega_whale_threshold: Порог mega whale
        """
        # Проверка: mega_whale > whale
        if mega_whale_threshold <= whale_threshold:
            self._add_error(
                f"Блокчейн '{chain}': mega_whale_threshold (${mega_whale_threshold:,.0f}) "
                f"должен быть больше whale_threshold (${whale_threshold:,.0f})"
            )
        
        # Проверка: whale >= min_usd (с предупреждением если меньше)
        if whale_threshold < min_usd:
            self._add_warning(
                f"Блокчейн '{chain}': whale_threshold (${whale_threshold:,.0f}) "
                f"меньше min_usd_value (${min_usd:,.0f}). "
                f"Это нестандартная конфигурация"
            )
        
        # Проверка: min_usd не слишком велик
        if min_usd > whale_threshold:
            self._add_warning(
                f"Блокчейн '{chain}': min_usd_value (${min_usd:,.0f}) "
                f"больше whale_threshold (${whale_threshold:,.0f}). "
                f"Это приведет к пропуску whale транзакций"
            )
        
        # Проверка разумности соотношения mega/whale
        if mega_whale_threshold < whale_threshold * 5:
            self._add_warning(
                f"Блокчейн '{chain}': mega_whale_threshold слишком близок к whale_threshold. "
                f"Рекомендуется соотношение минимум 10:1"
            )
    
    def _validate_chain_metadata(self, chain: str) -> None:
        """
        Валидация метаданных блокчейна
        
        Args:
            chain: Название блокчейна
        """
        # Проверка наличия эксплорера
        explorer_url = self.config.blockchain.get_explorer_url(chain)
        if not explorer_url:
            self._add_error(
                f"Блокчейн '{chain}': отсутствует URL эксплорера. "
                f"Ссылки на транзакции будут недоступны"
            )
        elif not self._validate_url(explorer_url, f"Explorer для {chain}", require_https=True):
            pass  # Ошибка уже добавлена в _validate_url
        
        # Проверка символа нативной валюты
        symbol = self.config.blockchain.get_chain_symbol(chain)
        if symbol == 'UNKNOWN':
            self._add_warning(
                f"Блокчейн '{chain}': не определен символ нативной валюты"
            )
        
        # Проверка полного имени
        name = self.config.blockchain.get_chain_name(chain)
        if not name or name == chain.capitalize():
            self._add_warning(
                f"Блокчейн '{chain}': использует дефолтное имя. "
                f"Рекомендуется задать полное название"
            )
        
        # Проверка emoji
        emoji = self.config.blockchain.get_chain_emoji(chain)
        if emoji == '⛓️':  # Дефолтный emoji
            self._add_warning(
                f"Блокчейн '{chain}': использует дефолтный emoji"
            )
        
        # Проверка цвета
        color = self.config.blockchain.get_chain_color(chain)
        if color == '#000000':  # Дефолтный черный
            self._add_warning(
                f"Блокчейн '{chain}': использует дефолтный цвет"
            )
    
    def _validate_global_settings(self) -> None:
        """Валидация глобальных настроек блокчейнов"""
        # Проверка глобального min_usd
        if hasattr(self.config.blockchain, 'min_usd'):
            global_min_usd = self.config.blockchain.min_usd
            
            if not self._validate_positive(global_min_usd, "Глобальный MIN_USD", allow_zero=False):
                pass  # Ошибка уже добавлена
            
            if global_min_usd < 10000:
                self._add_warning(
                    f"Глобальный MIN_USD очень мал (${global_min_usd:,.0f}). "
                    f"Рекомендуется минимум $10,000 для фильтрации шума"
                )
            
            self._add_info(f"Глобальный MIN_USD: ${global_min_usd:,.0f}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получить сводку валидации блокчейнов
        
        Returns:
            Словарь со статистикой валидации
        """
        return {
            'total_enabled': len(self.config.blockchain.enabled_chains),
            'total_supported': len(self.config.blockchain.get_all_supported_chains()),
            'has_errors': self.has_errors(),
            'has_warnings': self.has_warnings(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'validated_chains': self.config.blockchain.enabled_chains
        }