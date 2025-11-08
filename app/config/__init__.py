# app/config/__init__.py
"""
Configuration Package
Главный модуль конфигурации приложения с улучшенной архитектурой
"""

import logging
from typing import Dict, Any

from .base_config import BaseConfig
from .paths_config import PathsConfig
from .api_config import APIConfig
from .telegram_config import TelegramConfig
from .feeds_config import FeedsConfig, FeedConfig
from .blockchain_config import BlockchainConfig
from .features_config import FeaturesConfig
from .database_config import DatabaseConfig
from .rate_limiting_config import RateLimitingConfig
from .compatibility import setup_compatibility_properties
from .exports import setup_exports

logger = logging.getLogger(__name__)


class Config:
    """
    Главный класс конфигурации
    Объединяет все модули конфигурации и предоставляет единый интерфейс
    
    Singleton паттерн для обеспечения единственного экземпляра
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация главной конфигурации"""
        if self._initialized:
            return
        
        self._print_header()
        self._initialize_modules()
        self._setup_properties()
        self._validate_config()
        self._print_summary()
        
        self._initialized = True
    
    def _print_header(self):
        """Вывод заголовка инициализации"""
        print("\n" + "="*80)
        print("⚙️  BOT CONFIG v4.2 - INITIALIZATION")
        print("="*80 + "\n")
    
    def _initialize_modules(self):
        """Инициализация всех модулей конфигурации"""
        self.base = BaseConfig()
        self.paths = PathsConfig()
        self.api = APIConfig()
        self.telegram = TelegramConfig()
        self.feeds = FeedsConfig()
        self.blockchain = BlockchainConfig()
        self.features = FeaturesConfig()
        self.database = DatabaseConfig(self.paths.db_path)
        self.rate_limiting = RateLimitingConfig()
    
    def _setup_properties(self):
        """Настройка свойств для обратной совместимости"""
        setup_compatibility_properties(self)
    
    def has_scanner_api_key(self, chain: str) -> bool:
        """Проверка наличия API ключа для сканера"""
        return self.api.has_scanner_key(chain)
    
    def get_scanner_api_key(self, chain: str) -> str:
        """Получение API ключа для сканера"""
        return self.api.get_scanner_key(chain)
    
    def get_missing_scanner_keys(self) -> list:
        """Получение списка отсутствующих ключей"""
        return self.api.get_missing_scanner_keys(self.blockchain.enabled_chains)
    
    def has_coingecko(self) -> bool:
        """Проверка наличия CoinGecko API"""
        return bool(self.api.coingecko_api_key)
    
    def has_alchemy(self) -> bool:
        """Проверка наличия Alchemy API"""
        return bool(self.api.alchemy_api_key)
    
    def has_coinmarketcap(self) -> bool:
        """Проверка наличия CoinMarketCap API"""
        return bool(self.api.coinmarketcap_api_key)
    
    def has_ai_provider(self) -> bool:
        """Проверка наличия AI провайдера"""
        return self.api.has_ai_provider()
    
    def get_ai_provider(self) -> str:
        """Получение названия AI провайдера"""
        return self.api.get_ai_provider()
    
    def get_chain_explorer_url(self, chain: str, address: str = None, tx_hash: str = None) -> str:
        """Получение URL эксплорера"""
        return self.blockchain.get_explorer_url(chain, address, tx_hash)
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение символа блокчейна"""
        return self.blockchain.get_chain_symbol(chain)
    
    def get_chain_name(self, chain: str) -> str:
        """Получение имени блокчейна"""
        return self.blockchain.get_chain_name(chain)
    
    def get_chain_emoji(self, chain: str) -> str:
        """Получение emoji блокчейна"""
        return self.blockchain.get_chain_emoji(chain)
    
    def get_chain_color(self, chain: str) -> str:
        """Получение цвета блокчейна"""
        return self.blockchain.get_chain_color(chain)
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return self.blockchain.is_chain_enabled(chain)
    
    def get_sorted_feeds(self) -> list:
        """Получение отсортированных фидов"""
        return self.feeds.get_sorted_feeds()
    
    def get_feed_by_name(self, name: str) -> FeedConfig:
        """Получение фида по имени"""
        return self.feeds.get_feed_by_name(name)
    
    def get_feed_config(self, name: str) -> FeedConfig:
        """Получение конфигурации фида"""
        return self.feeds.get_feed_by_name(name)
    
    def get_all_feeds(self) -> Dict[str, FeedConfig]:
        """Получение всех фидов"""
        return self.feeds.feeds
    
    def get_enabled_feeds(self) -> Dict[str, FeedConfig]:
        """Получение активных фидов"""
        return self.feeds.get_enabled_feeds()
    
    def enable_feed(self, name: str):
        """Включение фида"""
        self.feeds.enable_feed(name)
    
    def disable_feed(self, name: str):
        """Отключение фида"""
        self.feeds.disable_feed(name)
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """Получение порогов whale для блокчейна"""
        return self.blockchain.get_whale_threshold(chain)
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        return self.blockchain.is_whale_transaction(chain, usd_value)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        return self.blockchain.is_mega_whale_transaction(chain, usd_value)
    
    def _validate_config(self):
        """Валидация конфигурации"""
        active_feeds = len(self.feeds.get_enabled_feeds())
        if active_feeds == 0:
            logger.warning("⚠️ [CONFIG] Нет активных RSS источников")
        
        if not self.api.has_ai_provider():
            logger.warning("⚠️ [CONFIG] AI провайдер не настроен")
        
        missing_keys = self.get_missing_scanner_keys()
        if missing_keys:
            print(f"⚠️ [CONFIG] Отсутствуют API ключи для: {', '.join(missing_keys)}")
        
        if not self.features.is_any_feature_enabled():
            logger.error("❌ [CONFIG] Все функции отключены!")
    
    def _print_summary(self):
        """Вывод сводки конфигурации"""
        print("✅ [CONFIG] Конфигурация загружена успешно")
        print(f"   Окружение: {self.base.ENVIRONMENT}")
        print(f"   Активных фидов: {len(self.feeds.get_enabled_feeds())}")
        print(f"   Включенные chains: {', '.join(self.blockchain.enabled_chains)}")
        print(f"   AI Provider: {self.api.get_ai_provider() or 'None'}")
        print(
            f"   Функции: Whale={self.features.whale_enabled}, "
            f"News={self.features.news_enabled}, "
            f"Analytics={self.features.analytics_enabled}"
        )
        print(f"   База данных: {self.paths.db_path}")
        print("")
    
    @property
    def ai_prompt_template(self) -> str:
        """Шаблон промпта для AI"""
        return """
Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.

Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

