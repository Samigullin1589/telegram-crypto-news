"""
Extended Database Configuration
Расширенная конфигурация БД с интеграцией менеджера и дополнительными возможностями
"""

import logging
from dataclasses import dataclass

from .database_config_core import DatabaseConfig as BaseDatabaseConfig
from .database_config_lifecycle import DatabaseConfigLifecycle
from .database_config_monitoring import DatabaseConfigMonitoring
from .database_config_serialization import DatabaseConfigSerialization
from .database.database_config_loader import DatabaseConfigLoader
from .database.database_config_globals import (
    get_database_config,
    set_database_config,
    reset_database_config,
    has_database_config,
    initialize_database,
    shutdown_database,
    get_database_status,
    restart_database,
    get_database_metrics,
    check_database_health
)

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig(
    BaseDatabaseConfig,
    DatabaseConfigLifecycle,
    DatabaseConfigMonitoring,
    DatabaseConfigSerialization
):
    """
    Полная расширенная конфигурация базы данных
    """
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_") -> "DatabaseConfig":
        """Создание конфигурации из переменных окружения"""
        return DatabaseConfigLoader.from_env(prefix)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "DatabaseConfig":
        """Создание конфигурации из словаря"""
        return DatabaseConfigLoader.from_dict(config_dict)
    
    @classmethod
    def from_url(cls, url: str, **kwargs) -> "DatabaseConfig":
        """Создание конфигурации из URL"""
        return DatabaseConfigLoader.from_url(url, **kwargs)
    
    @classmethod
    def from_file(cls, filepath: str, format: str = None) -> "DatabaseConfig":
        """Загрузка конфигурации из файла"""
        return DatabaseConfigLoader.from_file(filepath, format)


__all__ = [
    'DatabaseConfig',
    'DatabaseConfigLoader',
    'get_database_config',
    'set_database_config',
    'reset_database_config',
    'has_database_config',
    'initialize_database',
    'shutdown_database',
    'get_database_status',
    'restart_database',
    'get_database_metrics',
    'check_database_health'
]

logger.info("Extended database configuration module initialized")