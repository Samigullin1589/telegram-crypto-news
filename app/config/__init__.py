# app/config/__init__.py
"""
Configuration Package
Главный модуль конфигурации приложения
"""

import logging
from typing import Dict, Any
from pathlib import Path

from .base_config import BaseConfig
from .paths_config import PathsConfig
from .api_config import APIConfig
from .telegram_config import TelegramConfig
from .feeds_config import FeedsConfig, FeedConfig
from .blockchain_config import BlockchainConfig
from .features_config import FeaturesConfig
from .database_config import DatabaseConfig
from .rate_limiting_config import RateLimitingConfig

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
        
        print("\n" + "="*80)
        print("⚙️  BOT CONFIG v4.2 - INITIALIZATION")
        print("="*80 + "\n")
        
        self.base = BaseConfig()
        self.paths = PathsConfig()
        self.api = APIConfig()
        self.telegram = TelegramConfig()
        self.feeds = FeedsConfig()
        self.blockchain = BlockchainConfig()
        self.features = FeaturesConfig()
        self.database = DatabaseConfig(self.paths.db_path)
        self.rate_limiting = RateLimitingConfig()
        
        self._setup_compatibility_properties()
        
        self._initialized = True
        
        self._validate_config()
        self._print_summary()
    
    def _setup_compatibility_properties(self):
        """Настройка свойств для обратной совместимости"""
        
        self.TELEGRAM_BOT_TOKEN = self.telegram.bot_token
        self.TELEGRAM_CHANNEL_ID = self.telegram.channel_id
        self.ADMIN_CHAT_ID = self.telegram.admin_chat_id
        
        self.GEMINI_API_KEY = self.api.gemini_api_key
        self.OPENAI_API_KEY = self.api.openai_api_key
        self.ANTHROPIC_API_KEY = self.api.anthropic_api_key
        
        self.GEMINI_MODEL = self.api.gemini_model
        self.OPENAI_MODEL = self.api.openai_model
        self.ANTHROPIC_MODEL = self.api.anthropic_model
        
        self.AI_MAX_RETRIES = self.api.ai_max_retries
        self.AI_BACKOFF_FACTOR = self.api.ai_backoff_factor
        self.AI_TIMEOUT = self.api.ai_timeout
        self.AI_MAX_TOKENS = self.api.ai_max_tokens
        self.AI_TEMPERATURE = self.api.ai_temperature
        
        self.ETHERSCAN_API_KEY = self.api.etherscan_api_key
        self.BSCSCAN_API_KEY = self.api.bscscan_api_key
        self.POLYGONSCAN_API_KEY = self.api.polygonscan_api_key
        self.ARBISCAN_API_KEY = self.api.arbiscan_api_key
        self.BASESCAN_API_KEY = self.api.basescan_api_key
        self.SNOWTRACE_API_KEY = self.api.snowtrace_api_key
        self.OPTIMISM_ETHERSCAN_API_KEY = self.api.optimism_etherscan_api_key
        self.FTMSCAN_API_KEY = self.api.ftmscan_api_key
        
        self.HELIUS_API_KEY = self.api.helius_api_key
        self.SOLSCAN_API_KEY = self.api.solscan_api_key
        
        self.COINGECKO_API_KEY = self.api.coingecko_api_key
        self.ALCHEMY_API_KEY = self.api.alchemy_api_key
        self.COINMARKETCAP_API_KEY = self.api.coinmarketcap_api_key
        self.CRYPTOPANIC_API_KEY = self.api.cryptopanic_api_key
        self.NEWSAPI_KEY = self.api.newsapi_key
        self.DEXSCREENER_API_KEY = self.api.dexscreener_api_key
        self.BIRDEYE_API_KEY = self.api.birdeye_api_key
        
        self.RSS_FEEDS = self.feeds.feeds
        self.FETCH_INTERVAL = self.features.fetch_interval
        self.POSTS_PER_HOUR_CAP = self.features.posts_per_hour_cap
        self.MIN_CONFIDENCE_SCORE = self.features.min_confidence_score
        self.NEWS_CHECK_INTERVAL = self.features.news_check_interval
        
        self.WHALE_THRESHOLDS = self.blockchain.whale_thresholds
        self.ENABLED_CHAINS = self.blockchain.enabled_chains
        self.MIN_USD = self.blockchain.min_usd
        
        self.WHALE_ENABLED = self.features.whale_enabled
        self.NEWS_ENABLED = self.features.news_enabled
        self.ANALYTICS_ENABLED = self.features.analytics_enabled
        self.TRADING_ENABLED = self.features.trading_enabled
        self.HYPERLIQUID_ENABLED = self.features.hyperliquid_enabled
        
        self.POST_DELAY_SECONDS = self.features.post_delay_seconds
        self.IDLE_DELAY_SECONDS = self.features.idle_delay_seconds
        self.FEED_FETCH_TIMEOUT = self.features.feed_fetch_timeout
        self.RATE_LIMIT_DELAY_SECONDS = self.features.rate_limit_delay_seconds
        
        self.DATA_DIR = self.paths.data_dir
        self.DB_PATH = self.paths.db_path
        self.NEWS_DB_PATH = self.paths.news_db_path
        self.STATE_FILE = self.paths.state_file
        self.WALLET_DB_JSON_PATH = self.paths.wallet_db_json_path
        self.CACHE_DIR = self.paths.cache_dir
        
        self.DB_BACKUP_ENABLED = self.database.db_backup_enabled
        self.DB_BACKUP_INTERVAL_HOURS = self.database.db_backup_interval_hours
        self.DB_MAX_AGE_DAYS = self.database.db_max_age_days
        
        self.MIN_IMAGE_WIDTH = self.features.min_image_width
        self.MIN_IMAGE_HEIGHT = self.features.min_image_height
        self.MAX_IMAGE_SIZE_MB = self.features.max_image_size_mb
        self.IMAGE_CHECK_TIMEOUT = self.features.image_check_timeout
        self.IMAGE_PARTIAL_READ_BYTES = self.features.image_partial_read_bytes
        self.IMAGE_QUALITY = self.features.image_quality
        self.IMAGE_COMPRESSION_ENABLED = self.features.image_compression_enabled
        
        self.COMMON_HEADERS = self.base.COMMON_HEADERS
        
        self.SESSION_TIMEOUT_TOTAL = self.base.SESSION_TIMEOUT_TOTAL
        self.SESSION_TIMEOUT_CONNECT = self.base.SESSION_TIMEOUT_CONNECT
        self.SESSION_MAX_RETRIES = self.base.SESSION_MAX_RETRIES
        self.SESSION_RETRY_DELAY = self.base.SESSION_RETRY_DELAY
        self.CONNECTION_POOL_SIZE = self.base.CONNECTION_POOL_SIZE
        self.CONNECTION_POOL_MAX_SIZE = self.base.CONNECTION_POOL_MAX_SIZE
        
        self.MAX_ARTICLE_TEXT_LENGTH = self.features.max_article_text_length
        self.MAX_SUMMARY_LENGTH = self.features.max_summary_length
        self.MAX_SUMMARY_RETRIES = self.features.max_summary_retries
        self.SUMMARY_ENABLED = self.features.summary_enabled
        
        self.LOG_LEVEL = self.base.LOG_LEVEL
        self.VERBOSE_LOGGING = self.base.VERBOSE_LOGGING
        self.DEBUG_MODE = self.base.DEBUG_MODE
        self.LOG_FILE_ENABLED = self.base.LOG_FILE_ENABLED
        self.LOG_FILE_PATH = self.paths.log_file_path
        
        self.RATE_LIMIT_ENABLED = self.rate_limiting.rate_limit_enabled
        self.MAX_REQUESTS_PER_MINUTE = self.rate_limiting.max_requests_per_minute
        self.MAX_API_CALLS_PER_SECOND = self.rate_limiting.max_api_calls_per_second
        self.RATE_LIMIT_BURST = self.rate_limiting.rate_limit_burst
        
        self.CACHE_ENABLED = self.database.cache_enabled
        self.CACHE_TTL_SECONDS = self.database.cache_ttl_seconds
        self.CACHE_MAX_SIZE_MB = self.database.cache_max_size_mb
        
        self.RETRY_ENABLED = self.rate_limiting.retry_enabled
        self.RETRY_MAX_ATTEMPTS = self.rate_limiting.retry_max_attempts
        self.RETRY_INITIAL_DELAY = self.rate_limiting.retry_initial_delay
        self.RETRY_MAX_DELAY = self.rate_limiting.retry_max_delay
        self.RETRY_EXPONENTIAL_BASE = self.rate_limiting.retry_exponential_base
        
        self.HEALTH_CHECK_ENABLED = self.base.HEALTH_CHECK_ENABLED
        self.HEALTH_CHECK_INTERVAL = self.base.HEALTH_CHECK_INTERVAL
        self.HEALTH_CHECK_TIMEOUT = self.base.HEALTH_CHECK_TIMEOUT
        
        self.METRICS_ENABLED = self.base.METRICS_ENABLED
        self.METRICS_INTERVAL = self.base.METRICS_INTERVAL
        
        self.PORT = self.base.PORT
        self.HTTP_TIMEOUT = self.base.HTTP_TIMEOUT
        self.RPC_TIMEOUT = self.base.RPC_TIMEOUT
        self.WEBHOOK_TIMEOUT = self.base.WEBHOOK_TIMEOUT
        
        self.MAX_MEMORY_MB = self.base.MAX_MEMORY_MB
        self.GC_INTERVAL_SECONDS = self.base.GC_INTERVAL_SECONDS
        
        self.NOTIFICATION_CHANNELS = self.telegram.notification_channels
        
        self.TELEGRAM_MAX_MESSAGE_LENGTH = self.telegram.max_message_length
        self.TELEGRAM_MAX_CAPTION_LENGTH = self.telegram.max_caption_length
        self.TELEGRAM_RETRY_AFTER_DELAY = self.telegram.retry_after_delay
        self.TELEGRAM_RATE_LIMIT_DELAY = self.telegram.rate_limit_delay
        
        self.BLOCKCHAIN_EXPLORERS = self.blockchain.blockchain_explorers
        self.CHAIN_NATIVE_SYMBOLS = self.blockchain.chain_native_symbols
        self.CHAIN_NAMES = self.blockchain.chain_names
        self.CHAIN_COLORS = self.blockchain.chain_colors
        self.CHAIN_EMOJIS = self.blockchain.chain_emojis
    
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
            logger.warning(
                f"⚠️ [CONFIG] Отсутствуют API ключи для: {', '.join(missing_keys)}"
            )
        
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


TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHANNEL_ID = config.TELEGRAM_CHANNEL_ID
CHAT_ID = config.TELEGRAM_CHANNEL_ID
CHANNEL_ID = config.TELEGRAM_CHANNEL_ID
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID

GEMINI_API_KEY = config.GEMINI_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY
ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY

ETHERSCAN_API_KEY = config.ETHERSCAN_API_KEY
BSCSCAN_API_KEY = config.BSCSCAN_API_KEY
POLYGONSCAN_API_KEY = config.POLYGONSCAN_API_KEY
ARBISCAN_API_KEY = config.ARBISCAN_API_KEY
BASESCAN_API_KEY = config.BASESCAN_API_KEY
SNOWTRACE_API_KEY = config.SNOWTRACE_API_KEY
OPTIMISM_ETHERSCAN_API_KEY = config.OPTIMISM_ETHERSCAN_API_KEY
FTMSCAN_API_KEY = config.FTMSCAN_API_KEY
HELIUS_API_KEY = config.HELIUS_API_KEY
SOLSCAN_API_KEY = config.SOLSCAN_API_KEY

COINGECKO_API_KEY = config.COINGECKO_API_KEY
ALCHEMY_API_KEY = config.ALCHEMY_API_KEY
COINMARKETCAP_API_KEY = config.COINMARKETCAP_API_KEY
CRYPTOPANIC_API_KEY = config.CRYPTOPANIC_API_KEY
NEWSAPI_KEY = config.NEWSAPI_KEY
DEXSCREENER_API_KEY = config.DEXSCREENER_API_KEY
BIRDEYE_API_KEY = config.BIRDEYE_API_KEY

