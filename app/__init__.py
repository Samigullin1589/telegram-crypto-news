# app/__init__.py
"""
Crypto Compass Application Package
Version: 4.2.0

Main application initialization module
Provides clean API for importing configuration and constants
"""

__version__ = "4.2.0"
__author__ = "Crypto Compass Team"
__description__ = "Advanced Cryptocurrency Monitoring and Analysis Bot"


# ============================================================================
# Импорт главного объекта конфигурации
# ============================================================================

from app.config import config, Config


# ============================================================================
# Импорт всех констант для обратной совместимости
# ============================================================================

from app.config.exports import (
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_TOKEN,
    BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    CHAT_ID,
    CHANNEL_ID,
    ADMIN_CHAT_ID,
    
    # AI Providers
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    
    # Blockchain Scanners
    ETHERSCAN_API_KEY,
    BSCSCAN_API_KEY,
    POLYGONSCAN_API_KEY,
    ARBISCAN_API_KEY,
    BASESCAN_API_KEY,
    SNOWTRACE_API_KEY,
    OPTIMISM_ETHERSCAN_API_KEY,
    FTMSCAN_API_KEY,
    HELIUS_API_KEY,
    SOLSCAN_API_KEY,
    
    # Other APIs
    COINGECKO_API_KEY,
    ALCHEMY_API_KEY,
    COINMARKETCAP_API_KEY,
    CRYPTOPANIC_API_KEY,
    NEWSAPI_KEY,
    DEXSCREENER_API_KEY,
    BIRDEYE_API_KEY,
    
    # RSS Feeds and News
    RSS_FEEDS,
    NEWS_SOURCES,
    FETCH_INTERVAL,
    NEWS_CHECK_INTERVAL,
    POSTS_PER_HOUR_CAP,
    MIN_CONFIDENCE_SCORE,
    
    # Timing Configuration
    POST_DELAY_SECONDS,
    IDLE_DELAY_SECONDS,
    
    # File Paths
    DB_PATH,
    NEWS_DB_PATH,
    DATA_DIR,
    STATE_FILE,
    WALLET_DB_JSON_PATH,
    
    # Image Settings
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    
    # HTTP Settings
    COMMON_HEADERS,
    
    # Blockchain Configuration
    ENABLED_CHAINS,
    MIN_USD,
    
    # Feature Flags
    WHALE_ENABLED,
    NEWS_ENABLED,
    ANALYTICS_ENABLED,
    TRADING_ENABLED,
    HYPERLIQUID_ENABLED,
    
    # System Configuration
    LOG_LEVEL,
    HEALTH_CHECK_ENABLED,
    PORT,
    HTTP_TIMEOUT,
    RPC_TIMEOUT,
    WEBHOOK_TIMEOUT,
    MAX_MEMORY_MB,
)


# ============================================================================
# Публичный API модуля
# ============================================================================

__all__ = [
    # Version Info
    '__version__',
    '__author__',
    '__description__',
    
    # Main Configuration
    'config',
    'Config',
    
    # Telegram Configuration
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
    
    # RSS Feeds and News
    'RSS_FEEDS',
    'NEWS_SOURCES',
    'FETCH_INTERVAL',
    'NEWS_CHECK_INTERVAL',
    'POSTS_PER_HOUR_CAP',
    'MIN_CONFIDENCE_SCORE',
    
    # Timing Configuration
    'POST_DELAY_SECONDS',
    'IDLE_DELAY_SECONDS',
    
    # File Paths
    'DB_PATH',
    'NEWS_DB_PATH',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    
    # Image Settings
    'MIN_IMAGE_WIDTH',
    'MIN_IMAGE_HEIGHT',
    
    # HTTP Settings
    'COMMON_HEADERS',
    
    # Blockchain Configuration
    'ENABLED_CHAINS',
    'MIN_USD',
    
    # Feature Flags
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    
    # System Configuration
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'WEBHOOK_TIMEOUT',
    'MAX_MEMORY_MB',
]