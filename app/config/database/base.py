"""
Database Configuration Base - Unified Export Module
Единая точка импорта всех компонентов конфигурации БД

Этот модуль обеспечивает обратную совместимость и предоставляет
удобный API для работы со всей системой конфигурации БД.

Examples:
    # Простое использование
    >>> from app.config.database.base import DatabaseConfigBase
    >>> config = DatabaseConfigBase.from_env()
    
    # С кастомными параметрами
    >>> config = DatabaseConfigBase(
    ...     engine=DatabaseEngine.POSTGRESQL,
    ...     host='localhost',
    ...     database='mydb'
    ... )
    
    # Из URL
    >>> config = DatabaseConfigBase.from_url(
    ...     'postgresql://user:pass@localhost:5432/mydb'
    ... )
"""

import logging
from typing import Dict, Any, Optional, List, Type

# ============================================================================
# IMPORTS - Импорт всех компонентов
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

logger = logging.getLogger(__name__)


# ============================================================================
# FACTORY FUNCTIONS - Фабричные функции для создания конфигураций
# ============================================================================

def create_postgresql_config(
    host: str = "localhost",
    port: int = 5432,
    database: str = "postgres",
    user: str = "postgres",
    password: str = "",
    **kwargs
) -> DatabaseConfigBase:
    """
    Создание конфигурации для PostgreSQL с разумными defaults
    
    Args:
        host: Хост PostgreSQL сервера
        port: Порт PostgreSQL сервера
        database: Имя базы данных
        user: Имя пользователя
        password: Пароль
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация PostgreSQL
    """
    config_dict = {
        'engine': DatabaseEngine.POSTGRESQL,
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password
    }
    config_dict.update(kwargs)
    
    logger.info(f"Creating PostgreSQL config for {host}:{port}/{database}")
    return DatabaseConfigBase(**config_dict)


def create_sqlite_config(
    database: str = ":memory:",
    **kwargs
) -> DatabaseConfigBase:
    """
    Создание конфигурации для SQLite
    
    Args:
        database: Путь к файлу БД или :memory: для in-memory
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация SQLite
    """
    config_dict = {
        'engine': DatabaseEngine.SQLITE,
        'host': '',
        'port': 0,
        'database': database,
        'user': '',
        'password': ''
    }
    config_dict.update(kwargs)
    
    logger.info(f"Creating SQLite config for {database}")
    return DatabaseConfigBase(**config_dict)


def create_mysql_config(
    host: str = "localhost",
    port: int = 3306,
    database: str = "mysql",
    user: str = "root",
    password: str = "",
    **kwargs
) -> DatabaseConfigBase:
    """
    Создание конфигурации для MySQL с разумными defaults
    
    Args:
        host: Хост MySQL сервера
        port: Порт MySQL сервера
        database: Имя базы данных
        user: Имя пользователя
        password: Пароль
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация MySQL
    """
    config_dict = {
        'engine': DatabaseEngine.MYSQL,
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password
    }
    config_dict.update(kwargs)
    
    logger.info(f"Creating MySQL config for {host}:{port}/{database}")
    return DatabaseConfigBase(**config_dict)


def create_config_from_engine(
    engine: DatabaseEngine,
    **kwargs
) -> DatabaseConfigBase:
    """
    Создание конфигурации на основе типа движка
    
    Args:
        engine: Тип движка БД
        **kwargs: Параметры конфигурации
        
    Returns:
        Настроенная конфигурация для указанного движка
    """
    factory_map = {
        DatabaseEngine.POSTGRESQL: create_postgresql_config,
        DatabaseEngine.SQLITE: create_sqlite_config,
        DatabaseEngine.MYSQL: create_mysql_config
    }
    
    factory = factory_map.get(engine)
    if not factory:
        raise DatabaseConfigError(f"Unsupported database engine: {engine}")
    
    return factory(**kwargs)


# ============================================================================
# VALIDATION HELPERS - Вспомогательные функции валидации
# ============================================================================

def validate_config(config: DatabaseConfigBase) -> bool:
    """
    Валидация конфигурации БД
    
    Args:
        config: Конфигурация для валидации
        
    Returns:
        True если конфигурация валидна
        
    Raises:
        ValidationError: При ошибках валидации
    """
    try:
        return config.validate()
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


def validate_multiple_configs(
    configs: List[DatabaseConfigBase]
) -> Dict[str, bool]:
    """
    Валидация нескольких конфигураций
    
    Args:
        configs: Список конфигураций для валидации
        
    Returns:
        Словарь с результатами валидации для каждой конфигурации
    """
    results = {}
    
    for i, config in enumerate(configs):
        config_id = f"config_{i}_{config.database}"
        try:
            results[config_id] = validate_config(config)
        except ValidationError as e:
            results[config_id] = False
            logger.error(f"Config {config_id} validation failed: {e}")
    
    return results


