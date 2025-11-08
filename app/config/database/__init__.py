"""
Database Configuration Package
Enterprise-grade модульная система конфигурации БД
"""

from .config import DatabaseConfig
from .factory import create_database_config, DatabaseConfigBuilder
from .enums import (
    JournalMode,
    SynchronousMode,
    TempStoreMode,
    LockingMode,
    AutoVacuumMode,
    IsolationLevel,
    CacheEvictionPolicy
)
from .components.pool import DatabaseConnectionPoolConfig
from .components.pragma import DatabasePragmaConfig
from .components.backup import DatabaseBackupConfig
from .components.vacuum import DatabaseVacuumConfig
from .components.cache import DatabaseCacheConfig
from .components.connection import DatabaseConnectionConfig
from .exceptions import (
    DatabaseConfigError,
    ValidationError,
    ConfigurationError
)

__all__ = [
    # Main classes
    'DatabaseConfig',
    'create_database_config',
    'DatabaseConfigBuilder',
    
    # Enums
    'JournalMode',
    'SynchronousMode',
    'TempStoreMode',
    'LockingMode',
    'AutoVacuumMode',
    'IsolationLevel',
    'CacheEvictionPolicy',
    
    # Component configs
    'DatabaseConnectionPoolConfig',
    'DatabasePragmaConfig',
    'DatabaseBackupConfig',
    'DatabaseVacuumConfig',
    'DatabaseCacheConfig',
    'DatabaseConnectionConfig',
    
    # Exceptions
    'DatabaseConfigError',
    'ValidationError',
    'ConfigurationError',
]

__version__ = '2.0.0'