"""
API Validator
Валидация API ключей и эндпоинтов

Проверяет:
- AI провайдеры (OpenAI, Gemini, Anthropic)
- Blockchain scanners (Etherscan, BSCScan и т.д.)
- Дополнительные сервисы (CoinGecko, Helius, Alchemy)
"""

import logging
from typing import TYPE_CHECKING, Dict

from .base_validator import BaseValidator

if TYPE_CHECKING:
    from .. import Config

logger = logging.getLogger(__name__)


class APIValidator(BaseValidator):
    """
    Валидатор API ключей
    
    Проверяет наличие и корректность формата API ключей
    для различных сервисов, используемых системой.
    """
    
    def validate(self) -> list:
        """
        Выполнить валидацию API ключей
        
        Returns:
            Список всех сообщений валидации
        """
        logger.debug("Запуск валидации API ключей...")
        
        # Очистка предыдущих результатов
        self.clear_messages()
        
        # Валидация по категориям
        self._validate_ai_providers()
        self._validate_blockchain_scanners()
        self._validate_price_providers()
        self._validate_solana_services()
        self._validate_other_apis()
        
        logger.debug(f"Валидация API завершена: {len(self.errors)} ошибок, {len(self.warnings)} предупреждений")
        
        return self.get_all_messages()
    
    # ========================================================================
    # AI ПРОВАЙДЕРЫ
    # ========================================================================
    
    def _validate_ai_providers(self) -> None:
        """Валидация AI провайдеров"""
        logger.debug("Проверка AI провайдеров...")

        if (
            getattr(self.config.api, 'cheapvibecode_api_key', '')
            and not getattr(self.config.api, 'cheapvibecode_model', '')
        ):
            self._add_warning(
                "CHEAPVIBECODE_API_KEY задан, но CHEAPVIBECODE_MODEL отсутствует. "
                "CheapVibeCode не будет активирован без точного model ID."
            )
        
        if not self.config.api.has_ai_provider():
            self._add_warning(
                "AI провайдер не настроен. "
                "AI-обработка новостей будет недоступна. "
                "Новости будут публиковаться в сыром виде. "
                "Установите CheapVibeCode или один из стандартных AI провайдеров."
            )
            return
        
        # Определяем активного провайдера
        provider = self.config.api.get_ai_provider()
        self._add_info(f"AI провайдер: {provider}")
        
        # Валидация ключей для каждого провайдера
        if provider == 'cheapvibecode':
            self._add_info(
                f"CheapVibeCode model: {self.config.api.cheapvibecode_model}"
            )
        elif provider == 'openai' and self.config.api.openai_api_key:
            self._validate_openai_key()
        elif provider == 'gemini' and self.config.api.gemini_api_key:
            self._validate_gemini_key()
        elif provider == 'anthropic' and self.config.api.anthropic_api_key:
            self._validate_anthropic_key()
    
    def _validate_openai_key(self) -> None:
        """Валидация OpenAI API ключа"""
        key = self.config.api.openai_api_key
        
        if self._validate_key_format('OpenAI', key, min_length=40, prefix='sk-'):
            self._add_info("OpenAI API ключ: корректный формат")
        
        # Дополнительные проверки для OpenAI
        if key.startswith('sk-proj-'):
            self._add_info("OpenAI: используется Project API ключ")
    
    def _validate_gemini_key(self) -> None:
        """Валидация Gemini API ключа"""
        key = self.config.api.gemini_api_key
        
        if self._validate_key_format('Gemini', key, min_length=30):
            self._add_info("Gemini API ключ: корректный формат")
    
    def _validate_anthropic_key(self) -> None:
        """Валидация Anthropic API ключа"""
        key = self.config.api.anthropic_api_key
        
        if self._validate_key_format('Anthropic', key, min_length=40, prefix='sk-ant-'):
            self._add_info("Anthropic API ключ: корректный формат")
    
    # ========================================================================
    # BLOCKCHAIN SCANNERS
    # ========================================================================
    
    def _validate_blockchain_scanners(self) -> None:
        """Валидация blockchain scanner API ключей"""
        logger.debug("Проверка blockchain scanners...")
        
        # Получаем список блокчейнов без ключей
        missing_keys = self.config.get_missing_scanner_keys()
        
        if missing_keys:
            self._add_warning(
                f"Отсутствуют API ключи для blockchain scanners: {', '.join(missing_keys)}. "
                f"Мониторинг этих сетей будет работать с ограничениями rate limit. "
                f"Рекомендуется получить бесплатные ключи на соответствующих сайтах"
            )
        else:
            self._add_info("Все необходимые blockchain scanner ключи настроены")
        
        # Валидация формата существующих ключей
        scanner_keys = {
            'Etherscan': self.config.api.etherscan_api_key,
            'BSCScan': self.config.api.bscscan_api_key,
            'PolygonScan': self.config.api.polygonscan_api_key,
            'Arbiscan': self.config.api.arbiscan_api_key,
            'BaseScan': self.config.api.basescan_api_key,
            'Snowtrace': self.config.api.snowtrace_api_key,
            'Optimism Etherscan': self.config.api.optimism_etherscan_api_key,
            'FTMScan': self.config.api.ftmscan_api_key,
        }
        
        for name, key in scanner_keys.items():
            if key:
                if self._validate_key_format(name, key, min_length=30):
                    logger.debug(f"{name}: ключ валиден")
    
    # ========================================================================
    # PRICE PROVIDERS
    # ========================================================================
    
    def _validate_price_providers(self) -> None:
        """Валидация провайдеров цен"""
        logger.debug("Проверка price providers...")
        
        # CoinGecko
        if self.config.features.whale_enabled and not self.config.has_coingecko():
            self._add_warning(
                "Whale мониторинг включен, но отсутствует CoinGecko API ключ. "
                "Получение цен токенов будет работать с ограничениями (10-50 req/min). "
                "Рекомендуется получить бесплатный ключ на coingecko.com"
            )
        elif self.config.api.coingecko_api_key:
            if self._validate_key_format('CoinGecko', self.config.api.coingecko_api_key, min_length=20):
                self._add_info("CoinGecko API ключ: настроен")
        
        # CoinMarketCap (альтернативный провайдер цен)
        if self.config.api.coinmarketcap_api_key:
            if self._validate_key_format('CoinMarketCap', self.config.api.coinmarketcap_api_key, min_length=30):
                self._add_info("CoinMarketCap API ключ: настроен")
        
        # Alchemy (для EVM chains)
        if self.config.api.alchemy_api_key:
            if self._validate_key_format('Alchemy', self.config.api.alchemy_api_key, min_length=30):
                self._add_info("Alchemy API ключ: настроен")
    
    # ========================================================================
    # SOLANA SERVICES
    # ========================================================================
    
    def _validate_solana_services(self) -> None:
        """Валидация сервисов для Solana"""
        if not self.config.blockchain.is_chain_enabled('solana'):
            return
        
        logger.debug("Проверка Solana services...")
        
        # Helius (рекомендуемый RPC провайдер для Solana)
        if not self.config.api.helius_api_key:
            self._add_warning(
                "Solana включена, но отсутствует Helius API ключ. "
                "Публичные RPC endpoint'ы могут быть нестабильными и медленными. "
                "Настоятельно рекомендуется получить бесплатный ключ на helius.dev"
            )
        else:
            if self._validate_key_format('Helius', self.config.api.helius_api_key, min_length=30):
                self._add_info("Helius API ключ: настроен (рекомендуется для Solana)")
        
        # Solscan (опциональный)
        if self.config.api.solscan_api_key:
            if self._validate_key_format('Solscan', self.config.api.solscan_api_key, min_length=20):
                self._add_info("Solscan API ключ: настроен")
        
        # Birdeye (для цен Solana токенов)
        if self.config.api.birdeye_api_key:
            if self._validate_key_format('Birdeye', self.config.api.birdeye_api_key, min_length=20):
                self._add_info("Birdeye API ключ: настроен (улучшит получение цен Solana токенов)")
    
    # ========================================================================
    # ДОПОЛНИТЕЛЬНЫЕ СЕРВИСЫ
    # ========================================================================
    
    def _validate_other_apis(self) -> None:
        """Валидация дополнительных API сервисов"""
        logger.debug("Проверка дополнительных API...")
        
        # CryptoPanic (новости)
        if self.config.api.cryptopanic_api_key:
            if self._validate_key_format('CryptoPanic', self.config.api.cryptopanic_api_key, min_length=20):
                self._add_info("CryptoPanic API ключ: настроен")
        
        # NewsAPI (новости)
        if self.config.api.newsapi_key:
            if self._validate_key_format('NewsAPI', self.config.api.newsapi_key, min_length=30):
                self._add_info("NewsAPI ключ: настроен")
        
        # DexScreener (DEX данные)
        if self.config.api.dexscreener_api_key:
            if self._validate_key_format('DexScreener', self.config.api.dexscreener_api_key, min_length=20):
                self._add_info("DexScreener API ключ: настроен")
    
    def get_summary(self) -> Dict[str, any]:
        """
        Получить сводку валидации API
        
        Returns:
            Словарь со статистикой
        """
        return {
            'has_ai_provider': self.config.api.has_ai_provider(),
            'ai_provider': self.config.api.get_ai_provider(),
            'missing_scanner_keys': self.config.get_missing_scanner_keys(),
            'has_coingecko': self.config.has_coingecko(),
            'has_alchemy': self.config.has_alchemy(),
            'has_errors': self.has_errors(),
            'has_warnings': self.has_warnings(),
        }