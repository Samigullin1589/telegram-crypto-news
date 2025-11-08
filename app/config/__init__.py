# app/config/__init__.py
"""
Configuration Package
Главный модуль конфигурации с правильной архитектурой без циклических импортов
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# ШАГИ ИНИЦИАЛИЗАЦИИ (в правильном порядке):
# 1. Импорт всех субмодулей конфигурации
# 2. Создание класса Config
# 3. Создание экземпляра config
# 4. Настройка свойств совместимости
# 5. Экспорт констант для обратной совместимости
# ============================================================================


# ============================================================================
# ШАГ 1: Импорт субмодулей (БЕЗ циклических зависимостей)
# ============================================================================

from .base_config import BaseConfig
from .paths_config import PathsConfig
from .api_config import APIConfig
from .telegram_config import TelegramConfig
from .feeds_config import FeedsConfig, FeedConfig
from .blockchain_config import BlockchainConfig
from .features_config import FeaturesConfig
from .database_config import DatabaseConfig
from .rate_limiting_config import RateLimitingConfig


# ============================================================================
# ШАГ 2: Определение главного класса Config
# ============================================================================

class Config:
    """
    Главный класс конфигурации
    
    Объединяет все модули конфигурации и предоставляет единый интерфейс.
    Реализует паттерн Singleton для обеспечения единственного экземпляра.
    
    Архитектура:
    - Композиция субмодулей конфигурации
    - Единая точка доступа к настройкам
    - Валидация при инициализации
    - Обратная совместимость через свойства
    """
    
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Config':
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация главной конфигурации"""
        if self._initialized:
            return
        
        self._print_initialization_header()
        self._initialize_configuration_modules()
        self._validate_configuration()
        self._print_configuration_summary()
        
        self._initialized = True
    
    # ========================================================================
    # Инициализация
    # ========================================================================
    
    def _print_initialization_header(self) -> None:
        """Вывод заголовка инициализации конфигурации"""
        print("\n" + "=" * 80)
        print("⚙️  CRYPTO COMPASS - CONFIGURATION INITIALIZATION v4.2.0")
        print("=" * 80 + "\n")
    
    def _initialize_configuration_modules(self) -> None:
        """
        Инициализация всех модулей конфигурации в правильном порядке
        
        Порядок важен:
        1. Базовая конфигурация (окружение, DEBUG режим)
        2. Пути (зависит от базовой конфигурации)
        3. API ключи
        4. Telegram настройки
        5. RSS фиды
        6. Блокчейн конфигурация
        7. Функциональные флаги
        8. База данных (зависит от путей)
        9. Rate limiting
        """
        logger.info("📦 Инициализация модулей конфигурации...")
        
        # Базовая конфигурация окружения
        self.base = BaseConfig()
        
        # Пути к файлам и директориям
        self.paths = PathsConfig()
        
        # API ключи и эндпоинты
        self.api = APIConfig()
        
        # Telegram конфигурация
        self.telegram = TelegramConfig()
        
        # RSS фиды и источники новостей
        self.feeds = FeedsConfig()
        
        # Блокчейн сети и их параметры
        self.blockchain = BlockchainConfig()
        
        # Функциональные флаги (включение/отключение модулей)
        self.features = FeaturesConfig()
        
        # База данных (зависит от paths)
        self.database = DatabaseConfig(self.paths.db_path)
        
        # Rate limiting для API запросов
        self.rate_limiting = RateLimitingConfig()
        
        logger.info("✅ Все модули конфигурации инициализированы")
    
    # ========================================================================
    # Валидация конфигурации
    # ========================================================================
    
    def _validate_configuration(self) -> None:
        """
        Комплексная валидация конфигурации
        
        Проверяет:
        - Наличие обязательных API ключей
        - Корректность настроек блокчейнов
        - Активные источники новостей
        - AI провайдеры
        - Функциональные модули
        """
        logger.info("🔍 Валидация конфигурации...")
        
        validation_results = []
        
        # Проверка активных фидов
        active_feeds_count = len(self.feeds.get_enabled_feeds())
        if active_feeds_count == 0:
            validation_results.append("⚠️  Нет активных RSS источников новостей")
        
        # Проверка AI провайдера
        if not self.api.has_ai_provider():
            validation_results.append("⚠️  AI провайдер не настроен")
        
        # Проверка API ключей для блокчейн сканеров
        missing_scanner_keys = self.get_missing_scanner_keys()
        if missing_scanner_keys:
            validation_results.append(
                f"⚠️  Отсутствуют API ключи для сканеров: {', '.join(missing_scanner_keys)}"
            )
        
        # Проверка что хотя бы одна функция включена
        if not self.features.is_any_feature_enabled():
            validation_results.append("❌ Все функциональные модули отключены!")
        
        # Вывод результатов валидации
        if validation_results:
            print("\n📋 Результаты валидации:")
            for result in validation_results:
                print(f"   {result}")
        
        logger.info("✅ Валидация завершена")
    
    def _print_configuration_summary(self) -> None:
        """Вывод сводки загруженной конфигурации"""
        print("\n" + "=" * 80)
        print("📊 CONFIGURATION SUMMARY")
        print("=" * 80)
        print(f"   Окружение: {self.base.ENVIRONMENT}")
        print(f"   Debug режим: {self.base.DEBUG}")
        print(f"   Активных RSS фидов: {len(self.feeds.get_enabled_feeds())}")
        print(f"   Включенные блокчейны: {', '.join(self.blockchain.enabled_chains)}")
        print(f"   AI Provider: {self.api.get_ai_provider() or 'Не настроен'}")
        print(f"   База данных: {self.paths.db_path}")
        print("\n   Функциональные модули:")
        print(f"      • Whale Monitor: {'✅ Включен' if self.features.whale_enabled else '❌ Отключен'}")
        print(f"      • News Bot: {'✅ Включен' if self.features.news_enabled else '❌ Отключен'}")
        print(f"      • Analytics: {'✅ Включен' if self.features.analytics_enabled else '❌ Отключен'}")
        print(f"      • Trading System: {'✅ Включен' if self.features.trading_enabled else '❌ Отключен'}")
        print(f"      • Hyperliquid: {'✅ Включен' if self.features.hyperliquid_enabled else '❌ Отключен'}")
        print("=" * 80 + "\n")
    
    # ========================================================================
    # API ключи и сканеры
    # ========================================================================
    
    def has_scanner_api_key(self, chain: str) -> bool:
        """
        Проверка наличия API ключа для blockchain scanner
        
        Args:
            chain: Название блокчейна (ethereum, bsc, polygon, etc.)
        
        Returns:
            True если ключ есть
        """
        return self.api.has_scanner_key(chain)
    
    def get_scanner_api_key(self, chain: str) -> str:
        """
        Получение API ключа для blockchain scanner
        
        Args:
            chain: Название блокчейна
        
        Returns:
            API ключ или пустая строка
        """
        return self.api.get_scanner_key(chain)
    
    def get_missing_scanner_keys(self) -> list:
        """
        Получение списка блокчейнов без API ключей
        
        Returns:
            Список названий блокчейнов
        """
        return self.api.get_missing_scanner_keys(self.blockchain.enabled_chains)
    
    # ========================================================================
    # Проверка наличия API ключей
    # ========================================================================
    
    def has_coingecko(self) -> bool:
        """Проверка наличия CoinGecko API ключа"""
        return bool(self.api.coingecko_api_key)
    
    def has_alchemy(self) -> bool:
        """Проверка наличия Alchemy API ключа"""
        return bool(self.api.alchemy_api_key)
    
    def has_coinmarketcap(self) -> bool:
        """Проверка наличия CoinMarketCap API ключа"""
        return bool(self.api.coinmarketcap_api_key)
    
    def has_ai_provider(self) -> bool:
        """Проверка наличия хотя бы одного AI провайдера"""
        return self.api.has_ai_provider()
    
    def get_ai_provider(self) -> str:
        """Получение названия активного AI провайдера"""
        return self.api.get_ai_provider()
    
    # ========================================================================
    # Методы для работы с блокчейнами
    # ========================================================================
    
    def get_chain_explorer_url(
        self, 
        chain: str, 
        address: Optional[str] = None, 
        tx_hash: Optional[str] = None
    ) -> str:
        """
        Получение URL blockchain explorer
        
        Args:
            chain: Название блокчейна
            address: Адрес кошелька (опционально)
            tx_hash: Хеш транзакции (опционально)
        
        Returns:
            URL эксплорера
        """
        return self.blockchain.get_explorer_url(chain, address, tx_hash)
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение символа нативной валюты блокчейна"""
        return self.blockchain.get_chain_symbol(chain)
    
    def get_chain_name(self, chain: str) -> str:
        """Получение читаемого имени блокчейна"""
        return self.blockchain.get_chain_name(chain)
    
    def get_chain_emoji(self, chain: str) -> str:
        """Получение emoji для блокчейна"""
        return self.blockchain.get_chain_emoji(chain)
    
    def get_chain_color(self, chain: str) -> str:
        """Получение цвета блокчейна"""
        return self.blockchain.get_chain_color(chain)
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return self.blockchain.is_chain_enabled(chain)
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """
        Получение порогов для whale транзакций
        
        Returns:
            Dict с ключами 'whale' и 'mega_whale'
        """
        return self.blockchain.get_whale_threshold(chain)
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        return self.blockchain.is_whale_transaction(chain, usd_value)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        return self.blockchain.is_mega_whale_transaction(chain, usd_value)
    
    # ========================================================================
    # Методы для работы с RSS фидами
    # ========================================================================
    
    def get_sorted_feeds(self) -> list:
        """Получение отсортированных по приоритету фидов"""
        return self.feeds.get_sorted_feeds()
    
    def get_feed_by_name(self, name: str) -> Optional[FeedConfig]:
        """Получение конфигурации фида по имени"""
        return self.feeds.get_feed_by_name(name)
    
    def get_feed_config(self, name: str) -> Optional[FeedConfig]:
        """Получение конфигурации фида (алиас для get_feed_by_name)"""
        return self.feeds.get_feed_by_name(name)
    
    def get_all_feeds(self) -> Dict[str, FeedConfig]:
        """Получение всех фидов"""
        return self.feeds.feeds
    
    def get_enabled_feeds(self) -> Dict[str, FeedConfig]:
        """Получение только активных фидов"""
        return self.feeds.get_enabled_feeds()
    
    def enable_feed(self, name: str) -> None:
        """Включение фида"""
        self.feeds.enable_feed(name)
    
    def disable_feed(self, name: str) -> None:
        """Отключение фида"""
        self.feeds.disable_feed(name)
    
    # ========================================================================
    # Проверка функциональных модулей
    # ========================================================================
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Проверка включен ли функциональный модуль
        
        Args:
            feature_name: Название модуля (whale, news, analytics, trading, hyperliquid)
        
        Returns:
            True если модуль включен
        """
        feature_map = {
            'whale': self.features.whale_enabled,
            'news': self.features.news_enabled,
            'analytics': self.features.analytics_enabled,
            'trading': self.features.trading_enabled,
            'hyperliquid': self.features.hyperliquid_enabled,
        }
        return feature_map.get(feature_name.lower(), False)
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        """Получение статуса всех функциональных модулей"""
        return self.features.get_enabled_features()
    
    # ========================================================================
    # AI Template
    # ========================================================================
    
    @property
    def ai_prompt_template(self) -> str:
        """
        Шаблон промпта для AI обработки новостей
        
        Используется для генерации структурированных постов в Telegram
        """
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
    
    # ========================================================================
    # Сериализация
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Полезно для отладки, логирования и экспорта конфигурации
        
        Returns:
            Словарь со всеми настройками
        """
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


# ============================================================================
# ШАГ 3: Создание единственного экземпляра конфигурации
# ============================================================================

config = Config()


# ============================================================================
# ШАГ 4: Настройка свойств для обратной совместимости
# ============================================================================

from .compatibility import setup_compatibility_properties
setup_compatibility_properties(config)


# ============================================================================
# ШАГ 5: Экспорт констант для обратной совместимости
# ============================================================================

# Импортируем все константы из exports модуля
from .exports import (
    # Telegram
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
    
    # RSS and News
    RSS_FEEDS,
    NEWS_SOURCES,
    FETCH_INTERVAL,
    NEWS_CHECK_INTERVAL,
    POSTS_PER_HOUR_CAP,
    MIN_CONFIDENCE_SCORE,
    
    # Timing
    POST_DELAY_SECONDS,
    IDLE_DELAY_SECONDS,
    
    # Paths
    DB_PATH,
    NEWS_DB_PATH,
    DATA_DIR,
    STATE_FILE,
    WALLET_DB_JSON_PATH,
    
    # Images
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_HEIGHT,
    
    # HTTP
    COMMON_HEADERS,
    
    # Blockchain
    ENABLED_CHAINS,
    MIN_USD,
    
    # Features
    WHALE_ENABLED,
    NEWS_ENABLED,
    ANALYTICS_ENABLED,
    TRADING_ENABLED,
    HYPERLIQUID_ENABLED,
    
    # System
    LOG_LEVEL,
    HEALTH_CHECK_ENABLED,
    PORT,
    HTTP_TIMEOUT,
    RPC_TIMEOUT,
    WEBHOOK_TIMEOUT,
    MAX_MEMORY_MB,
)


# ============================================================================
# Экспорт всех публичных элементов
# ============================================================================

__all__ = [
    # Главные классы
    'config',
    'Config',
    'FeedConfig',
    
    # Субмодули конфигурации
    'BaseConfig',
    'PathsConfig',
    'APIConfig',
    'TelegramConfig',
    'FeedsConfig',
    'BlockchainConfig',
    'FeaturesConfig',
    'DatabaseConfig',
    'RateLimitingConfig',
    
    # Константы для обратной совместимости
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