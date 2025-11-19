# app/settings.py
"""
Backward Compatibility Wrapper v1.1
Экспорт констант с безопасным доступом к config
"""

from app.config import config

# ============================================================================
# TRADING SETTINGS
# ============================================================================

# ИСПРАВЛЕНО: Используем config.features.trading вместо config.trading
_trading = getattr(config, 'features', None)
if _trading:
    _trading = getattr(_trading, 'trading', None)

TRADING_ENABLED = config.is_feature_enabled('trading') if hasattr(config, 'is_feature_enabled') else False
TRADING_DRY_RUN = getattr(_trading, 'dry_run', True) if _trading else True

# Confidence & Quality
TRADING_MIN_CONFIDENCE = 75
TRADING_MIN_TECHNICAL_SCORE = 60
TRADING_MIN_FUNDAMENTAL_SCORE = 60
TRADING_MIN_ML_CONFIDENCE = 70

# Limits
TRADING_MAX_SIGNALS_PER_DAY = getattr(_trading, 'max_signals_per_day', 10) if _trading else 10
TRADING_SIGNAL_COOLDOWN_MINUTES = 60
TRADING_MAX_OPEN_POSITIONS = getattr(_trading, 'max_open_positions', 5) if _trading else 5
TRADING_MAX_POSITION_SIZE_USD = 10000

# Risk Management
TRADING_DEFAULT_STOP_LOSS_PERCENT = getattr(_trading, 'default_stop_loss', 3.0) if _trading else 3.0
TRADING_DEFAULT_TAKE_PROFIT_PERCENT = getattr(_trading, 'default_take_profit', 5.0) if _trading else 5.0

# ============================================================================
# API KEYS
# ============================================================================

_api = getattr(config, 'api', None)
COINGECKO_API_KEY = getattr(_api, 'coingecko_api_key', '') if _api else ''
OPENAI_API_KEY = getattr(_api, 'openai_api_key', '') if _api else ''
ANTHROPIC_API_KEY = getattr(_api, 'anthropic_api_key', '') if _api else ''
GEMINI_API_KEY = getattr(_api, 'gemini_api_key', '') if _api else ''

# ============================================================================
# BLOCKCHAIN SETTINGS
# ============================================================================

_blockchain = getattr(config, 'blockchain', None)
ENABLED_CHAINS = getattr(_blockchain, 'enabled_chains', []) if _blockchain else []
_rpc_urls = getattr(_blockchain, 'rpc_urls', {}) if _blockchain else {}
ETHEREUM_RPC_URL = _rpc_urls.get('ethereum', '')
BSC_RPC_URL = _rpc_urls.get('bsc', '')
POLYGON_RPC_URL = _rpc_urls.get('polygon', '')
SOLANA_RPC_URL = _rpc_urls.get('solana', '')

# ============================================================================
# WHALE SETTINGS
# ============================================================================

WHALE_ENABLED = config.is_feature_enabled('whale') if hasattr(config, 'is_feature_enabled') else False
_whale = getattr(config, 'features', None)
if _whale:
    _whale = getattr(_whale, 'whale', None)
WHALE_MIN_USD_THRESHOLD = getattr(_whale, 'min_usd_threshold', 100000) if _whale else 100000
WHALE_MIN_CONFIDENCE_SCORE = getattr(_whale, 'min_confidence_score', 70) if _whale else 70

# ============================================================================
# NEWS SETTINGS
# ============================================================================

_news = getattr(config, 'news', None) or getattr(config, 'feeds', None)
NEWS_ENABLED = getattr(_news, 'enabled', False) if _news else False
NEWS_FETCH_INTERVAL = getattr(_news, 'fetch_interval', 300) if _news else 300
NEWS_AI_ENABLED = getattr(_news, 'ai_enabled', False) if _news else False
NEWS_AI_PROVIDER = getattr(_news, 'ai_provider', 'openai') if _news else 'openai'

# ============================================================================
# PRODUCTION SETTINGS
# ============================================================================

_base = getattr(config, 'base', None)
PORT = getattr(_base, 'port', 8000) if _base else 8000
HTTP_TIMEOUT = getattr(_base, 'http_timeout', 30) if _base else 30
MAX_MEMORY_MB = getattr(_base, 'max_memory_mb', 450) if _base else 450

# ============================================================================
# RATE LIMITING
# ============================================================================

_rate_limit = getattr(config, 'rate_limiting', None)
RATE_LIMIT_ENABLED = getattr(_rate_limit, 'enabled', True) if _rate_limit else True
RATE_LIMIT_CALLS = getattr(_rate_limit, 'calls_per_minute', 60) if _rate_limit else 60

# ============================================================================
# WHALE FILTERS (для обратной совместимости)
# ============================================================================

DEBUG_FILTERS = False
ASSETS = '*'
MIN_USD_FLOOR = 100000
MIN_USD_K = 0.01


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
    
    # Whale filters
    'DEBUG_FILTERS',
    'ASSETS',
    'MIN_USD_FLOOR',
    'MIN_USD_K',
]
