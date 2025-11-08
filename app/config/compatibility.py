# app/config/compatibility.py
"""
Compatibility Module
Обеспечивает обратную совместимость старых имен переменных
"""


def setup_compatibility_properties(config_instance):
    """
    Настройка свойств для обратной совместимости
    
    Args:
        config_instance: Экземпляр Config класса
    """
    config = config_instance
    
    config.TELEGRAM_BOT_TOKEN = config.telegram.bot_token
    config.TELEGRAM_CHANNEL_ID = config.telegram.channel_id
    config.ADMIN_CHAT_ID = config.telegram.admin_chat_id
    
    config.GEMINI_API_KEY = config.api.gemini_api_key
    config.OPENAI_API_KEY = config.api.openai_api_key
    config.ANTHROPIC_API_KEY = config.api.anthropic_api_key
    
    config.GEMINI_MODEL = config.api.gemini_model
    config.OPENAI_MODEL = config.api.openai_model
    config.ANTHROPIC_MODEL = config.api.anthropic_model
    
    config.AI_MAX_RETRIES = config.api.ai_max_retries
    config.AI_BACKOFF_FACTOR = config.api.ai_backoff_factor
    config.AI_TIMEOUT = config.api.ai_timeout
    config.AI_MAX_TOKENS = config.api.ai_max_tokens
    config.AI_TEMPERATURE = config.api.ai_temperature
    
    config.ETHERSCAN_API_KEY = config.api.etherscan_api_key
    config.BSCSCAN_API_KEY = config.api.bscscan_api_key
    config.POLYGONSCAN_API_KEY = config.api.polygonscan_api_key
    config.ARBISCAN_API_KEY = config.api.arbiscan_api_key
    config.BASESCAN_API_KEY = config.api.basescan_api_key
    config.SNOWTRACE_API_KEY = config.api.snowtrace_api_key
    config.OPTIMISM_ETHERSCAN_API_KEY = config.api.optimism_etherscan_api_key
    config.FTMSCAN_API_KEY = config.api.ftmscan_api_key
    
    config.HELIUS_API_KEY = config.api.helius_api_key
    config.SOLSCAN_API_KEY = config.api.solscan_api_key
    
    config.COINGECKO_API_KEY = config.api.coingecko_api_key
    config.ALCHEMY_API_KEY = config.api.alchemy_api_key
    config.COINMARKETCAP_API_KEY = config.api.coinmarketcap_api_key
    config.CRYPTOPANIC_API_KEY = config.api.cryptopanic_api_key
    config.NEWSAPI_KEY = config.api.newsapi_key
    config.DEXSCREENER_API_KEY = config.api.dexscreener_api_key
    config.BIRDEYE_API_KEY = config.api.birdeye_api_key
    
    config.RSS_FEEDS = config.feeds.feeds
    config.FETCH_INTERVAL = config.features.fetch_interval
    config.POSTS_PER_HOUR_CAP = config.features.posts_per_hour_cap
    config.MIN_CONFIDENCE_SCORE = config.features.min_confidence_score
    config.NEWS_CHECK_INTERVAL = config.features.news_check_interval
    
    config.WHALE_THRESHOLDS = config.blockchain.whale_thresholds
    config.ENABLED_CHAINS = config.blockchain.enabled_chains
    config.MIN_USD = config.blockchain.min_usd
    
    config.WHALE_ENABLED = config.features.whale_enabled
    config.NEWS_ENABLED = config.features.news_enabled
    config.ANALYTICS_ENABLED = config.features.analytics_enabled
    config.TRADING_ENABLED = config.features.trading_enabled
    config.HYPERLIQUID_ENABLED = config.features.hyperliquid_enabled
    
    config.POST_DELAY_SECONDS = config.features.post_delay_seconds
    config.IDLE_DELAY_SECONDS = config.features.idle_delay_seconds
    config.FEED_FETCH_TIMEOUT = config.features.feed_fetch_timeout
    config.RATE_LIMIT_DELAY_SECONDS = config.features.rate_limit_delay_seconds
    
    config.DATA_DIR = config.paths.data_dir
    config.DB_PATH = config.paths.db_path
    config.NEWS_DB_PATH = config.paths.news_db_path
    config.STATE_FILE = config.paths.state_file
    config.WALLET_DB_JSON_PATH = config.paths.wallet_db_json_path
    config.CACHE_DIR = config.paths.cache_dir
    
    config.DB_BACKUP_ENABLED = config.database.db_backup_enabled
    config.DB_BACKUP_INTERVAL_HOURS = config.database.db_backup_interval_hours
    config.DB_MAX_AGE_DAYS = config.database.db_max_age_days
    
    config.MIN_IMAGE_WIDTH = config.features.min_image_width
    config.MIN_IMAGE_HEIGHT = config.features.min_image_height
    config.MAX_IMAGE_SIZE_MB = config.features.max_image_size_mb
    config.IMAGE_CHECK_TIMEOUT = config.features.image_check_timeout
    config.IMAGE_PARTIAL_READ_BYTES = config.features.image_partial_read_bytes
    config.IMAGE_QUALITY = config.features.image_quality
    config.IMAGE_COMPRESSION_ENABLED = config.features.image_compression_enabled
    
    config.COMMON_HEADERS = config.base.COMMON_HEADERS
    
    config.SESSION_TIMEOUT_TOTAL = config.base.SESSION_TIMEOUT_TOTAL
    config.SESSION_TIMEOUT_CONNECT = config.base.SESSION_TIMEOUT_CONNECT
    config.SESSION_MAX_RETRIES = config.base.SESSION_MAX_RETRIES
    config.SESSION_RETRY_DELAY = config.base.SESSION_RETRY_DELAY
    config.CONNECTION_POOL_SIZE = config.base.CONNECTION_POOL_SIZE
    config.CONNECTION_POOL_MAX_SIZE = config.base.CONNECTION_POOL_MAX_SIZE
    
    config.MAX_ARTICLE_TEXT_LENGTH = config.features.max_article_text_length
    config.MAX_SUMMARY_LENGTH = config.features.max_summary_length
    config.MAX_SUMMARY_RETRIES = config.features.max_summary_retries
    config.SUMMARY_ENABLED = config.features.summary_enabled
    
    config.LOG_LEVEL = config.base.LOG_LEVEL
    config.VERBOSE_LOGGING = config.base.VERBOSE_LOGGING
    config.DEBUG_MODE = config.base.DEBUG_MODE
    config.LOG_FILE_ENABLED = config.base.LOG_FILE_ENABLED
    config.LOG_FILE_PATH = config.paths.log_file_path
    
    config.RATE_LIMIT_ENABLED = config.rate_limiting.rate_limit_enabled
    config.MAX_REQUESTS_PER_MINUTE = config.rate_limiting.max_requests_per_minute
    config.MAX_API_CALLS_PER_SECOND = config.rate_limiting.max_api_calls_per_second
    config.RATE_LIMIT_BURST = config.rate_limiting.rate_limit_burst
    
    config.CACHE_ENABLED = config.database.cache_enabled
    config.CACHE_TTL_SECONDS = config.database.cache_ttl_seconds
    config.CACHE_MAX_SIZE_MB = config.database.cache_max_size_mb
    
    config.RETRY_ENABLED = config.rate_limiting.retry_enabled
    config.RETRY_MAX_ATTEMPTS = config.rate_limiting.retry_max_attempts
    config.RETRY_INITIAL_DELAY = config.rate_limiting.retry_initial_delay
    config.RETRY_MAX_DELAY = config.rate_limiting.retry_max_delay
    config.RETRY_EXPONENTIAL_BASE = config.rate_limiting.retry_exponential_base
    
    config.HEALTH_CHECK_ENABLED = config.base.HEALTH_CHECK_ENABLED
    config.HEALTH_CHECK_INTERVAL = config.base.HEALTH_CHECK_INTERVAL
    config.HEALTH_CHECK_TIMEOUT = config.base.HEALTH_CHECK_TIMEOUT
    
    config.METRICS_ENABLED = config.base.METRICS_ENABLED
    config.METRICS_INTERVAL = config.base.METRICS_INTERVAL
    
    config.PORT = config.base.PORT
    config.HTTP_TIMEOUT = config.base.HTTP_TIMEOUT
    config.RPC_TIMEOUT = config.base.RPC_TIMEOUT
    config.WEBHOOK_TIMEOUT = config.base.WEBHOOK_TIMEOUT
    
    config.MAX_MEMORY_MB = config.base.MAX_MEMORY_MB
    config.GC_INTERVAL_SECONDS = config.base.GC_INTERVAL_SECONDS
    
    config.NOTIFICATION_CHANNELS = config.telegram.notification_channels
    
    config.TELEGRAM_MAX_MESSAGE_LENGTH = config.telegram.max_message_length
    config.TELEGRAM_MAX_CAPTION_LENGTH = config.telegram.max_caption_length
    config.TELEGRAM_RETRY_AFTER_DELAY = config.telegram.retry_after_delay
    config.TELEGRAM_RATE_LIMIT_DELAY = config.telegram.rate_limit_delay
    
    config.BLOCKCHAIN_EXPLORERS = config.blockchain.blockchain_explorers
    config.CHAIN_NATIVE_SYMBOLS = config.blockchain.chain_native_symbols
    config.CHAIN_NAMES = config.blockchain.chain_names
    config.CHAIN_COLORS = config.blockchain.chain_colors
    config.CHAIN_EMOJIS = config.blockchain.chain_emojis