{emoji} **{title}**

*Здесь напиши главную суть новости в 2-3 предложениях. Используй профессиональный, но понятный язык. Объясни, почему это важно.*

**Детали:**
- Ключевой факт или цифра из статьи.
- Контекст или причина произошедшего.
- Возможные последствия для рынка или индустрии.

*(Сгенерируй 3 релевантных хэштега на русском, например: #биткоин #регулирование #SEC)*
"""
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        """Статус включенных функций"""
        return self.features.get_enabled_features()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'base': self.base.to_dict(),
            'paths': self.paths.to_dict(),
            'api': self.api.to_dict(),
            'telegram': self.telegram.to_dict(),
            'feeds': self.feeds.to_dict(),
            'blockchain': self.blockchain.to_dict(),
            'features': self.features.to_dict(),
            'database': self.database.to_dict(),
            'rate_limiting': self.rate_limiting.to_dict()
        }


config = Config()

from .exports import *

__all__ = [
    'config',
    'Config',
    'FeedConfig',
    'BaseConfig',
    'PathsConfig',
    'APIConfig',
    'TelegramConfig',
    'FeedsConfig',
    'BlockchainConfig',
    'FeaturesConfig',
    'DatabaseConfig',
    'RateLimitingConfig',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_TOKEN',
    'BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'CHAT_ID',
    'CHANNEL_ID',
    'ADMIN_CHAT_ID',
    'GEMINI_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'ETHERSCAN_API_KEY',
    'BSCSCAN_API_KEY',
    'POLYGONSCAN_API_KEY',
    'ARBISCAN_API_KEY',
    'BASESCAN_API_KEY',
    'SNOWTRACE_API_KEY',
    'OPTIMISM_ETHERSCAN_API_KEY',
    'FTMSCAN_API_KEY',
    'HELIUS_API_KEY',
    'SOLSCAN_API_KEY',
    'COINGECKO_API_KEY',
    'ALCHEMY_API_KEY',
    'COINMARKETCAP_API_KEY',
    'CRYPTOPANIC_API_KEY',
    'NEWSAPI_KEY',
    'DEXSCREENER_API_KEY',
    'BIRDEYE_API_KEY',
    'RSS_FEEDS',
    'NEWS_SOURCES',
    'FETCH_INTERVAL',
    'NEWS_CHECK_INTERVAL',
    'POSTS_PER_HOUR_CAP',
    'MIN_CONFIDENCE_SCORE',
    'POST_DELAY_SECONDS',
    'IDLE_DELAY_SECONDS',
    'DB_PATH',
    'NEWS_DB_PATH',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    'MIN_IMAGE_WIDTH',
    'MIN_IMAGE_HEIGHT',
    'COMMON_HEADERS',
    'ENABLED_CHAINS',
    'MIN_USD',
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'WEBHOOK_TIMEOUT',
    'MAX_MEMORY_MB',
]