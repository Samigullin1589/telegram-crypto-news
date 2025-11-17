# app/config/initialization.py
"""
Config Initialization Logic
Логика инициализации конфигурации
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigInitializer:
    """
    Инициализатор конфигурации
    
    Отвечает за правильную последовательность инициализации
    всех модулей конфигурации
    """
    
    def initialize(self, config_instance: 'Config'):
        """
        Инициализация всех модулей конфигурации
        
        Args:
            config_instance: Экземпляр Config для инициализации
        """
        from .base_config import BaseConfig
        from .paths_config import PathsConfig
        from .api_config import APIConfig
        from .telegram_config import TelegramConfig
        from .feeds_config import FeedsConfig
        from .blockchain_config import BlockchainConfig
        from .features_config import FeaturesConfig
        from .database_config import DatabaseConfig
        from .rate_limiting_config import RateLimitingConfig
        from .trading_config import TradingConfig
        from .hyperliquid_config import HyperliquidConfig
        from .config_validator import ConfigValidator
        from .config_printer import ConfigPrinter
        
        self._initialize_modules(config_instance)
        self._initialize_helpers(config_instance)
        self._validate_and_print(config_instance)
    
    def _initialize_modules(self, config_instance: 'Config'):
        """
        Инициализация конфигурационных модулей
        
        Порядок важен: базовые модули должны быть инициализированы первыми
        """
        from .base_config import BaseConfig
        from .paths_config import PathsConfig
        from .api_config import APIConfig
        from .telegram_config import TelegramConfig
        from .feeds_config import FeedsConfig
        from .blockchain_config import BlockchainConfig
        from .features_config import FeaturesConfig
        from .database_config import DatabaseConfig
        from .database.enums import DatabaseEngine
        from .rate_limiting_config import RateLimitingConfig
        from .trading_config import TradingConfig
        from .hyperliquid_config import HyperliquidConfig

        logger.debug("Инициализация конфигурационных модулей...")
        
        config_instance.base = BaseConfig()
        logger.debug("✓ BaseConfig")
        
        config_instance.paths = PathsConfig()
        logger.debug("✓ PathsConfig")
        
        config_instance.api = APIConfig()
        logger.debug("✓ APIConfig")
        
        config_instance.telegram = TelegramConfig()
        logger.debug("✓ TelegramConfig")
        
        config_instance.feeds = FeedsConfig()
        logger.debug("✓ FeedsConfig")
        
        config_instance.blockchain = BlockchainConfig()
        logger.debug("✓ BlockchainConfig")
        
        config_instance.features = FeaturesConfig()
        logger.debug("✓ FeaturesConfig")
        
        # База данных - используем from_env для загрузки из окружения
        try:
            config_instance.database = DatabaseConfig.from_env()
            logger.debug("✓ DatabaseConfig (from environment)")
        except Exception as e:
            logger.warning(f"Failed to load DatabaseConfig from env: {e}")
            # Fallback: создаём SQLite конфигурацию с путём из PathsConfig
            config_instance.database = DatabaseConfig(
                engine=DatabaseEngine.SQLITE,
                database=str(config_instance.paths.db_path),
                host="localhost",
                port=5432,
                user="postgres",
                password=""
            )
            logger.debug("✓ DatabaseConfig (fallback to SQLite)")
        
        config_instance.rate_limiting = RateLimitingConfig()
        logger.debug("✓ RateLimitingConfig")

        config_instance.trading = TradingConfig()
        logger.debug("✓ TradingConfig")

        config_instance.hyperliquid = HyperliquidConfig()
        logger.debug("✓ HyperliquidConfig")

        logger.debug("Все модули инициализированы")
    
    def _initialize_helpers(self, config_instance: 'Config'):
        """Инициализация вспомогательных классов"""
        from .config_validator import ConfigValidator
        from .config_printer import ConfigPrinter
        
        logger.debug("Инициализация вспомогательных инструментов...")
        
        config_instance.validator = ConfigValidator(config_instance)
        logger.debug("✓ ConfigValidator")
        
        config_instance.printer = ConfigPrinter(config_instance)
        logger.debug("✓ ConfigPrinter")
    
    def _validate_and_print(self, config_instance: 'Config'):
        """Валидация и вывод информации"""
        try:
            config_instance.printer.print_initialization_header()
            
            validation_results = config_instance.validator.validate()
            
            if validation_results:
                print("\n📋 Результаты валидации:")
                for result in validation_results:
                    print(f"   {result}")
            
            config_instance.printer.print_configuration_summary()
            
        except Exception as e:
            logger.error(f"Ошибка валидации/вывода: {e}", exc_info=True)