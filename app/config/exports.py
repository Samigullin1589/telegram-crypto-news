"""
Configuration Exports
Экспорт всех констант для обратной совместимости

Этот модуль экспортирует константы для использования старым кодом.
Все значения читаются напрямую из переменных окружения.

ВАЖНО: Этот модуль содержит только константы и не имеет сложной логики.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# TELEGRAM - Константы Telegram
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_TOKEN = TELEGRAM_BOT_TOKEN  # Алиас
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Алиас

TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')
CHAT_ID = TELEGRAM_CHANNEL_ID  # Алиас
CHANNEL_ID = TELEGRAM_CHANNEL_ID  # Алиас

ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', TELEGRAM_CHANNEL_ID)

# ============================================================================
# AI PROVIDERS - API ключи AI сервисов
# ============================================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# ============================================================================
# BLOCKCHAIN SCANNERS - API ключи blockchain explorers
# ============================================================================

ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', '')
POLYGONSCAN_API_KEY = os.getenv('POLYGONSCAN_API_KEY', '')
ARBISCAN_API_KEY = os.getenv('ARBISCAN_API_KEY', '')
BASESCAN_API_KEY = os.getenv('BASESCAN_API_KEY', '')
SNOWTRACE_API_KEY = os.getenv('SNOWTRACE_API_KEY', '')
OPTIMISM_ETHERSCAN_API_KEY = os.getenv('OPTIMISM_ETHERSCAN_API_KEY', '')
FTMSCAN_API_KEY = os.getenv('FTMSCAN_API_KEY', '')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')

# ============================================================================
# OTHER APIs - Прочие внешние сервисы
# ============================================================================

COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', '')
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', '')
CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
DEXSCREENER_API_KEY = os.getenv('DEXSCREENER_API_KEY', '')
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')

# ============================================================================
# RSS AND NEWS - Настройки новостей
# ============================================================================

# Эти будут установлены после инициализации feeds_config
RSS_FEEDS = {}
NEWS_SOURCES = {}

# Интервалы и лимиты
FETCH_INTERVAL = int(os.getenv('NEWS_FETCH_INTERVAL', '300'))
NEWS_CHECK_INTERVAL = FETCH_INTERVAL
POSTS_PER_HOUR_CAP = int(os.getenv('POSTS_PER_HOUR_CAP', '3'))
MIN_CONFIDENCE_SCORE = int(os.getenv('MIN_CONFIDENCE_SCORE', '6'))

# ============================================================================
# TIMING - Временные константы
# ============================================================================

POST_DELAY_SECONDS = int(os.getenv('POST_DELAY_SECONDS', '10'))
IDLE_DELAY_SECONDS = int(os.getenv('IDLE_DELAY_SECONDS', '300'))

# ============================================================================
# PATHS - Пути к файлам и директориям
# ============================================================================

DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
DB_PATH = DATA_DIR / 'crypto_monitor.db'
NEWS_DB_PATH = Path(os.getenv('NEWS_DB_PATH', 'news_database.sqlite'))
STATE_FILE = DATA_DIR / 'state.json'
WALLET_DB_JSON_PATH = DATA_DIR / 'wallets' / 'tracked_wallets.json'

# ============================================================================
# IMAGES - Настройки изображений
# ============================================================================

MIN_IMAGE_WIDTH = int(os.getenv('MIN_IMAGE_WIDTH', '400'))
MIN_IMAGE_HEIGHT = int(os.getenv('MIN_IMAGE_HEIGHT', '300'))

# ============================================================================
# HTTP - HTTP заголовки и настройки
# ============================================================================

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', '30'))
RPC_TIMEOUT = int(os.getenv('RPC_TIMEOUT', '15'))
WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', '10'))

# ============================================================================
# BLOCKCHAIN - Настройки блокчейнов
# ============================================================================

ENABLED_CHAINS = os.getenv(
    'ENABLED_CHAINS',
    'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche'
).split(',')

# Очистка списка от пробелов
ENABLED_CHAINS = [chain.strip() for chain in ENABLED_CHAINS if chain.strip()]

MIN_USD = float(os.getenv('MIN_USD', '100000'))

# ============================================================================
# FEATURES - Флаги включения модулей
# ============================================================================

def _parse_bool(value: str) -> bool:
    """Парсинг булевого значения из строки"""
    return value.lower() in ('true', '1', 'yes', 'on', 'enabled')

WHALE_ENABLED = _parse_bool(os.getenv('WHALE_ENABLED', 'true'))
NEWS_ENABLED = _parse_bool(os.getenv('NEWS_ENABLED', 'true'))
ANALYTICS_ENABLED = _parse_bool(os.getenv('ANALYTICS_ENABLED', 'false'))
TRADING_ENABLED = _parse_bool(os.getenv('TRADING_ENABLED', 'false'))
HYPERLIQUID_ENABLED = _parse_bool(os.getenv('HYPERLIQUID_ENABLED', 'false'))

# ============================================================================
# SYSTEM - Системные настройки
# ============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
DEBUG_MODE = _parse_bool(os.getenv('DEBUG_MODE', 'false'))
HEALTH_CHECK_ENABLED = _parse_bool(os.getenv('HEALTH_CHECK_ENABLED', 'true'))
PORT = int(os.getenv('PORT', '8000'))

# Memory
MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', '450'))

# ============================================================================
# DATABASE - Настройки БД
# ============================================================================

DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))

# ============================================================================
# RATE LIMITING - Ограничения скорости
# ============================================================================

MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60'))
SOLANA_REQUESTS_PER_SECOND = int(os.getenv('SOLANA_REQUESTS_PER_SECOND', '25'))

# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
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
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'WEBHOOK_TIMEOUT',
    
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
    'ENVIRONMENT',
    'DEBUG_MODE',
    'HEALTH_CHECK_ENABLED',
    'PORT',
    'MAX_MEMORY_MB',
    
    # Database
    'DB_POOL_SIZE',
    'DB_MAX_OVERFLOW',
    
    # Rate Limiting
    'MAX_REQUESTS_PER_MINUTE',
    'SOLANA_REQUESTS_PER_SECOND',
]

logger.debug(f"Экспортировано {len(__all__)} констант конфигурации")