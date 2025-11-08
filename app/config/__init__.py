"""
Configuration Package v3.0
Модульная система конфигурации с правильной архитектурой

Этот пакет предоставляет централизованное управление конфигурацией
всего приложения через паттерн Singleton и композицию модулей.

Основные компоненты:
- Config: Главный класс конфигурации (Singleton)
- Субмодули: api, base, blockchain, database, features, feeds, paths, rate_limiting, telegram
- Валидаторы: Модульная система валидации
- Printer: Красивый вывод конфигурации

Использование:
    from app.config import config
    
    # Доступ к настройкам
    bot_token = config.telegram.bot_token
    enabled_chains = config.blockchain.enabled_chains
    
    # Проверка наличия модулей
    if config.features.whale_enabled:
        ...
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ============================================================================
# ФАЗА 1: ИМПОРТ ВСЕХ СУБМОДУЛЕЙ
# ============================================================================
# Важно: импортируем все субмодули ДО создания главного класса Config
# чтобы избежать циклических зависимостей

from .env_loader import load_environment
from .base_config import BaseConfig
from .paths_config import PathsConfig
from .api_config import APIConfig
from .telegram_config import TelegramConfig
from .feeds_config import FeedsConfig, FeedConfig
from .blockchain_config import BlockchainConfig
from .features_config import FeaturesConfig
from .database_config import DatabaseConfig
from .rate_limiting_config import RateLimitingConfig
from .config_validator import ConfigValidator
from .config_printer import ConfigPrinter

# ============================================================================
# ФАЗА 2: ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================================================
# Загружаем .env файл перед инициализацией конфигурации

try:
    load_environment()
    logger.debug("Переменные окружения загружены")
except Exception as e:
    logger.warning(f"Не удалось загрузить .env файл: {e}")

# ============================================================================
# ФАЗА 3: ОПРЕДЕЛЕНИЕ ГЛАВНОГО КЛАССА CONFIG
# ============================================================================


class Config:
    """
    Главный класс конфигурации системы
    
    Реализует паттерн Singleton для обеспечения единственного
    экземпляра конфигурации во всем приложении.
    
    Использует композицию субмодулей для организации настроек:
    - base: Базовые настройки окружения
    - paths: Пути к файлам и директориям
    - api: API ключи для внешних сервисов
    - telegram: Настройки Telegram бота
    - feeds: Конфигурация RSS фидов
    - blockchain: Настройки блокчейнов и whale мониторинга
    - features: Флаги включения/отключения модулей
    - database: Настройки базы данных
    - rate_limiting: Настройки ограничения скорости запросов
    
    Attributes:
        base: BaseConfig - базовые настройки
        paths: PathsConfig - пути к файлам
        api: APIConfig - API ключи
        telegram: TelegramConfig - Telegram настройки
        feeds: FeedsConfig - RSS фиды
        blockchain: BlockchainConfig - блокчейны
        features: FeaturesConfig - функциональные модули
        database: DatabaseConfig - база данных
        rate_limiting: RateLimitingConfig - rate limiting
        validator: ConfigValidator - валидатор конфигурации
        printer: ConfigPrinter - принтер конфигурации
    """
    
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Config':
        """
        Реализация паттерна Singleton
        
        Гарантирует что в системе существует только один
        экземпляр конфигурации.
        
        Returns:
            Единственный экземпляр Config
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.debug("Создан новый экземпляр Config (Singleton)")
        return cls._instance
    
    def __init__(self):
        """
        Инициализация конфигурации
        
        Выполняется только один раз благодаря флагу _initialized.
        Инициализирует все субмодули, выполняет валидацию и
        выводит информацию о конфигурации.
        """
        # Защита от повторной инициализации
        if self._initialized:
            logger.debug("Config уже инициализирован, пропускаем повторную инициализацию")
            return
        
        logger.info("=" * 80)
        logger.info("🚀 Инициализация Configuration System v3.0")
        logger.info("=" * 80)
        
        try:
            # Инициализация всех субмодулей
            self._initialize_modules()
            
            # Инициализация вспомогательных инструментов
            self._initialize_helpers()
            
            # Валидация и вывод информации
            self._validate_and_print()
            
            # Установка флага успешной инициализации
            self._initialized = True
            
            logger.info("✅ Конфигурация успешно инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка инициализации конфигурации: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось инициализировать конфигурацию: {e}") from e
    
    def _initialize_modules(self) -> None:
        """
        Инициализация всех конфигурационных модулей
        
        Порядок инициализации важен:
        1. base - базовые настройки (нужны для логирования)
        2. paths - пути к файлам (нужны для database)
        3. api - API ключи
        4. telegram - настройки бота
        5. feeds - RSS источники
        6. blockchain - настройки блокчейнов
        7. features - флаги модулей
        8. database - БД (использует paths)
        9. rate_limiting - ограничения
        """
        logger.debug("Инициализация конфигурационных модулей...")
        
        # Базовые настройки - первыми
        self.base = BaseConfig()
        logger.debug("✓ BaseConfig инициализирован")
        
        # Пути - нужны для database
        self.paths = PathsConfig()
        logger.debug("✓ PathsConfig инициализирован")
        
        # API ключи
        self.api = APIConfig()
        logger.debug("✓ APIConfig инициализирован")
        
        # Telegram
        self.telegram = TelegramConfig()
        logger.debug("✓ TelegramConfig инициализирован")
        
        # RSS фиды
        self.feeds = FeedsConfig()
        logger.debug("✓ FeedsConfig инициализирован")
        
        # Блокчейны
        self.blockchain = BlockchainConfig()
        logger.debug("✓ BlockchainConfig инициализирован")
        
        # Функциональные модули
        self.features = FeaturesConfig()
        logger.debug("✓ FeaturesConfig инициализирован")
        
        # База данных (требует paths)
        self.database = DatabaseConfig(self.paths.db_path)
        logger.debug("✓ DatabaseConfig инициализирован")
        
        # Rate limiting
        self.rate_limiting = RateLimitingConfig()
        logger.debug("✓ RateLimitingConfig инициализирован")
        
        logger.debug("Все модули успешно инициализированы")
    
    def _initialize_helpers(self) -> None:
        """
        Инициализация вспомогательных классов
        
        Создает экземпляры валидатора и принтера,
        которые используют главную конфигурацию.
        """
        logger.debug("Инициализация вспомогательных инструментов...")
        
        # Валидатор конфигурации
        self.validator = ConfigValidator(self)
        logger.debug("✓ ConfigValidator инициализирован")
        
        # Принтер конфигурации
        self.printer = ConfigPrinter(self)
        logger.debug("✓ ConfigPrinter инициализирован")
    
    def _validate_and_print(self) -> None:
        """
        Валидация конфигурации и вывод информации
        
        Выполняет полную валидацию всех параметров конфигурации
        и выводит красиво отформатированную информацию.
        """
        try:
            # Заголовок инициализации
            self.printer.print_initialization_header()
            
            # Валидация конфигурации
            validation_results = self.validator.validate()
            
            # Вывод результатов валидации (если есть)
            if validation_results:
                print("\n📋 Результаты валидации конфигурации:")
                for result in validation_results:
                    print(f"   {result}")
            
            # Краткая сводка конфигурации
            self.printer.print_configuration_summary()
            
        except Exception as e:
            logger.error(f"Ошибка во время валидации/вывода: {e}", exc_info=True)
            # Не останавливаем инициализацию из-за ошибок вывода
    
    # ========================================================================
    # API МЕТОДЫ - Удобный доступ к API функционалу
    # ========================================================================
    
    def has_scanner_api_key(self, chain: str) -> bool:
        """
        Проверка наличия API ключа для blockchain scanner
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если API ключ настроен
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
    
    def get_missing_scanner_keys(self) -> List[str]:
        """
        Получение списка блокчейнов без API ключей
        
        Returns:
            Список названий блокчейнов без scanner ключей
        """
        return self.api.get_missing_scanner_keys(self.blockchain.enabled_chains)
    
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
        """Проверка наличия AI провайдера"""
        return self.api.has_ai_provider()
    
    def get_ai_provider(self) -> str:
        """Получение названия активного AI провайдера"""
        return self.api.get_ai_provider()
    
    # ========================================================================
    # BLOCKCHAIN МЕТОДЫ - Удобный доступ к blockchain функционалу
    # ========================================================================
    
    def get_chain_explorer_url(
        self,
        chain: str,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> str:
        """Получение URL blockchain explorer"""
        return self.blockchain.get_explorer_url(chain, address, tx_hash)
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение символа нативной валюты"""
        return self.blockchain.get_chain_symbol(chain)
    
    def get_chain_name(self, chain: str) -> str:
        """Получение полного имени блокчейна"""
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
        """Получение порогов для whale транзакций"""
        return self.blockchain.get_whale_threshold(chain)
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        return self.blockchain.is_whale_transaction(chain, usd_value)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        return self.blockchain.is_mega_whale_transaction(chain, usd_value)
    
    # ========================================================================
    # RSS FEEDS МЕТОДЫ
    # ========================================================================
    
    def get_sorted_feeds(self) -> List[tuple]:
        """Получение отсортированных по приоритету фидов"""
        return self.feeds.get_sorted_feeds()
    
    def get_feed_by_name(self, name: str) -> Optional[FeedConfig]:
        """Получение конфигурации фида по имени"""
        return self.feeds.get_feed_by_name(name)
    
    def get_feed_config(self, name: str) -> Optional[FeedConfig]:
        """Алиас для get_feed_by_name"""
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
    # FEATURES МЕТОДЫ
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
        """Получение статуса всех модулей"""
        return self.features.get_enabled_features()
    
    # ========================================================================
    # AI TEMPLATE
    # ========================================================================
    
    @property
    def ai_prompt_template(self) -> str:
        """Шаблон промпта для AI обработки новостей"""
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
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Преобразует всю конфигурацию в словарь для
        сериализации или отладки.
        
        Returns:
            Словарь со всеми параметрами конфигурации
        """
        try:
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
        except Exception as e:
            logger.error(f"Ошибка сериализации конфигурации: {e}")
            return {}
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        return (
            f"Config("
            f"env={self.base.ENVIRONMENT}, "
            f"chains={len(self.blockchain.enabled_chains)}, "
            f"feeds={len(self.feeds.get_enabled_feeds())}, "
            f"features={sum(1 for v in self.features_enabled.values() if v)}"
            f")"
        )


# ============================================================================
# ФАЗА 4: СОЗДАНИЕ ГЛОБАЛЬНОГО ЭКЗЕМПЛЯРА
# ============================================================================

config = Config()

# ============================================================================
# ФАЗА 5: ОБРАТНАЯ СОВМЕСТИМОСТЬ
# ============================================================================
# Настройка алиасов для старого кода

from .compatibility import setup_compatibility_properties

try:
    setup_compatibility_properties(config)
    logger.debug("Свойства обратной совместимости настроены")
except Exception as e:
    logger.warning(f"Не удалось настроить обратную совместимость: {e}")

# ============================================================================
# ФАЗА 6: ЭКСПОРТ КОНСТАНТ
# ============================================================================

try:
    from .exports import *
    logger.debug("Константы экспортированы")
except ImportError as e:
    logger.warning(f"Не удалось импортировать exports: {e}")

# ============================================================================
# ЭКСПОРТ
# ============================================================================

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
    'ConfigValidator',
    'ConfigPrinter',
]

__version__ = '3.0.0'

logger.info("=" * 80)
logger.info("✅ Configuration Package готов к использованию")
logger.info("=" * 80)