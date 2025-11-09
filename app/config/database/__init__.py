"""
Database Configuration Package
Полная система конфигурации и управления базой данных

Этот пакет предоставляет:
- Конфигурацию БД с валидацией
- Загрузку из различных источников
- Управление соединениями
- Мониторинг и метрики
- Централизованное управление через DatabaseManager

Examples:
    # Базовое использование
    >>> from app.config.database import DatabaseManager
    >>> manager = DatabaseManager()
    >>> await manager.initialize()
    
    # Использование конфигурации
    >>> from app.config.database import DatabaseConfigBase
    >>> config = DatabaseConfigBase.from_env()
    
    # Создание специфичной конфигурации
    >>> from app.config.database import create_postgresql_config
    >>> config = create_postgresql_config(host='localhost', database='mydb')
"""

import logging

# ============================================================================
# BASE COMPONENTS
# ============================================================================

# Enums
from .enums import (
    DatabaseEngine,
    PoolStrategy,
    SSLMode,
    VacuumStrategy,
    BackupType,
    HealthStatus,
    AlertSeverity,
    OperationPriority
)

# Exceptions
from .exceptions import (
    DatabaseConfigError,
    ValidationError,
    DatabaseConnectionError,
    DatabaseValidationError
)

# Protocols
from .protocols import (
    Configurable,
    DatabaseConfigProtocol
)

# ============================================================================
# BASE CLASSES
# ============================================================================

from .base_classes import (
    ConfigSerializer,
    BaseConfig,
    TimedConfig,
    ValidationMixin
)

# ============================================================================
# SUB-CONFIGURATIONS
# ============================================================================

from .sub_configs import (
    PoolConfig,
    SSLConfig,
    TimeoutConfig,
    RetryConfig,
    MonitoringConfig
)

# ============================================================================
# MAIN CONFIGURATION
# ============================================================================

from .database_base import DatabaseConfigBase

# ============================================================================
# BASE MODULE RE-EXPORTS (Factory Functions, Utilities)
# ============================================================================

from .base import (
    # Factory functions
    create_postgresql_config,
    create_sqlite_config,
    create_mysql_config,
    create_config_from_engine,
    
    # Validation helpers
    validate_config,
    validate_multiple_configs,
    check_config_compatibility,
    
    # Migration helpers
    migrate_from_dict,
    export_to_legacy_format,
    
    # Multi-database
    MultiDatabaseConfig,
    
    # Utilities
    get_default_config_for_environment,
    compare_configs,
    test_connection_params
)

# ============================================================================
# LOADERS
# ============================================================================

from .loader import (
    EnvironmentVariableParser,
    EnvironmentLoader,
    DatabaseConfigLoader
)

# ============================================================================
# VALIDATORS
# ============================================================================

from .validators import (
    ValidationIssue,
    ValidationResult,
    BasicValidators,
    NetworkValidators,
    FileSystemValidators,
    DatabaseConfigValidator
)

# ============================================================================
# MANAGER
# ============================================================================

from .manager import (
    ConnectionPoolManager,
    DatabaseMonitoringService,
    DatabaseManager,
    get_db_manager,
    set_db_manager,
    reset_db_manager
)


# ============================================================================
# PACKAGE METADATA
# ============================================================================

__version__ = '2.0.0'
__author__ = 'Crypto Monitor Team'
__all__ = [
    # ===== ENUMS =====
    'DatabaseEngine',
    'PoolStrategy',
    'SSLMode',
    'VacuumStrategy',
    'BackupType',
    'HealthStatus',
    'AlertSeverity',
    'OperationPriority',
    
    # ===== EXCEPTIONS =====
    'DatabaseConfigError',
    'ValidationError',
    'DatabaseConnectionError',
    'DatabaseValidationError',
    
    # ===== PROTOCOLS =====
    'Configurable',
    'DatabaseConfigProtocol',
    
    # ===== BASE CLASSES =====
    'ConfigSerializer',
    'BaseConfig',
    'TimedConfig',
    'ValidationMixin',
    
    # ===== SUB-CONFIGURATIONS =====
    'PoolConfig',
    'SSLConfig',
    'TimeoutConfig',
    'RetryConfig',
    'MonitoringConfig',
    
    # ===== MAIN CONFIGURATION =====
    'DatabaseConfigBase',
    
    # ===== FACTORY FUNCTIONS =====
    'create_postgresql_config',
    'create_sqlite_config',
    'create_mysql_config',
    'create_config_from_engine',
    
    # ===== VALIDATION HELPERS =====
    'validate_config',
    'validate_multiple_configs',
    'check_config_compatibility',
    
    # ===== MIGRATION HELPERS =====
    'migrate_from_dict',
    'export_to_legacy_format',
    
    # ===== MULTI-DATABASE =====
    'MultiDatabaseConfig',
    
    # ===== UTILITIES =====
    'get_default_config_for_environment',
    'compare_configs',
    'test_connection_params',
    
    # ===== LOADERS =====
    'EnvironmentVariableParser',
    'EnvironmentLoader',
    'DatabaseConfigLoader',
    
    # ===== VALIDATORS =====
    'ValidationIssue',
    'ValidationResult',
    'BasicValidators',
    'NetworkValidators',
    'FileSystemValidators',
    'DatabaseConfigValidator',
    
    # ===== MANAGER =====
    'ConnectionPoolManager',
    'DatabaseMonitoringService',
    'DatabaseManager',
    'get_db_manager',
    'set_db_manager',
    'reset_db_manager',
]