def check_config_compatibility(
    config1: DatabaseConfigBase,
    config2: DatabaseConfigBase
) -> Dict[str, Any]:
    """
    Проверка совместимости двух конфигураций
    
    Args:
        config1: Первая конфигурация
        config2: Вторая конфигурация
        
    Returns:
        Словарь с результатами проверки совместимости
    """
    compatibility = {
        'same_engine': config1.engine == config2.engine,
        'same_host': config1.host == config2.host,
        'same_port': config1.port == config2.port,
        'different_database': config1.database != config2.database,
        'compatible': True,
        'issues': []
    }
    
    # Проверки совместимости
    if config1.engine != config2.engine:
        compatibility['issues'].append("Different database engines")
    
    if config1.host == config2.host and config1.port == config2.port and config1.database == config2.database:
        compatibility['compatible'] = False
        compatibility['issues'].append("Identical connection parameters - potential conflict")
    
    return compatibility


# ============================================================================
# MIGRATION HELPERS - Помощники для миграции
# ============================================================================

def migrate_from_dict(old_config: Dict[str, Any]) -> DatabaseConfigBase:
    """
    Миграция из старого формата словаря в новую конфигурацию
    
    Args:
        old_config: Словарь со старой конфигурацией
        
    Returns:
        Новая конфигурация DatabaseConfigBase
    """
    logger.info("Migrating configuration from dict format")
    
    # Mapping старых ключей на новые
    key_mapping = {
        'db_host': 'host',
        'db_port': 'port',
        'db_name': 'database',
        'db_user': 'user',
        'db_password': 'password',
        'db_engine': 'engine'
    }
    
    # Преобразуем ключи
    new_config = {}
    for old_key, value in old_config.items():
        new_key = key_mapping.get(old_key, old_key)
        new_config[new_key] = value
    
    # Преобразуем engine если это строка
    if 'engine' in new_config and isinstance(new_config['engine'], str):
        new_config['engine'] = DatabaseEngine(new_config['engine'])
    
    return DatabaseConfigBase(**new_config)


def export_to_legacy_format(config: DatabaseConfigBase) -> Dict[str, Any]:
    """
    Экспорт конфигурации в legacy формат для обратной совместимости
    
    Args:
        config: Современная конфигурация
        
    Returns:
        Словарь в старом формате
    """
    return {
        'db_engine': config.engine.value,
        'db_host': config.host,
        'db_port': config.port,
        'db_name': config.database,
        'db_user': config.user,
        'db_password': config.password,
        'db_schema': config.schema,
        'pool_min': config.pool.min_size,
        'pool_max': config.pool.max_size,
        'timeout': config.timeouts.query_timeout
    }


# ============================================================================
# MULTI-DATABASE HELPERS - Работа с несколькими БД
# ============================================================================

class MultiDatabaseConfig:
    """
    Менеджер конфигураций для множественных баз данных
    
    Используется когда приложение работает с несколькими БД одновременно.
    
    Example:
        >>> multi_config = MultiDatabaseConfig()
        >>> multi_config.add('primary', create_postgresql_config(...))
        >>> multi_config.add('cache', create_sqlite_config(...))
        >>> primary = multi_config.get('primary')
    """
    
    def __init__(self):
        """Инициализация менеджера конфигураций"""
        self._configs: Dict[str, DatabaseConfigBase] = {}
        self._default_name: Optional[str] = None
        logger.debug("MultiDatabaseConfig initialized")
    
    def add(
        self,
        name: str,
        config: DatabaseConfigBase,
        set_as_default: bool = False
    ) -> None:
        """
        Добавление конфигурации
        
        Args:
            name: Имя конфигурации
            config: Конфигурация БД
            set_as_default: Установить как конфигурацию по умолчанию
        """
        if name in self._configs:
            logger.warning(f"Overwriting existing config: {name}")
        
        self._configs[name] = config
        logger.info(f"Added database config: {name}")
        
        if set_as_default or self._default_name is None:
            self._default_name = name
            logger.info(f"Set default database config: {name}")
    
    def get(self, name: Optional[str] = None) -> DatabaseConfigBase:
        """
        Получение конфигурации по имени
        
        Args:
            name: Имя конфигурации (None = default)
            
        Returns:
            Конфигурация БД
            
        Raises:
            KeyError: Если конфигурация не найдена
        """
        if name is None:
            if self._default_name is None:
                raise KeyError("No default database config set")
            name = self._default_name
        
        if name not in self._configs:
            raise KeyError(f"Database config not found: {name}")
        
        return self._configs[name]
    
    def remove(self, name: str) -> None:
        """
        Удаление конфигурации
        
        Args:
            name: Имя конфигурации для удаления
        """
        if name in self._configs:
            del self._configs[name]
            logger.info(f"Removed database config: {name}")
            
            if self._default_name == name:
                self._default_name = None
                logger.warning("Removed default config, no default set now")
    
    def list_configs(self) -> List[str]:
        """
        Получение списка всех конфигураций
        
        Returns:
            Список имён конфигураций
        """
        return list(self._configs.keys())
    
    def get_all(self) -> Dict[str, DatabaseConfigBase]:
        """
        Получение всех конфигураций
        
        Returns:
            Словарь всех конфигураций
        """
        return self._configs.copy()
    
    def validate_all(self) -> Dict[str, bool]:
        """
        Валидация всех конфигураций
        
        Returns:
            Словарь с результатами валидации
        """
        return validate_multiple_configs(list(self._configs.values()))
    
    def __len__(self) -> int:
        """Количество конфигураций"""
        return len(self._configs)
    
    def __contains__(self, name: str) -> bool:
        """Проверка наличия конфигурации"""
        return name in self._configs
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return f"MultiDatabaseConfig(configs={len(self._configs)}, default='{self._default_name}')"


