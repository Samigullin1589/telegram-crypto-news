# app/config/exports.py
"""
Exports Module
Экспорт всех констант для обратной совместимости

ВАЖНО: Этот модуль не импортирует config напрямую, чтобы избежать циклических импортов
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config


def _get_config() -> 'Config':
    """
    Ленивое получение экземпляра config
    
    Импорт происходит только при вызове функции,
    когда config уже полностью инициализирован
    """
    from . import config
    return config


def setup_exports() -> dict:
    """
    Создает и возвращает все экспортируемые константы
    
    Эта функция вызывается ПОСЛЕ инициализации config,
    поэтому циклического импорта не происходит
    
    Returns:
        Dict со всеми константами для экспорта
    """
    cfg = _get_config()
    
    return {
        # Telegram
        'TELEGRAM_BOT_TOKEN': cfg.telegram.bot_token,
        'TELEGRAM_TOKEN': cfg.telegram.bot_token,
        'BOT_TOKEN': cfg.telegram.bot_token,
        'TELEGRAM_CHANNEL_ID': cfg.telegram.channel_id,
        'CHAT_ID': cfg.telegram.channel_id,
        'CHANNEL_ID': cfg.telegram.channel_id,
        'ADMIN_CHAT_ID': cfg.telegram.admin_chat_id,
        
        # AI Providers
        'GEMINI_API_KEY': cfg.api.gemini_api_key,
        'OPENAI_API_KEY': cfg.api.openai_api_key,
        'ANTHROPIC_API_KEY': cfg.api.anthropic_api_key,
        
        # Blockchain Scanners
        'ETHERSCAN_API_KEY': cfg.api.etherscan_api_key,
        'BSCSCAN_API_KEY': cfg.api.bscscan_api_key,
        'POLYGONSCAN_API_KEY': cfg.api.polygonscan_api_key,
        'ARBISCAN_API_KEY': cfg.api.arbiscan_api_key,
        'BASESCAN_API_KEY': cfg.api.basescan_api_key,
        'SNOWTRACE_API_KEY': cfg.api.snowtrace_api_key,
        'OPTIMISM_ETHERSCAN_API_KEY': cfg.api.optimism_etherscan_api_key,
        'FTMSCAN_API_KEY': cfg.api.ftmscan_api_key,
        'HELIUS_API_KEY': cfg.api.helius_api_key,
        'SOLSCAN_API_KEY': cfg.api.solscan_api_key,
        
        # Other APIs
        'COINGECKO_API_KEY': cfg.api.coingecko_api_key,
        'ALCHEMY_API_KEY': cfg.api.alchemy_api_key,
        'COINMARKETCAP_API_KEY': cfg.api.coinmarketcap_api_key,
        'CRYPTOPANIC_API_KEY': cfg.api.cryptopanic_api_key,
        'NEWSAPI_KEY': cfg.api.newsapi_key,
        'DEXSCREENER_API_KEY': cfg.api.dexscreener_api_key,
        'BIRDEYE_API_KEY': cfg.api.birdeye_api_key,
        
        # RSS and News
        'RSS_FEEDS': {name: feed.url for name, feed in cfg.feeds.feeds.items()},
        'NEWS_SOURCES': [
            {
                'name': name,
                'url': feed.url,
                'priority': feed.priority,
                'category': feed.category,
                'language': feed.language,
                'enabled': feed.enabled
            }
            for name, feed in cfg.feeds.feeds.items()
        ],
        'FETCH_INTERVAL': cfg.feeds.fetch_interval,
        'NEWS_CHECK_INTERVAL': cfg.feeds.news_check_interval,
        'POSTS_PER_HOUR_CAP': cfg.feeds.posts_per_hour_cap,
        'MIN_CONFIDENCE_SCORE': cfg.feeds.min_confidence_score,
        
        # Timing
        'POST_DELAY_SECONDS': cfg.feeds.post_delay_seconds,
        'IDLE_DELAY_SECONDS': cfg.feeds.idle_delay_seconds,
        
        # Paths
        'DB_PATH': str(cfg.paths.db_path),
        'NEWS_DB_PATH': str(cfg.paths.news_db_path),
        'DATA_DIR': str(cfg.paths.data_dir),
        'STATE_FILE': str(cfg.paths.state_file),
        'WALLET_DB_JSON_PATH': str(cfg.paths.wallet_db_json_path),
        
        # Images
        'MIN_IMAGE_WIDTH': cfg.telegram.min_image_width,
        'MIN_IMAGE_HEIGHT': cfg.telegram.min_image_height,
        
        # HTTP
        'COMMON_HEADERS': cfg.telegram.common_headers,
        
        # Blockchain
        'ENABLED_CHAINS': cfg.blockchain.enabled_chains,
        'MIN_USD': cfg.blockchain.min_usd_value,
        
        # Features
        'WHALE_ENABLED': cfg.features.whale_enabled,
        'NEWS_ENABLED': cfg.features.news_enabled,
        'ANALYTICS_ENABLED': cfg.features.analytics_enabled,
        'TRADING_ENABLED': cfg.features.trading_enabled,
        'HYPERLIQUID_ENABLED': cfg.features.hyperliquid_enabled,
        
        # System
        'LOG_LEVEL': cfg.base.LOG_LEVEL,
        'HEALTH_CHECK_ENABLED': cfg.base.health_check_enabled,
        'PORT': cfg.base.PORT,
        'HTTP_TIMEOUT': cfg.base.http_timeout,
        'RPC_TIMEOUT': cfg.base.rpc_timeout,
        'WEBHOOK_TIMEOUT': cfg.base.webhook_timeout,
        'MAX_MEMORY_MB': cfg.base.max_memory_mb,
    }


# Ленивая инициализация констант при первом импорте
_exports_cache = None


def _get_exports():
    """Получение кэшированных экспортов"""
    global _exports_cache
    if _exports_cache is None:
        _exports_cache = setup_exports()
    return _exports_cache


# Динамическое создание констант при импорте
def __getattr__(name: str):
    """
    Магический метод для ленивого создания констант
    
    Позволяет импортировать константы как обычно:
    from app.config.exports import TELEGRAM_BOT_TOKEN
    
    Но создание происходит только при первом обращении
    """
    exports = _get_exports()
    if name in exports:
        return exports[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """Список всех доступных атрибутов"""
    exports = _get_exports()
    return list(exports.keys())


__all__ = [
    'setup_exports',
    # Telegram
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_TOKEN',
    'BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'CHAT_ID',
    'CHANNEL_ID',
    'ADMIN_CHAT_ID',
    # AI Providers
    'GEMINI_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    # Blockchain Scanners
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
    # Other APIs
    'COINGECKO_API_KEY',
    'ALCHEMY_API_KEY',
    'COINMARKETCAP_API_KEY',
    'CRYPTOPANIC_API_KEY',
    'NEWSAPI_KEY',
    'DEXSCREENER_API_KEY',
    'BIRDEYE_API_KEY',
    # RSS and News
    'RSS_FEEDS',
    'NEWS_SOURCES',
    'FETCH_INTERVAL',
    'NEWS_CHECK_INTERVAL',
    'POSTS_PER_HOUR_CAP',
    'MIN_CONFIDENCE_SCORE',
    # Timing
    'POST_DELAY_SECONDS',
    'IDLE_DELAY_SECONDS',
    # Paths
    'DB_PATH',
    'NEWS_DB_PATH',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    # Images
    'MIN_IMAGE_WIDTH',
    'MIN_IMAGE_HEIGHT',
    # HTTP
    'COMMON_HEADERS',
    # Blockchain
    'ENABLED_CHAINS',
    'MIN_USD',
    # Features
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    # System
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'WEBHOOK_TIMEOUT',
    'MAX_MEMORY_MB',
]