# ============================================================================
# PACKAGE INITIALIZATION
# ============================================================================

logger = logging.getLogger(__name__)
logger.debug(f"Database configuration package initialized (v{__version__})")
logger.debug(f"Available exports: {len(__all__)} components")


# ============================================================================
# CONVENIENCE IMPORTS FOR QUICK ACCESS
# ============================================================================

# Shortcut для быстрого доступа к менеджеру
db_manager = get_db_manager


# ============================================================================
# PACKAGE-LEVEL FUNCTIONS
# ============================================================================

def get_package_info() -> dict:
    """
    Получение информации о пакете
    
    Returns:
        Словарь с метаданными пакета
    """
    return {
        'name': 'database',
        'version': __version__,
        'author': __author__,
        'components_count': len(__all__),
        'components': __all__
    }


def validate_installation() -> dict:
    """
    Проверка корректности установки пакета
    
    Returns:
        Словарь с результатами проверки
    """
    results = {
        'status': 'ok',
        'missing_components': [],
        'import_errors': []
    }
    
    # Проверка импорта всех компонентов
    for component_name in __all__:
        try:
            globals()[component_name]
        except KeyError:
            results['missing_components'].append(component_name)
            results['status'] = 'error'
    
    # Проверка основных классов
    critical_components = [
        'DatabaseConfigBase',
        'DatabaseManager',
        'DatabaseConfigLoader',
        'DatabaseConfigValidator'
    ]
    
    for component in critical_components:
        if component in results['missing_components']:
            results['import_errors'].append(
                f"Critical component missing: {component}"
            )
    
    return results


# ============================================================================
# MODULE DOCSTRING EXAMPLES
# ============================================================================

def __example_usage():
    """
    Примеры использования пакета
    
    Эта функция не выполняется, служит только для документации.
    """
    # Пример 1: Базовое использование менеджера
    async def example_basic():
        manager = DatabaseManager()
        await manager.initialize()
        status = manager.get_status()
        print(status)
        await manager.shutdown()
    
    # Пример 2: Создание кастомной конфигурации
    def example_custom_config():
        config = create_postgresql_config(
            host='localhost',
            port=5432,
            database='myapp',
            user='admin',
            password='secret'
        )
        return config
    
    # Пример 3: Загрузка из environment
    def example_env_config():
        loader = DatabaseConfigLoader(prefix='DB_')
        config = loader.load_from_env()
        return config
    
    # Пример 4: Валидация конфигурации
    def example_validation():
        config = DatabaseConfigBase.from_env()
        validator = DatabaseConfigValidator(config)
        result = validator.validate_all()
        
        if not result.is_valid:
            print("Validation errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        return result
    
    # Пример 5: Множественные БД
    def example_multi_db():
        multi = MultiDatabaseConfig()
        
        # Добавление конфигураций
        multi.add('primary', create_postgresql_config(database='main'))
        multi.add('cache', create_sqlite_config(database=':memory:'))
        
        # Получение конфигурации
        primary_config = multi.get('primary')
        
        return multi
    
    # Пример 6: Мониторинг и метрики
    async def example_monitoring():
        manager = DatabaseManager()
        await manager.initialize()
        
        # Получение метрик
        metrics = manager.get_metrics()
        
        # Получение алертов
        alerts = manager.get_alerts(active_only=True)
        
        # Проверка здоровья
        health = manager.get_health_status()
        
        return metrics, alerts, health


# Автоматическая проверка при импорте (только в debug режиме)
if __debug__:
    _install_check = validate_installation()
    if _install_check['status'] != 'ok':
        logger.warning(
            f"Package installation check failed: {_install_check}"
        )