# ============================================================================
# UTILITY FUNCTIONS - Утилитарные функции
# ============================================================================

def get_default_config_for_environment(
    environment: str = "development"
) -> DatabaseConfigBase:
    """
    Получение конфигурации по умолчанию для окружения
    
    Args:
        environment: Название окружения (development/testing/production)
        
    Returns:
        Конфигурация с настройками для окружения
    """
    env_configs = {
        'development': {
            'echo_queries': True,
            'pool': PoolConfig(min_size=2, max_size=5),
            'monitoring': MonitoringConfig(enabled=False)
        },
        'testing': {
            'echo_queries': False,
            'pool': PoolConfig(min_size=1, max_size=3),
            'monitoring': MonitoringConfig(enabled=False)
        },
        'production': {
            'echo_queries': False,
            'log_slow_queries': True,
            'pool': PoolConfig(min_size=10, max_size=50),
            'monitoring': MonitoringConfig(enabled=True),
            'retry': RetryConfig(enabled=True, max_attempts=5)
        }
    }
    
    config_params = env_configs.get(environment.lower(), env_configs['development'])
    
    # Загружаем базовую конфигурацию из env
    config = DatabaseConfigBase.from_env()
    
    # Обновляем параметрами окружения
    config.update_from_dict(config_params, validate=True)
    
    logger.info(f"Created config for environment: {environment}")
    return config


def compare_configs(
    config1: DatabaseConfigBase,
    config2: DatabaseConfigBase
) -> Dict[str, Any]:
    """
    Сравнение двух конфигураций и получение различий
    
    Args:
        config1: Первая конфигурация
        config2: Вторая конфигурация
        
    Returns:
        Словарь с различиями
    """
    dict1 = config1.to_dict(mask_sensitive=False)
    dict2 = config2.to_dict(mask_sensitive=False)
    
    differences = {
        'equal': config1 == config2,
        'differences': {}
    }
    
    # Находим различия
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        val1 = dict1.get(key)
        val2 = dict2.get(key)
        
        if val1 != val2:
            differences['differences'][key] = {
                'config1': val1,
                'config2': val2
            }
    
    return differences


def test_connection_params(config: DatabaseConfigBase) -> Dict[str, Any]:
    """
    Тестирование параметров подключения (без фактического подключения)
    
    Args:
        config: Конфигурация для тестирования
        
    Returns:
        Словарь с результатами тестирования
    """
    results = {
        'valid': False,
        'connection_string': None,
        'diagnostic_info': None,
        'errors': []
    }
    
    try:
        # Валидация конфигурации
        config.validate()
        
        # Получение строки подключения
        results['connection_string'] = config.test_connection_string()
        
        # Диагностическая информация
        results['diagnostic_info'] = config.get_diagnostic_info()
        
        results['valid'] = True
        logger.info("Connection parameters test passed")
        
    except ValidationError as e:
        results['errors'].append(f"Validation error: {e}")
        logger.error(f"Connection parameters test failed: {e}")
    except Exception as e:
        results['errors'].append(f"Unexpected error: {e}")
        logger.error(f"Unexpected error during connection test: {e}")
    
    return results


# ============================================================================
# EXPORTS - Экспорт всех компонентов
# ============================================================================

__all__ = [
    # Enums
    'DatabaseEngine',
    'PoolStrategy',
    'SSLMode',
    'VacuumStrategy',
    'BackupType',
    'HealthStatus',
    'AlertSeverity',
    'OperationPriority',
    
    # Exceptions
    'DatabaseConfigError',
    'ValidationError',
    'DatabaseConnectionError',
    'DatabaseValidationError',
    
    # Protocols
    'Configurable',
    'DatabaseConfigProtocol',
    
    # Base Classes
    'ConfigSerializer',
    'BaseConfig',
    'TimedConfig',
    'ValidationMixin',
    
    # Sub Configurations
    'PoolConfig',
    'SSLConfig',
    'TimeoutConfig',
    'RetryConfig',
    'MonitoringConfig',
    
    # Main Configuration
    'DatabaseConfigBase',
    
    # Factory Functions
    'create_postgresql_config',
    'create_sqlite_config',
    'create_mysql_config',
    'create_config_from_engine',
    
    # Validation Helpers
    'validate_config',
    'validate_multiple_configs',
    'check_config_compatibility',
    
    # Migration Helpers
    'migrate_from_dict',
    'export_to_legacy_format',
    
    # Multi-Database
    'MultiDatabaseConfig',
    
    # Utilities
    'get_default_config_for_environment',
    'compare_configs',
    'test_connection_params'
]


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

logger.info("Database configuration module initialized")
logger.debug(f"Available components: {len(__all__)}")