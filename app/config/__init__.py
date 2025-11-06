# app/config/__init__.py
"""
Configuration package for Crypto Compass Bot
"""

from app.config.settings import Config, config
from app.config.models import (
    TelegramConfig,
    ProductionConfig,
    RateLimitConfig,
    ChainConfig,
    WhaleConfig,
    HyperliquidConfig,
    TradingConfig,
    NewsConfig,
    SmartDiscoveryConfig,
    ValidationConfig,
    PerformanceConfig,
    AdaptiveThresholdsConfig,
    AnalyticsConfig,
    DatabaseConfig,
    MetricsConfig,
    DiscoveryConfig
)

# Экспорт для обратной совместимости
TELEGRAM_BOT_TOKEN = config.telegram.token
TELEGRAM_TOKEN = config.telegram.token
BOT_TOKEN = config.telegram.token
TELEGRAM_CHANNEL_ID = config.telegram.channel_id
CHAT_ID = config.telegram.channel_id
CHANNEL_ID = config.telegram.channel_id
ADMIN_CHAT_ID = config.telegram.admin_chat_id

PORT = config.production.port
HTTP_TIMEOUT = config.production.http_timeout
RPC_TIMEOUT = config.production.rpc_timeout
WEBHOOK_TIMEOUT = config.production.webhook_timeout
MAX_MEMORY_MB = config.production.max_memory_mb
GC_INTERVAL_SECONDS = config.production.gc_interval_seconds

MIN_USD = config.whale.min_usd_threshold
MIN_USD_THRESHOLD = config.whale.min_usd_threshold
WHALE_MIN_VALUE_USD = config.whale.min_usd_threshold
MIN_CONFIDENCE_SCORE = config.whale.min_confidence_score
POSTS_PER_HOUR_CAP = config.whale.posts_per_hour_cap
POLL_SECONDS = config.whale.poll_seconds
START_FROM_MINUTES_AGO = config.whale.start_from_minutes_ago

ENABLED_CHAINS = config.chains.enabled_chains
CHAINS_ENABLED = config.is_feature_enabled('chains')

WHALE_ENABLED = config.is_feature_enabled('whale')
NEWS_ENABLED = config.is_feature_enabled('news')
ANALYTICS_ENABLED = config.is_feature_enabled('analytics')
TRADING_ENABLED = config.is_feature_enabled('trading')
HYPERLIQUID_ENABLED = config.is_feature_enabled('hyperliquid')
SMART_DISCOVERY_ENABLED = config.is_feature_enabled('smart_discovery')
VALIDATION_ENABLED = config.is_feature_enabled('validation')
ADAPTIVE_THRESHOLDS_ENABLED = config.is_feature_enabled('adaptive_thresholds')
PERFORMANCE_TRACKING_ENABLED = config.is_feature_enabled('performance_tracking')

FETCH_INTERVAL = config.news.fetch_interval
NEWS_CHECK_INTERVAL = config.news.fetch_interval
NEWS_SOURCES = config.news.sources
NEWS_DB_PATH = config.database.news_db_path
DB_PATH = config.database.news_db_path

DATA_DIR = str(config.data_dir)
STATE_FILE = str(config.state_file)
WALLET_DB_JSON_PATH = str(config.wallet_db_path)
WATCHLIST_FILE = str(config.watchlist_file)
HISTORY_FILE = str(config.history_file)
POSITIONS_DIR = str(config.positions_dir)
PERFORMANCE_DIR = str(config.performance_dir)

LOG_LEVEL = config.log_level

HEALTH_CHECK_ENABLED = config.health_check_enabled
HEALTH_CHECK_INTERVAL = config.health_check_interval
HEALTH_CHECK_MAX_SILENCE = config.health_check_max_silence
SEND_STARTUP_NOTIFICATION = config.send_startup_notification
SEND_DAILY_STATS = config.send_daily_stats

OPENAI_API_KEY = config.openai_api_key
ANTHROPIC_API_KEY = config.anthropic_api_key
GEMINI_API_KEY = config.gemini_api_key
COINGECKO_API_KEY = config.coingecko_api_key
ALCHEMY_API_KEY = config.alchemy_api_key

