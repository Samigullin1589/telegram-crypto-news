# app/config/__init__.py
"""
Configuration Package v3.2
Модульная система конфигурации с улучшенной архитектурой

ИСПРАВЛЕНО v3.2:
- Добавлен TradingConfig для поддержки config.trading

Основные компоненты:
- Config: Главный класс конфигурации (Singleton)
- Субмодули: api, base, blockchain, database, features, feeds, paths, rate_limiting, telegram, trading
- Валидаторы: Модульная система валидации
- Printer: Красивый вывод конфигурации
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Импорты для type checking
if TYPE_CHECKING:
    from typing import Dict, Any, Optional, List
    from .feeds_config import FeedConfig

# ============================================================================
# ФАЗА 1: ИМПОРТ ВСЕХ СУБМОДУЛЕЙ
# ============================================================================

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
from .trading_config import TradingConfig
from .hyperliquid_config import HyperliquidConfig
from .config_validator import ConfigValidator
from .config_printer import ConfigPrinter

# ============================================================================
# ФАЗА 2: ИМПОРТ ВНУТРЕННИХ МОДУЛЕЙ
# ============================================================================

from .singleton import SingletonMeta
from .initialization import ConfigInitializer
from .methods import ConfigMethods
from .aliases import ConfigAliases

# ============================================================================
# ФАЗА 3: ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================================================

try:
    load_environment()
    logger.debug("Переменные окружения загружены")
except Exception as e:
    logger.warning(f"Не удалось загрузить .env файл: {e}")

# ============================================================================
# ФАЗА 4: ОПРЕДЕЛЕНИЕ ГЛАВНОГО КЛАССА CONFIG
# ============================================================================


class Config(metaclass=SingletonMeta):
    """
    Главный класс конфигурации системы

    Реализует паттерн Singleton для обеспечения единственного
    экземпляра конфигурации во всем приложении.

    Attributes:
        base: BaseConfig - базовые настройки
        paths: PathsConfig - пути к файлам
        api: APIConfig - API ключи
        telegram: TelegramConfig - Telegram настройки
        feeds: FeedsConfig - RSS фиды (также доступен как news)
        blockchain: BlockchainConfig - блокчейны
        features: FeaturesConfig - функциональные модули
        database: DatabaseConfig - база данных
        rate_limiting: RateLimitingConfig - rate limiting
        trading: TradingConfig - торговая система
        hyperliquid: HyperliquidConfig - конфигурация Hyperliquid DEX
        validator: ConfigValidator - валидатор
        printer: ConfigPrinter - принтер
        news: FeedsConfig - алиас для feeds (обратная совместимость)
    """
    
    def __init__(self):
        """Инициализация конфигурации"""
        
        # Защита от повторной инициализации
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        logger.info("=" * 80)
        logger.info("🚀 Инициализация Configuration System v3.1")
        logger.info("=" * 80)
        
        try:
            # Инициализация через специальный класс
            initializer = ConfigInitializer()
            initializer.initialize(self)
            
            # Настройка алиасов и обратной совместимости
            self._setup_aliases()
            
            # Установка флага
            self._initialized = True
            
            logger.info("✅ Конфигурация успешно инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка инициализации: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось инициализировать конфигурацию: {e}") from e
    
    def _setup_aliases(self):
        """Настройка алиасов для обратной совместимости"""
        try:
            aliases = ConfigAliases(self)
            aliases.setup_all()
            logger.debug("Алиасы настроены")
        except Exception as e:
            logger.warning(f"Ошибка настройки алиасов: {e}")
    
    # ========================================================================
    # API МЕТОДЫ
    # ========================================================================
    
    # Делегируем все методы в ConfigMethods
    def __getattr__(self, name):
        """Динамическое делегирование методов"""
        # Сначала проверяем есть ли метод в ConfigMethods
        methods = ConfigMethods(self)
        if hasattr(methods, name):
            return getattr(methods, name)
        
        # Если нет - стандартная ошибка
        raise AttributeError(f"Config has no attribute '{name}'")
    
    # Явно определяем основные методы для автодополнения IDE
    
    def has_scanner_api_key(self, chain: str) -> bool:
        """Проверка наличия API ключа для blockchain scanner"""
        return ConfigMethods(self).has_scanner_api_key(chain)
    
    def get_scanner_api_key(self, chain: str) -> str:
        """Получение API ключа для blockchain scanner"""
        return ConfigMethods(self).get_scanner_api_key(chain)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Проверка включен ли функциональный модуль"""
        return ConfigMethods(self).is_feature_enabled(feature_name)
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return ConfigMethods(self).is_chain_enabled(chain)
    
    @property
    def features_enabled(self):
        """Получение статуса всех модулей"""
        return self.features.get_enabled_features()
    
    @property
    def ai_prompt_template(self) -> str:
        """Шаблон промпта для AI обработки новостей"""
        return ConfigMethods(self).ai_prompt_template
    
    def to_dict(self):
        """Конвертация конфигурации в словарь"""
        return ConfigMethods(self).to_dict()
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return ConfigMethods(self).__repr__()


# ============================================================================
# ФАЗА 5: СОЗДАНИЕ ГЛОБАЛЬНОГО ЭКЗЕМПЛЯРА
# ============================================================================

config = Config()

# ============================================================================
# ФАЗА 6: НАСТРОЙКА ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================================================

from .compatibility import setup_compatibility_properties

try:
    setup_compatibility_properties(config)
    logger.debug("Обратная совместимость настроена")
except Exception as e:
    logger.warning(f"Ошибка настройки обратной совместимости: {e}")

# ============================================================================
# ФАЗА 7: ЭКСПОРТ КОНСТАНТ
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
    'TradingConfig',
    'HyperliquidConfig',
    'ConfigValidator',
    'ConfigPrinter',
]

__version__ = '3.1.0'

logger.info("=" * 80)
logger.info("✅ Configuration Package готов к использованию")
logger.info("=" * 80)