# app/settings.py
"""
Backward Compatibility Wrapper v1.0
Экспорт констант для trading_system.py
"""

from app.config import config

# ============================================================================
# TRADING SETTINGS
# ============================================================================

TRADING_ENABLED = config.trading.enabled
TRADING_DRY_RUN = getattr(config.trading, 'dry_run', True)

# Confidence & Quality
TRADING_MIN_CONFIDENCE = 75
TRADING_MIN_TECHNICAL_SCORE = 60
TRADING_MIN_FUNDAMENTAL_SCORE = 60
TRADING_MIN_ML_CONFIDENCE = 70

# Limits
# ИСПРАВЛЕНО: используем существующие атрибуты TradingFeatures
TRADING_MAX_SIGNALS_PER_DAY = getattr(config.trading, 'max_signals_per_day', 10)
# check_interval в секундах, переводим в минуты для кулдауна
TRADING_SIGNAL_COOLDOWN_MINUTES = getattr(config.trading, 'check_interval', 300) // 60
TRADING_MAX_OPEN_POSITIONS = 5
TRADING_MAX_POSITION_SIZE_USD = 10000

# Risk Management
TRADING_DEFAULT_STOP_LOSS_PERCENT = 3.0
TRADING_DEFAULT_TAKE_PROFIT_PERCENT = 5.0

# ============================================================================
# API KEYS
# ============================================================================

# ИСПРАВЛЕНО: используем правильные пути к API ключам через config.api
COINGECKO_API_KEY = getattr(config.api, 'coingecko_api_key', '') if hasattr(config, 'api') else ''
OPENAI_API_KEY = getattr(config.api, 'openai_api_key', '') if hasattr(config, 'api') else ''
ANTHROPIC_API_KEY = getattr(config.api, 'anthropic_api_key', '') if hasattr(config, 'api') else ''
GEMINI_API_KEY = getattr(config.api, 'gemini_api_key', '') if hasattr(config, 'api') else ''

# ============================================================================
# BLOCKCHAIN SETTINGS
# ============================================================================

ENABLED_CHAINS = config.chains.enabled_chains
ETHEREUM_RPC_URL = config.chains.rpc_urls.get('ethereum', '')
BSC_RPC_URL = config.chains.rpc_urls.get('bsc', '')
POLYGON_RPC_URL = config.chains.rpc_urls.get('polygon', '')
SOLANA_RPC_URL = config.chains.rpc_urls.get('solana', '')

# ============================================================================
# WHALE SETTINGS
# ============================================================================

WHALE_ENABLED = config.is_feature_enabled('whale')
WHALE_MIN_USD_THRESHOLD = config.whale.min_usd_threshold
WHALE_MIN_CONFIDENCE_SCORE = config.whale.min_confidence_score

# ============================================================================
# NEWS SETTINGS
# ============================================================================

NEWS_ENABLED = config.news.enabled
NEWS_FETCH_INTERVAL = config.news.fetch_interval
NEWS_AI_ENABLED = config.news.ai_enabled
NEWS_AI_PROVIDER = config.news.ai_provider

# ============================================================================
# PRODUCTION SETTINGS
# ============================================================================

PORT = config.production.port
HTTP_TIMEOUT = config.production.http_timeout
MAX_MEMORY_MB = config.production.max_memory_mb

# ============================================================================
# RATE LIMITING
# ============================================================================

RATE_LIMIT_ENABLED = config.rate_limit.enabled
RATE_LIMIT_CALLS = config.rate_limit.calls_per_minute


__all__ = [
    # Trading
    'TRADING_ENABLED',
    'TRADING_DRY_RUN',
    'TRADING_MIN_CONFIDENCE',
    'TRADING_MIN_TECHNICAL_SCORE',
    'TRADING_MIN_FUNDAMENTAL_SCORE',
    'TRADING_MIN_ML_CONFIDENCE',
    'TRADING_MAX_SIGNALS_PER_DAY',
    'TRADING_SIGNAL_COOLDOWN_MINUTES',
    'TRADING_MAX_OPEN_POSITIONS',
    'TRADING_MAX_POSITION_SIZE_USD',
    'TRADING_DEFAULT_STOP_LOSS_PERCENT',
    'TRADING_DEFAULT_TAKE_PROFIT_PERCENT',
    
    # API Keys
    'COINGECKO_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'GEMINI_API_KEY',
    
    # Blockchain
    'ENABLED_CHAINS',
    'ETHEREUM_RPC_URL',
    'BSC_RPC_URL',
    'POLYGON_RPC_URL',
    'SOLANA_RPC_URL',
    
    # Features
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    
    # Production
    'PORT',
    'HTTP_TIMEOUT',
    'MAX_MEMORY_MB',
]