ETHERSCAN_API_KEY = config.chains.api_keys.get('etherscan', '')
BSCSCAN_API_KEY = config.chains.api_keys.get('bscscan', '')
POLYGONSCAN_API_KEY = config.chains.api_keys.get('polygonscan', '')
ARBISCAN_API_KEY = config.chains.api_keys.get('arbiscan', '')
BASESCAN_API_KEY = config.chains.api_keys.get('basescan', '')
HELIUS_API_KEY = config.chains.api_keys.get('helius', '')

ETHEREUM_RPC_URL = config.chains.rpc_urls.get('ethereum', '')
BSC_RPC_URL = config.chains.rpc_urls.get('bsc', '')
POLYGON_RPC_URL = config.chains.rpc_urls.get('polygon', '')
ARBITRUM_RPC_URL = config.chains.rpc_urls.get('arbitrum', '')
BASE_RPC_URL = config.chains.rpc_urls.get('base', '')
SOLANA_RPC_URL = config.chains.rpc_urls.get('solana', '')
TRON_RPC_URL = config.chains.rpc_urls.get('tron', '')

SOLANA_RATE_LIMIT_REQUESTS = config.rate_limit.solana_requests
SOLANA_RATE_LIMIT_WINDOW = config.rate_limit.solana_window_seconds
SOLANA_RETRY_ON_429 = config.rate_limit.solana_retry_on_429

HYPERLIQUID_API_URL = config.hyperliquid.api_url
HYPERLIQUID_MIN_TRADE_USD = config.hyperliquid.min_trade_usd
HYPERLIQUID_MIN_LIQUIDATION_USD = config.hyperliquid.min_liquidation_usd
HYPERLIQUID_MIN_WHALE_ACTIVITY_USD = config.hyperliquid.min_whale_activity_usd
HYPERLIQUID_NOTIFY_WHALE_ACTIVITY = config.hyperliquid.notify_whale_activity
HYPERLIQUID_NOTIFY_LIQUIDATIONS = config.hyperliquid.notify_liquidations

TRADING_SIGNAL_INTERVAL_HOURS = config.trading.signal_interval_hours
TRADING_MONITORED_ASSETS = config.trading.monitored_assets
POSITION_UPDATE_INTERVAL_SECONDS = config.trading.position_update_interval_seconds

SMART_DISCOVERY_INTERVAL_HOURS = config.smart_discovery.interval_hours
SMART_DISCOVERY_MAX_NEW_WALLETS = config.smart_discovery.max_new_wallets

VALIDATION_INTERVAL_DAYS = config.validation.interval_days
VALIDATION_MIN_SCORE_TO_KEEP = config.validation.min_score_to_keep

PERFORMANCE_SUCCESS_THRESHOLD = config.performance.success_threshold

ADAPTIVE_BASE_MIN_CONFIDENCE = config.adaptive_thresholds.base_min_confidence

WEBHOOK_URL = config.webhook_url
RENDER_EXTERNAL_URL = config.render_external_url
RENDER_SERVICE_NAME = config.render_service_name

ENABLE_METRICS = config.metrics.enabled
METRICS_PORT = config.metrics.port
SENTRY_DSN = config.metrics.sentry_dsn

# Discovery Engine параметры
MIN_TOKEN_AGE_DAYS = config.discovery.min_token_age_days
DISCOVERY_TOP_N_PER_CHAIN = config.discovery.top_n_per_chain
DISCOVERY_BLACKLIST = config.discovery.blacklist
DISCOVERY_MIN_VOLUME_USD = config.discovery.min_volume_usd
DISCOVERY_MIN_MARKET_CAP_USD = config.discovery.min_market_cap_usd
DISCOVERY_MAX_PRICE_CHANGE_PERCENT = config.discovery.max_price_change_percent
DISCOVERY_INTERVAL_HOURS = config.discovery.interval_hours