RSS_FEEDS = {name: feed.url for name, feed in config.RSS_FEEDS.items()}
POST_DELAY_SECONDS = config.POST_DELAY_SECONDS
IDLE_DELAY_SECONDS = config.IDLE_DELAY_SECONDS
DB_PATH = str(config.DB_PATH)
NEWS_DB_PATH = str(config.NEWS_DB_PATH)
MIN_IMAGE_WIDTH = config.MIN_IMAGE_WIDTH
MIN_IMAGE_HEIGHT = config.MIN_IMAGE_HEIGHT
COMMON_HEADERS = config.COMMON_HEADERS

NEWS_SOURCES = [
    {
        'name': name,
        'url': feed.url,
        'priority': feed.priority,
        'category': feed.category,
        'language': feed.language,
        'enabled': feed.enabled
    }
    for name, feed in config.RSS_FEEDS.items()
]

FETCH_INTERVAL = config.FETCH_INTERVAL
NEWS_CHECK_INTERVAL = config.NEWS_CHECK_INTERVAL
POSTS_PER_HOUR_CAP = config.POSTS_PER_HOUR_CAP
MIN_CONFIDENCE_SCORE = config.MIN_CONFIDENCE_SCORE

ENABLED_CHAINS = config.ENABLED_CHAINS
MIN_USD = config.MIN_USD

WHALE_ENABLED = config.WHALE_ENABLED
NEWS_ENABLED = config.NEWS_ENABLED
ANALYTICS_ENABLED = config.ANALYTICS_ENABLED
TRADING_ENABLED = config.TRADING_ENABLED
HYPERLIQUID_ENABLED = config.HYPERLIQUID_ENABLED

DATA_DIR = config.DATA_DIR
STATE_FILE = config.STATE_FILE
WALLET_DB_JSON_PATH = config.WALLET_DB_JSON_PATH

LOG_LEVEL = config.LOG_LEVEL
HEALTH_CHECK_ENABLED = config.HEALTH_CHECK_ENABLED

PORT = config.PORT
HTTP_TIMEOUT = config.HTTP_TIMEOUT
RPC_TIMEOUT = config.RPC_TIMEOUT
MAX_MEMORY_MB = config.MAX_MEMORY_MB


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
    'MAX_MEMORY_MB',
]