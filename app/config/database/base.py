"""
Database Configuration Base - Unified Export Module
Единая точка импорта всех компонентов конфигурации БД

Этот модуль обеспечивает обратную совместимость и предоставляет
удобный API для работы со всей системой конфигурации БД.

Structure:
    - Enums: Перечисления для типов БД, режимов и т.д.
    - Exceptions: Иерархия исключений
    - Protocols: Интерфейсы и протоколы
    - Base Classes: Базовые классы конфигурации
    - Sub Configurations: Под-конфигурации (Pool, SSL, Timeouts, etc.)
    - Main Configuration: Основной класс DatabaseConfigBase
    - Factories: Фабричные функции создания конфигураций
    - Validators: Функции валидации
    - Migration: Миграция между форматами
    - Multi-Database: Управление множественными БД
    - Utilities: Утилитарные функции

Examples:
    # Простое использование
    >>> from app.config.database.base import DatabaseConfigBase
    >>> config = DatabaseConfigBase.from_env()
    
    # С кастомными параметрами
    >>> from app.config.database.base import create_postgresql_config
    >>> config = create_postgresql_config(
    ...     host='localhost',
    ...     database='mydb',
    ...     user='admin',
    ...     password='secret'
    ... )
    
    # Из URL
    >>> config = DatabaseConfigBase.from_url(
    ...     'postgresql://user:pass@localhost:5432/mydb'
    ... )
    
    # Множественные БД
    >>> from app.config.database.base import MultiDatabaseConfig
    >>> multi = MultiDatabaseConfig()
    >>> multi.add('primary', create_postgresql_config(...))
    >>> multi.add('cache', create_sqlite_config(...))
"""

import logging

# ============================================================================
# CORE IMPORTS - Базовые компоненты
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
    DatabaseValidationError,
    FieldValidationError,
    TypeValidationError,
    RangeValidationError,
    ConnectionError,
    PoolConnectionError,
    TimeoutError,
    AuthenticationError,
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    ConfigConflictError,
    EnvironmentError,
    MissingEnvironmentError,
    InvalidEnvironmentError,
    ComponentError,
    ComponentInitError,
    ComponentStateError,
    ComponentNotFoundError
)

# Protocols
from .protocols import (
    Configurable,
    DatabaseConfigProtocol
)

# Base Classes
from .base_classes import (
    ConfigSerializer,
    BaseConfig,
    TimedConfig,
    ValidationMixin
)

# Sub Configurations
from .sub_configs import (
    PoolConfig,
    SSLConfig,
    TimeoutConfig,
    RetryConfig,
    MonitoringConfig
)

# Main Configuration
from .database_base import DatabaseConfigBase

# ============================================================================
# FACTORY FUNCTIONS - Создание конфигураций
# ============================================================================

from .base_factories import (
    create_postgresql_config,
    create_sqlite_config,
    create_mysql_config,
    create_config_from_engine,
    create_development_config,
    create_testing_config,
    create_production_config
)

# ============================================================================
# VALIDATION HELPERS - Валидация
# ============================================================================

from .base_validators import (
    validate_config,
    validate_multiple_configs,
    check_config_compatibility,
    check_multiple_configs_compatibility,
    test_connection_params
)

# ============================================================================
# MIGRATION HELPERS - Миграция
# ============================================================================

from .base_migration import (
    migrate_from_dict,
    export_to_legacy_format,
    migrate_from_url,
    migrate_from_env_vars,
    migrate_config_version,
    backup_config,
    restore_config
)

# ============================================================================
# MULTI-DATABASE - Множественные БД
# ============================================================================

from .base_multi import MultiDatabaseConfig

# ============================================================================
# UTILITIES - Утилиты
# ============================================================================