__all__ = [
    'config',
    'Config',
    'TelegramConfig',
    'ProductionConfig',
    'RateLimitConfig',
    'ChainConfig',
    'WhaleConfig',
    'HyperliquidConfig',
    'TradingConfig',
    'NewsConfig',
    'SmartDiscoveryConfig',
    'ValidationConfig',
    'PerformanceConfig',
    'AdaptiveThresholdsConfig',
    'AnalyticsConfig',
    'DatabaseConfig',
    'MetricsConfig',
    'DiscoveryConfig',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_TOKEN',
    'BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'CHAT_ID',
    'CHANNEL_ID',
    'ADMIN_CHAT_ID',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'WEBHOOK_TIMEOUT',
    'MAX_MEMORY_MB',
    'GC_INTERVAL_SECONDS',
    'MIN_USD',
    'MIN_USD_THRESHOLD',
    'WHALE_MIN_VALUE_USD',
    'MIN_CONFIDENCE_SCORE',
    'POSTS_PER_HOUR_CAP',
    'POLL_SECONDS',
    'START_FROM_MINUTES_AGO',
    'ENABLED_CHAINS',
    'CHAINS_ENABLED',
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    'SMART_DISCOVERY_ENABLED',
    'VALIDATION_ENABLED',
    'ADAPTIVE_THRESHOLDS_ENABLED',
    'PERFORMANCE_TRACKING_ENABLED',
    'FETCH_INTERVAL',
    'NEWS_CHECK_INTERVAL',
    'NEWS_SOURCES',
    'NEWS_DB_PATH',
    'DB_PATH',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    'WATCHLIST_FILE',
    'HISTORY_FILE',
    'POSITIONS_DIR',
    'PERFORMANCE_DIR',
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'HEALTH_CHECK_INTERVAL',
    'HEALTH_CHECK_MAX_SILENCE',
    'SEND_STARTUP_NOTIFICATION',
    'SEND_DAILY_STATS',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'GEMINI_API_KEY',
    'COINGECKO_API_KEY',
    'ALCHEMY_API_KEY',
    'ETHERSCAN_API_KEY',
    'BSCSCAN_API_KEY',
    'POLYGONSCAN_API_KEY',
    'ARBISCAN_API_KEY',
    'BASESCAN_API_KEY',
    'HELIUS_API_KEY',
    'ETHEREUM_RPC_URL',
    'BSC_RPC_URL',
    'POLYGON_RPC_URL',
    'ARBITRUM_RPC_URL',
    'BASE_RPC_URL',
    'SOLANA_RPC_URL',
    'TRON_RPC_URL',
    'SOLANA_RATE_LIMIT_REQUESTS',
    'SOLANA_RATE_LIMIT_WINDOW',
    'SOLANA_RETRY_ON_429',
    'HYPERLIQUID_API_URL',
    'HYPERLIQUID_MIN_TRADE_USD',
    'HYPERLIQUID_MIN_LIQUIDATION_USD',
    'HYPERLIQUID_MIN_WHALE_ACTIVITY_USD',
    'HYPERLIQUID_NOTIFY_WHALE_ACTIVITY',
    'HYPERLIQUID_NOTIFY_LIQUIDATIONS',
    'TRADING_SIGNAL_INTERVAL_HOURS',
    'TRADING_MONITORED_ASSETS',
    'POSITION_UPDATE_INTERVAL_SECONDS',
    'SMART_DISCOVERY_INTERVAL_HOURS',
    'SMART_DISCOVERY_MAX_NEW_WALLETS',
    'VALIDATION_INTERVAL_DAYS',
    'VALIDATION_MIN_SCORE_TO_KEEP',
    'PERFORMANCE_SUCCESS_THRESHOLD',
    'ADAPTIVE_BASE_MIN_CONFIDENCE',
    'WEBHOOK_URL',
    'RENDER_EXTERNAL_URL',
    'RENDER_SERVICE_NAME',
    'ENABLE_METRICS',
    'METRICS_PORT',
    'SENTRY_DSN',
    'MIN_TOKEN_AGE_DAYS',
    'DISCOVERY_TOP_N_PER_CHAIN',
    'DISCOVERY_BLACKLIST',
    'DISCOVERY_MIN_VOLUME_USD',
    'DISCOVERY_MIN_MARKET_CAP_USD',
    'DISCOVERY_MAX_PRICE_CHANGE_PERCENT',
    'DISCOVERY_INTERVAL_HOURS',
]