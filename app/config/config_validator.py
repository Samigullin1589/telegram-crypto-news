"""
Configuration Validator
Модуль валидации конфигурации
"""

import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Валидатор конфигурации"""
    
    def __init__(self, config: 'Config'):
        """
        Инициализация валидатора
        
        Args:
            config: Экземпляр главной конфигурации
        """
        self.config = config
    
    def validate(self) -> List[str]:
        """
        Комплексная валидация конфигурации
        
        Returns:
            Список предупреждений и ошибок валидации
        """
        logger.info("🔍 Валидация конфигурации...")
        
        validation_results = []
        
        # Базовая валидация
        validation_results.extend(self._validate_base_config())
        
        # Валидация путей
        validation_results.extend(self._validate_paths())
        
        # Валидация API ключей
        validation_results.extend(self._validate_api_keys())
        
        # Валидация Telegram
        validation_results.extend(self._validate_telegram())
        
        # Валидация фидов
        validation_results.extend(self._validate_feeds())
        
        # Валидация блокчейнов
        validation_results.extend(self._validate_blockchains())
        
        # Валидация функциональных модулей
        validation_results.extend(self._validate_features())
        
        # Валидация базы данных
        validation_results.extend(self._validate_database())
        
        # Валидация rate limiting
        validation_results.extend(self._validate_rate_limiting())
        
        logger.info("✅ Валидация завершена")
        return validation_results
    
    def _validate_base_config(self) -> List[str]:
        """Валидация базовой конфигурации"""
        results = []
        
        # Проверка окружения
        valid_environments = ['production', 'staging', 'development']
        if self.config.base.ENVIRONMENT.lower() not in valid_environments:
            results.append(
                f"⚠️  Неизвестное окружение: {self.config.base.ENVIRONMENT}"
            )
        
        # Предупреждение о DEBUG режиме в production
        if self.config.base.is_production() and self.config.base.DEBUG_MODE:
            results.append("⚠️  DEBUG режим включен в production!")
        
        # Проверка портов
        if not 1 <= self.config.base.PORT <= 65535:
            results.append(f"❌ Некорректный порт: {self.config.base.PORT}")
        
        return results
    
    def _validate_paths(self) -> List[str]:
        """Валидация путей"""
        results = []
        
        # Проверка существования data директории
        if not self.config.paths.data_dir.exists():
            results.append(
                f"⚠️  Data директория не существует: {self.config.paths.data_dir}"
            )
        
        return results
    
    def _validate_api_keys(self) -> List[str]:
        """Валидация API ключей"""
        results = []
        
        # Проверка AI провайдера
        if not self.config.api.has_ai_provider():
            results.append("⚠️  AI провайдер не настроен (нужен OpenAI, Gemini или Anthropic)")
        
        # Проверка API ключей для блокчейн сканеров
        missing_scanner_keys = self.config.get_missing_scanner_keys()
        if missing_scanner_keys:
            results.append(
                f"⚠️  Отсутствуют API ключи для сканеров: {', '.join(missing_scanner_keys)}"
            )
        
        # Проверка CoinGecko для whale мониторинга
        if self.config.features.whale_enabled and not self.config.has_coingecko():
            results.append("⚠️  Whale мониторинг включен, но нет CoinGecko API ключа")
        
        return results
    
    def _validate_telegram(self) -> List[str]:
        """Валидация Telegram настроек"""
        results = []
        
        # Проверка bot token
        if not self.config.telegram.bot_token:
            results.append("❌ Отсутствует TELEGRAM_BOT_TOKEN!")
        elif len(self.config.telegram.bot_token) < 20:
            results.append("⚠️  TELEGRAM_BOT_TOKEN слишком короткий")
        
        # Проверка channel ID
        if not self.config.telegram.channel_id:
            results.append("⚠️  Отсутствует TELEGRAM_CHANNEL_ID")
        
        # Проверка admin chat ID
        if not self.config.telegram.admin_chat_id:
            results.append("⚠️  Отсутствует ADMIN_CHAT_ID")
        
        return results
    
    def _validate_feeds(self) -> List[str]:
        """Валидация RSS фидов"""
        results = []
        
        # Проверка активных фидов
        active_feeds = self.config.feeds.get_enabled_feeds()
        if len(active_feeds) == 0:
            results.append("⚠️  Нет активных RSS источников новостей")
        elif len(active_feeds) < 3:
            results.append(
                f"⚠️  Мало активных RSS источников: {len(active_feeds)}"
            )
        
        # Проверка корректности URL фидов
        for feed_name, feed_config in active_feeds.items():
            if not feed_config.url.startswith(('http://', 'https://')):
                results.append(
                    f"⚠️  Некорректный URL для фида {feed_name}: {feed_config.url}"
                )
        
        return results
    
    def _validate_blockchains(self) -> List[str]:
        """Валидация блокчейн конфигурации"""
        results = []
        
        # Проверка включенных блокчейнов
        if len(self.config.blockchain.enabled_chains) == 0:
            results.append("⚠️  Нет включенных блокчейнов для мониторинга")
        
        # Проверка whale thresholds
        for chain in self.config.blockchain.enabled_chains:
            thresholds = self.config.blockchain.get_whale_threshold(chain)
            if thresholds['whale'] <= 0 or thresholds['mega_whale'] <= 0:
                results.append(
                    f"⚠️  Некорректные whale thresholds для {chain}"
                )
            if thresholds['mega_whale'] <= thresholds['whale']:
                results.append(
                    f"⚠️  Mega whale threshold должен быть больше whale для {chain}"
                )
        
        return results
    
    def _validate_features(self) -> List[str]:
        """Валидация функциональных модулей"""
        results = []
        
        # Проверка что хотя бы одна функция включена
        if not self.config.features.is_any_feature_enabled():
            results.append("❌ Все функциональные модули отключены!")
        
        # Предупреждения о зависимостях модулей
        if self.config.features.analytics_enabled and not self.config.features.news_enabled:
            results.append("⚠️  Analytics включен без News модуля")
        
        if self.config.features.trading_enabled and not self.config.features.whale_enabled:
            results.append("⚠️  Trading включен без Whale мониторинга")
        
        return results
    
    def _validate_database(self) -> List[str]:
        """Валидация базы данных"""
        results = []
        
        # Проверка настроек пула соединений
        if self.config.database.pool_size < 1:
            results.append("❌ Pool size должен быть >= 1")
        
        if self.config.database.max_overflow < 0:
            results.append("❌ Max overflow должен быть >= 0")
        
        # Проверка настроек бэкапа
        if self.config.database.backup_enabled:
            if self.config.database.backup_interval_hours < 1:
                results.append("⚠️  Слишком частый интервал бэкапа")
            if self.config.database.backup_retention_days < 1:
                results.append("⚠️  Слишком короткий срок хранения бэкапов")
        
        return results
    
    def _validate_rate_limiting(self) -> List[str]:
        """Валидация rate limiting"""
        results = []
        
        if self.config.rate_limiting.enabled:
            # Проверка корректности лимитов
            if self.config.rate_limiting.max_requests_per_minute < 1:
                results.append("❌ Некорректный rate limit")
            
            # Предупреждение о слишком строгих лимитах
            if self.config.rate_limiting.max_requests_per_minute < 10:
                results.append("⚠️  Очень строгий rate limit (< 10 req/min)")
        
        return results