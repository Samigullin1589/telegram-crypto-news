"""
Database Configuration Factory Functions
Фабричные функции для создания конфигураций различных типов БД
"""

import logging
from typing import Any

from .database_base import DatabaseConfigBase
from .enums import DatabaseEngine
from .exceptions import DatabaseConfigError

logger = logging.getLogger(__name__)


# ============================================================================
# POSTGRESQL FACTORY
# ============================================================================

def create_postgresql_config(
    host: str = "localhost",
    port: int = 5432,
    database: str = "postgres",
    user: str = "postgres",
    password: str = "",
    schema: str = "public",
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для PostgreSQL с разумными defaults
    
    Args:
        host: Хост PostgreSQL сервера
        port: Порт PostgreSQL сервера
        database: Имя базы данных
        user: Имя пользователя
        password: Пароль
        schema: Схема по умолчанию
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация PostgreSQL
        
    Example:
        >>> config = create_postgresql_config(
        ...     host='localhost',
        ...     database='myapp',
        ...     user='admin',
        ...     password='secret'
        ... )
    """
    config_dict = {
        'engine': DatabaseEngine.POSTGRESQL,
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password,
        'schema': schema
    }
    
    # Добавляем дополнительные параметры
    config_dict.update(kwargs)
    
    logger.info(f"Creating PostgreSQL config for {host}:{port}/{database}")
    
    try:
        return DatabaseConfigBase(**config_dict)
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL config: {e}")
        raise DatabaseConfigError(
            f"Failed to create PostgreSQL configuration",
            details={'error': str(e), 'host': host, 'database': database}
        )


# ============================================================================
# SQLITE FACTORY
# ============================================================================

def create_sqlite_config(
    database: str = ":memory:",
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для SQLite
    
    Args:
        database: Путь к файлу БД или :memory: для in-memory
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация SQLite
        
    Example:
        >>> # In-memory database
        >>> config = create_sqlite_config()
        >>> 
        >>> # File database
        >>> config = create_sqlite_config(database='/path/to/db.sqlite')
    """
    config_dict = {
        'engine': DatabaseEngine.SQLITE,
        'host': '',
        'port': 0,
        'database': database,
        'user': '',
        'password': '',
        'schema': ''
    }
    
    # Добавляем дополнительные параметры
    config_dict.update(kwargs)
    
    logger.info(f"Creating SQLite config for {database}")
    
    try:
        return DatabaseConfigBase(**config_dict)
    except Exception as e:
        logger.error(f"Failed to create SQLite config: {e}")
        raise DatabaseConfigError(
            f"Failed to create SQLite configuration",
            details={'error': str(e), 'database': database}
        )


# ============================================================================
# MYSQL FACTORY
# ============================================================================

def create_mysql_config(
    host: str = "localhost",
    port: int = 3306,
    database: str = "mysql",
    user: str = "root",
    password: str = "",
    charset: str = "utf8mb4",
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для MySQL с разумными defaults
    
    Args:
        host: Хост MySQL сервера
        port: Порт MySQL сервера
        database: Имя базы данных
        user: Имя пользователя
        password: Пароль
        charset: Кодировка (utf8mb4 рекомендуется)
        **kwargs: Дополнительные параметры
        
    Returns:
        Настроенная конфигурация MySQL
        
    Example:
        >>> config = create_mysql_config(
        ...     host='localhost',
        ...     database='myapp',
        ...     user='root',
        ...     password='secret'
        ... )
    """
    config_dict = {
        'engine': DatabaseEngine.MYSQL,
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password,
        'charset': charset
    }
    
    # Добавляем дополнительные параметры
    config_dict.update(kwargs)
    
    logger.info(f"Creating MySQL config for {host}:{port}/{database}")
    
    try:
        return DatabaseConfigBase(**config_dict)
    except Exception as e:
        logger.error(f"Failed to create MySQL config: {e}")
        raise DatabaseConfigError(
            f"Failed to create MySQL configuration",
            details={'error': str(e), 'host': host, 'database': database}
        )


# ============================================================================
# GENERIC FACTORY
# ============================================================================

def create_config_from_engine(
    engine: DatabaseEngine,
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации на основе типа движка
    
    Args:
        engine: Тип движка БД
        **kwargs: Параметры конфигурации
        
    Returns:
        Настроенная конфигурация для указанного движка
        
    Raises:
        DatabaseConfigError: Если движок не поддерживается
        
    Example:
        >>> from .enums import DatabaseEngine
        >>> config = create_config_from_engine(
        ...     DatabaseEngine.POSTGRESQL,
        ...     host='localhost',
        ...     database='myapp'
        ... )
    """
    factory_map = {
        DatabaseEngine.POSTGRESQL: create_postgresql_config,
        DatabaseEngine.SQLITE: create_sqlite_config,
        DatabaseEngine.MYSQL: create_mysql_config
    }
    
    factory = factory_map.get(engine)
    if not factory:
        raise DatabaseConfigError(
            f"Unsupported database engine: {engine}",
            details={'engine': engine.value, 'supported': list(factory_map.keys())}
        )
    
    logger.info(f"Creating config for engine: {engine.value}")
    
    return factory(**kwargs)


# ============================================================================
# ENVIRONMENT-SPECIFIC FACTORIES
# ============================================================================

def create_development_config(
    engine: DatabaseEngine = DatabaseEngine.SQLITE,
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для development окружения
    
    Args:
        engine: Тип движка БД
        **kwargs: Дополнительные параметры
        
    Returns:
        Конфигурация для разработки
    """
    defaults = {
        'echo_queries': True,
        'log_slow_queries': True,
    }
    
    # Специфичные настройки для SQLite в dev
    if engine == DatabaseEngine.SQLITE:
        defaults['database'] = ':memory:'
    
    defaults.update(kwargs)
    
    logger.info("Creating development configuration")
    return create_config_from_engine(engine, **defaults)


def create_testing_config(
    engine: DatabaseEngine = DatabaseEngine.SQLITE,
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для testing окружения
    
    Args:
        engine: Тип движка БД
        **kwargs: Дополнительные параметры
        
    Returns:
        Конфигурация для тестирования
    """
    defaults = {
        'echo_queries': False,
    }
    
    # Специфичные настройки для SQLite в тестах
    if engine == DatabaseEngine.SQLITE:
        defaults['database'] = ':memory:'
    
    defaults.update(kwargs)
    
    logger.info("Creating testing configuration")
    return create_config_from_engine(engine, **defaults)


def create_production_config(
    engine: DatabaseEngine,
    **kwargs: Any
) -> DatabaseConfigBase:
    """
    Создание конфигурации для production окружения
    
    Args:
        engine: Тип движка БД
        **kwargs: Параметры конфигурации (обязательны: host, database, user, password)
        
    Returns:
        Конфигурация для production
        
    Raises:
        DatabaseConfigError: Если не указаны обязательные параметры
    """
    # Проверка обязательных параметров
    required_params = ['host', 'database', 'user', 'password']
    missing_params = [p for p in required_params if p not in kwargs]
    
    if missing_params and engine != DatabaseEngine.SQLITE:
        raise DatabaseConfigError(
            f"Missing required parameters for production config",
            details={'missing': missing_params, 'required': required_params}
        )
    
    defaults = {
        'echo_queries': False,
        'log_slow_queries': True,
    }
    
    defaults.update(kwargs)
    
    logger.info("Creating production configuration")
    return create_config_from_engine(engine, **defaults)


__all__ = [
    'create_postgresql_config',
    'create_sqlite_config',
    'create_mysql_config',
    'create_config_from_engine',
    'create_development_config',
    'create_testing_config',
    'create_production_config'
]