from .base_utils import (
    get_default_config_for_environment,
    compare_configs,
    get_config_diff_summary,
    diagnose_config,
    print_diagnostics,
    clone_config,
    merge_configs,
    discover_configs_in_directory,
    export_config_to_env_file,
    generate_config_documentation
)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# EXPORTS - Полный список экспортируемых компонентов
# ============================================================================

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
    'FieldValidationError',
    'TypeValidationError',
    'RangeValidationError',
    'ConnectionError',
    'PoolConnectionError',
    'TimeoutError',
    'AuthenticationError',
    'ConfigurationError',
    'MissingConfigError',
    'InvalidConfigError',
    'ConfigConflictError',
    'EnvironmentError',
    'MissingEnvironmentError',
    'InvalidEnvironmentError',
    'ComponentError',
    'ComponentInitError',
    'ComponentStateError',
    'ComponentNotFoundError',
    
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
    'create_development_config',
    'create_testing_config',
    'create_production_config',
    
    # ===== VALIDATION HELPERS =====
    'validate_config',
    'validate_multiple_configs',
    'check_config_compatibility',
    'check_multiple_configs_compatibility',
    'test_connection_params',
    
    # ===== MIGRATION HELPERS =====
    'migrate_from_dict',
    'export_to_legacy_format',
    'migrate_from_url',
    'migrate_from_env_vars',
    'migrate_config_version',
    'backup_config',
    'restore_config',
    
    # ===== MULTI-DATABASE =====
    'MultiDatabaseConfig',
    
    # ===== UTILITIES =====
    'get_default_config_for_environment',
    'compare_configs',
    'get_config_diff_summary',
    'diagnose_config',
    'print_diagnostics',
    'clone_config',
    'merge_configs',
    'discover_configs_in_directory',
    'export_config_to_env_file',
    'generate_config_documentation'
]

# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '2.0.0'
__author__ = 'Crypto Monitor Team'

# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

logger.info("Database configuration base module initialized")
logger.debug(f"Version: {__version__}")
logger.debug(f"Available components: {len(__all__)}")

# ============================================================================
# CONVENIENCE SHORTCUTS
# ============================================================================

# Популярные алиасы для быстрого доступа
Config = DatabaseConfigBase
create_config = create_config_from_engine
MultiConfig = MultiDatabaseConfig

# ============================================================================
# MODULE-LEVEL DOCUMENTATION
# ============================================================================

def get_module_info() -> dict:
    """
    Получение информации о модуле
    
    Returns:
        Словарь с метаданными модуля
    """
    return {
        'version': __version__,
        'author': __author__,
        'components_count': len(__all__),
        'components': {
            'enums': 8,
            'exceptions': 19,
            'protocols': 2,
            'base_classes': 4,
            'sub_configs': 5,
            'factories': 7,
            'validators': 5,
            'migration': 7,
            'utilities': 10
        }
    }


def list_all_components() -> list:
    """
    Список всех доступных компонентов
    
    Returns:
        Отсортированный список имён компонентов
    """
    return sorted(__all__)


def get_component_info(component_name: str) -> dict:
    """
    Получение информации о конкретном компоненте
    
    Args:
        component_name: Имя компонента
        
    Returns:
        Словарь с информацией о компоненте
    """
    if component_name not in __all__:
        return {
            'error': f"Component '{component_name}' not found",
            'available': list_all_components()
        }
    
    component = globals().get(component_name)
    
    return {
        'name': component_name,
        'type': type(component).__name__,
        'module': getattr(component, '__module__', 'unknown'),
        'doc': getattr(component, '__doc__', 'No documentation available'),
        'callable': callable(component)
    }


# ============================================================================
# VALIDATION ON IMPORT
# ============================================================================

def _validate_module():
    """Валидация корректности импортов модуля"""
    missing = []
    
    for name in __all__:
        if name not in globals():
            missing.append(name)
    
    if missing:
        logger.error(f"Missing components in module: {missing}")
        raise ImportError(f"Failed to import components: {missing}")
    
    logger.debug("Module validation passed")


# Выполняем валидацию при импорте (только в debug режиме)
if __debug__:
    try:
        _validate_module()
    except ImportError as e:
        logger.error(f"Module validation failed: {e}")
        raise