"""
Extended Database Configuration
Расширенная конфигурация БД с интеграцией менеджера и дополнительными возможностями

Этот модуль объединяет все компоненты расширенной конфигурации:
- Основной класс DatabaseConfig
- Управление жизненным циклом
- Мониторинг и метрики
- Сериализация
- Загрузка из источников
- Глобальное управление
"""

import logging
from dataclasses import dataclass

from .database_config_core import DatabaseConfig as BaseDatabaseConfig
from .database_config_lifecycle import DatabaseConfigLifecycle
from .database_config_monitoring import DatabaseConfigMonitoring
from .database_config_serialization import DatabaseConfigSerialization
from .database_config_loader import DatabaseConfigLoader
from .database_config_globals import (
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


# ============================================================================
# MAIN DATABASE CONFIG CLASS
# ============================================================================

@dataclass
class DatabaseConfig(
    BaseDatabaseConfig,
    DatabaseConfigLifecycle,
    DatabaseConfigMonitoring,
    DatabaseConfigSerialization
):
    """
    Полная расширенная конфигурация базы данных
    
    Объединяет все возможности:
    - Базовая конфигурация подключения (от DatabaseConfigBase)
    - Управление жизненным циклом (initialize, shutdown, restart)
    - Мониторинг и метрики (status, health, alerts)
    - Сериализация (to_dict, to_json, to_yaml)
    - Интеграция с DatabaseManager
    
    Example:
        >>> # Загрузка из environment
        >>> config = DatabaseConfig.from_env()
        >>> await config.initialize()
        >>> 
        >>> # Получение статуса
        >>> status = config.get_status()
        >>> health = config.get_health_status()
        >>> 
        >>> # Мониторинг
        >>> metrics = config.get_metrics()
        >>> alerts = config.get_alerts()
        >>> 
        >>> # Завершение
        >>> await config.shutdown()
    """
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_") -> "DatabaseConfig":
        """
        Создание конфигурации из переменных окружения
        
        Args:
            prefix: Префикс для переменных окружения
            
        Returns:
            Инстанс DatabaseConfig
        """
        return DatabaseConfigLoader.from_env(prefix)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "DatabaseConfig":
        """
        Создание конфигурации из словаря
        
        Args:
            config_dict: Словарь с параметрами
            
        Returns:
            Инстанс DatabaseConfig
        """
        return DatabaseConfigLoader.from_dict(config_dict)
    
    @classmethod
    def from_url(cls, url: str, **kwargs) -> "DatabaseConfig":
        """
        Создание конфигурации из URL
        
        Args:
            url: URL подключения
            **kwargs: Дополнительные параметры
            
        Returns:
            Инстанс DatabaseConfig
        """
        return DatabaseConfigLoader.from_url(url, **kwargs)
    
    @classmethod
    def from_file(cls, filepath: str, format: str = None) -> "DatabaseConfig":
        """
        Загрузка конфигурации из файла
        
        Args:
            filepath: Путь к файлу
            format: Формат файла ('json' или 'yaml')
            
        Returns:
            Инстанс DatabaseConfig
        """
        return DatabaseConfigLoader.from_file(filepath, format)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Main class
    'DatabaseConfig',
    
    # Loader
    'DatabaseConfigLoader',
    
    # Global instance management
    'get_database_config',
    'set_database_config',
    'reset_database_config',
    'has_database_config',
    
    # Convenience functions
    'initialize_database',
    'shutdown_database',
    'get_database_status',
    'restart_database',
    'get_database_metrics',
    'check_database_health'
]


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

logger.info("Extended database configuration module initialized")