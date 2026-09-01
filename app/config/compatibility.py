"""
Compatibility Layer
Обратная совместимость со старым кодом

Этот модуль добавляет алиасы старых имен переменных к новой структуре
конфигурации, позволяя старому коду работать без изменений.

ВАЖНО: Этот модуль НЕ импортирует Config напрямую, чтобы избежать
циклических зависимостей. Вместо этого функция setup_compatibility_properties
принимает экземпляр config как параметр.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


def setup_compatibility_properties(config_instance: 'Config') -> None:
    """
    Настройка свойств для обратной совместимости
    
    Добавляет алиасы старых имен переменных к экземпляру конфигурации.
    Это позволяет старому коду обращаться к параметрам через старые имена:
    
    Примеры:
        config.TELEGRAM_BOT_TOKEN вместо config.telegram.bot_token
        config.ENABLED_CHAINS вместо config.blockchain.enabled_chains
        config.WHALE_ENABLED вместо config.features.whale_enabled
    
    Args:
        config_instance: Экземпляр Config для настройки
        
    Raises:
        Exception: При критических ошибках настройки совместимости
    """
    try:
        logger.debug("Настройка свойств обратной совместимости...")
        
        # ====================================================================
        # TELEGRAM - Алиасы для настроек Telegram бота
        # ====================================================================
        
        # Bot token (несколько вариантов для совместимости)
        config_instance.TELEGRAM_BOT_TOKEN = config_instance.telegram.bot_token
        config_instance.TELEGRAM_TOKEN = config_instance.telegram.bot_token
        config_instance.BOT_TOKEN = config_instance.telegram.bot_token
        
        # Channel and admin
        config_instance.TELEGRAM_CHANNEL_ID = config_instance.telegram.channel_id
        config_instance.CHAT_ID = config_instance.telegram.channel_id
        config_instance.CHANNEL_ID = config_instance.telegram.channel_id
        config_instance.ADMIN_CHAT_ID = config_instance.telegram.admin_chat_id
        
        # ====================================================================
        # API KEYS - AI PROVIDERS
        # ====================================================================
        
        config_instance.GEMINI_API_KEY = config_instance.api.gemini_api_key
        config_instance.OPENAI_API_KEY = config_instance.api.openai_api_key
        config_instance.ANTHROPIC_API_KEY = config_instance.api.anthropic_api_key
        config_instance.CHEAPVIBECODE_API_KEY = config_instance.api.cheapvibecode_api_key
        
        # ====================================================================
        # API KEYS - BLOCKCHAIN SCANNERS
        # ====================================================================
        
        config_instance.ETHERSCAN_API_KEY = config_instance.api.etherscan_api_key
        config_instance.BSCSCAN_API_KEY = config_instance.api.bscscan_api_key
        config_instance.POLYGONSCAN_API_KEY = config_instance.api.polygonscan_api_key
        config_instance.ARBISCAN_API_KEY = config_instance.api.arbiscan_api_key
        config_instance.BASESCAN_API_KEY = config_instance.api.basescan_api_key
        config_instance.SNOWTRACE_API_KEY = config_instance.api.snowtrace_api_key
        config_instance.OPTIMISM_ETHERSCAN_API_KEY = config_instance.api.optimism_etherscan_api_key
        config_instance.FTMSCAN_API_KEY = config_instance.api.ftmscan_api_key
        config_instance.HELIUS_API_KEY = config_instance.api.helius_api_key
        config_instance.SOLSCAN_API_KEY = config_instance.api.solscan_api_key
        
        # ====================================================================
        # API KEYS - OTHER SERVICES
        # ====================================================================
        
        config_instance.COINGECKO_API_KEY = config_instance.api.coingecko_api_key
        config_instance.ALCHEMY_API_KEY = config_instance.api.alchemy_api_key
        config_instance.COINMARKETCAP_API_KEY = config_instance.api.coinmarketcap_api_key
        config_instance.CRYPTOPANIC_API_KEY = config_instance.api.cryptopanic_api_key
        config_instance.NEWSAPI_KEY = config_instance.api.newsapi_key
        config_instance.DEXSCREENER_API_KEY = config_instance.api.dexscreener_api_key
        config_instance.BIRDEYE_API_KEY = config_instance.api.birdeye_api_key
        
        # ====================================================================
        # BLOCKCHAIN - Настройки блокчейнов
        # ====================================================================
        
        config_instance.ENABLED_CHAINS = config_instance.blockchain.enabled_chains
        config_instance.MIN_USD = config_instance.blockchain.min_usd
        
        # ====================================================================
        # FEATURES - Функциональные модули
        # ====================================================================
        
        config_instance.WHALE_ENABLED = config_instance.features.whale_enabled
        config_instance.NEWS_ENABLED = config_instance.features.news_enabled
        config_instance.ANALYTICS_ENABLED = config_instance.features.analytics_enabled
        config_instance.TRADING_ENABLED = config_instance.features.trading_enabled
        config_instance.HYPERLIQUID_ENABLED = config_instance.features.hyperliquid_enabled
        
        # ====================================================================
        # PATHS - Пути к файлам
        # ====================================================================
        
        config_instance.DB_PATH = config_instance.paths.db_path
        config_instance.NEWS_DB_PATH = config_instance.paths.news_db_path
        config_instance.DATA_DIR = config_instance.paths.data_dir
        config_instance.STATE_FILE = config_instance.paths.state_file
        
        # Wallet DB path (если существует)
        if hasattr(config_instance.paths, 'wallet_db_json_path'):
            config_instance.WALLET_DB_JSON_PATH = config_instance.paths.wallet_db_json_path
        
        # ====================================================================
        # RSS FEEDS - Источники новостей
        # ====================================================================
        
        config_instance.RSS_FEEDS = config_instance.feeds.feeds
        config_instance.NEWS_SOURCES = config_instance.feeds.feeds
        
        # ====================================================================
        # SYSTEM - Системные настройки
        # ====================================================================
        
        config_instance.LOG_LEVEL = config_instance.base.LOG_LEVEL
        config_instance.PORT = config_instance.base.PORT
        config_instance.ENVIRONMENT = config_instance.base.ENVIRONMENT
        config_instance.DEBUG_MODE = config_instance.base.DEBUG_MODE
        config_instance.HEALTH_CHECK_ENABLED = config_instance.base.HEALTH_CHECK_ENABLED
        
        # Timeouts (если существуют)
        if hasattr(config_instance.base, 'HTTP_TIMEOUT'):
            config_instance.HTTP_TIMEOUT = config_instance.base.HTTP_TIMEOUT
        if hasattr(config_instance.base, 'RPC_TIMEOUT'):
            config_instance.RPC_TIMEOUT = config_instance.base.RPC_TIMEOUT
        if hasattr(config_instance.base, 'WEBHOOK_TIMEOUT'):
            config_instance.WEBHOOK_TIMEOUT = config_instance.base.WEBHOOK_TIMEOUT
        
        # Memory limits (если существуют)
        if hasattr(config_instance.base, 'MAX_MEMORY_MB'):
            config_instance.MAX_MEMORY_MB = config_instance.base.MAX_MEMORY_MB
        
        # ====================================================================
        # NEWS SETTINGS - Настройки новостного модуля
        # ====================================================================
        
        if hasattr(config_instance.features, 'news_fetch_interval'):
            config_instance.FETCH_INTERVAL = config_instance.features.news_fetch_interval
            config_instance.NEWS_CHECK_INTERVAL = config_instance.features.news_fetch_interval
        
        if hasattr(config_instance.features, 'news_posts_per_hour'):
            config_instance.POSTS_PER_HOUR_CAP = config_instance.features.news_posts_per_hour
        
        if hasattr(config_instance.features, 'min_confidence_score'):
            config_instance.MIN_CONFIDENCE_SCORE = config_instance.features.min_confidence_score
        
        # ====================================================================
        # TIMING - Временные константы
        # ====================================================================
        
        config_instance.POST_DELAY_SECONDS = 10
        config_instance.IDLE_DELAY_SECONDS = 300
        
        # ====================================================================
        # IMAGES - Настройки изображений
        # ====================================================================
        
        config_instance.MIN_IMAGE_WIDTH = 400
        config_instance.MIN_IMAGE_HEIGHT = 300
        
        # ====================================================================
        # HTTP HEADERS - Стандартные заголовки
        # ====================================================================
        
        config_instance.COMMON_HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # ====================================================================
        # DATABASE - Настройки БД
        # ====================================================================
        
        if hasattr(config_instance.database, 'pool_size'):
            config_instance.DB_POOL_SIZE = config_instance.database.pool_size
        
        if hasattr(config_instance.database, 'max_overflow'):
            config_instance.DB_MAX_OVERFLOW = config_instance.database.max_overflow
        
        # ====================================================================
        # RATE LIMITING - Ограничения скорости
        # ====================================================================
        
        if hasattr(config_instance.rate_limiting, 'max_requests_per_minute'):
            config_instance.MAX_REQUESTS_PER_MINUTE = config_instance.rate_limiting.max_requests_per_minute
        
        if hasattr(config_instance.rate_limiting, 'solana_requests_per_second'):
            config_instance.SOLANA_REQUESTS_PER_SECOND = config_instance.rate_limiting.solana_requests_per_second
        
        logger.debug("✓ Свойства обратной совместимости настроены успешно")
        
    except Exception as e:
        logger.error(f"Ошибка при настройке обратной совместимости: {e}", exc_info=True)
        # Не поднимаем исключение - совместимость не критична
        logger.warning("Некоторые старые имена переменных могут быть недоступны")


def get_config_value(config_instance: 'Config', key: str, default=None):
    """
    Универсальный геттер для получения значений конфигурации
    
    Пытается получить значение из конфигурации используя различные
    способы доступа (атрибут, метод, ключ словаря).
    
    Args:
        config_instance: Экземпляр Config
        key: Ключ конфигурации (может быть точечным: 'telegram.bot_token')
        default: Значение по умолчанию если ключ не найден
        
    Returns:
        Значение конфигурации или default
        
    Examples:
        >>> get_config_value(config, 'TELEGRAM_BOT_TOKEN')
        '123456789:ABC...'
        >>> get_config_value(config, 'telegram.bot_token')
        '123456789:ABC...'
        >>> get_config_value(config, 'UNKNOWN_KEY', 'default_value')
        'default_value'
    """
    try:
        # Простой атрибут
        if hasattr(config_instance, key):
            return getattr(config_instance, key, default)
        
        # Точечная нотация (например: 'telegram.bot_token')
        if '.' in key:
            parts = key.split('.')
            obj = config_instance
            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default
            return obj
        
        return default
        
    except Exception as e:
        logger.debug(f"Не удалось получить значение для ключа '{key}': {e}")
        return default


def validate_compatibility(config_instance: 'Config') -> bool:
    """
    Проверка что свойства совместимости настроены корректно
    
    Args:
        config_instance: Экземпляр Config для проверки
        
    Returns:
        True если все критичные свойства доступны
    """
    critical_properties = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHANNEL_ID',
        'ENABLED_CHAINS',
        'WHALE_ENABLED',
        'NEWS_ENABLED',
    ]
    
    missing = []
    for prop in critical_properties:
        if not hasattr(config_instance, prop):
            missing.append(prop)
    
    if missing:
        logger.warning(
            f"Отсутствуют критичные свойства совместимости: {', '.join(missing)}"
        )
        return False
    
    return True