# core/initialization/__init__.py
"""
Initialization Module
=====================

Модуль инициализации всех компонентов системы.
Предоставляет функциональный API для инициализации.

Public API:
-----------
- validate_environment(): Валидация окружения и загрузка конфигурации
- initialize_database(): Инициализация базы данных
- initialize_monitor(): Инициализация системного монитора

Architecture:
-------------
Модуль использует классы-инициализаторы и предоставляет
функциональный API для упрощения использования.

Classes (внутренние):
---------------------
- EnvironmentInitializer: Валидация окружения
- DatabaseInitializer: Инициализация БД
- MonitorInitializer: Инициализация монитора

Functions (публичные):
----------------------
- validate_environment: Обертка над EnvironmentInitializer
- initialize_database: Обертка над DatabaseInitializer
- initialize_monitor: Обертка над MonitorInitializer
"""

import logging
from typing import Any

from core.initialization.environment import EnvironmentInitializer
from core.initialization.database import DatabaseInitializer
from core.initialization.monitor import MonitorInitializer


logger = logging.getLogger(__name__)


def validate_environment() -> Any:
    """
    Валидация окружения и загрузка конфигурации
    
    Функциональная обертка над EnvironmentInitializer.
    Выполняет валидацию переменных окружения и загружает конфигурацию.
    
    Returns:
        Config: Объект конфигурации приложения
        
    Raises:
        RuntimeError: Если валидация не прошла
        
    Example:
        >>> config = validate_environment()
        >>> print(config.TELEGRAM_BOT_TOKEN)
    """
    logger.debug("Starting environment validation")
    
    try:
        initializer = EnvironmentInitializer()
        config = initializer.validate_and_load()
        
        logger.debug("Environment validation completed successfully")
        return config
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to validate environment: {e}") from e


async def initialize_database() -> Any:
    """
    Инициализация базы данных
    
    Функциональная обертка над DatabaseInitializer.
    Создает подключение к БД, выполняет миграции и настраивает оптимизацию.
    
    Returns:
        DatabaseManager: Менеджер базы данных
        
    Raises:
        RuntimeError: Если инициализация не удалась
        
    Example:
        >>> db_manager = await initialize_database()
        >>> await db_manager.execute("SELECT 1")
    """
    logger.debug("Starting database initialization")
    
    try:
        initializer = DatabaseInitializer()
        db_manager = await initializer.initialize()
        
        logger.debug("Database initialization completed successfully")
        return db_manager
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize database: {e}") from e


async def initialize_monitor(config: Any, db_manager: Any) -> Any:
    """
    Инициализация системного монитора
    
    Функциональная обертка над MonitorInitializer.
    Создает и настраивает системный монитор со всеми компонентами.
    
    Args:
        config: Конфигурация приложения
        db_manager: Менеджер базы данных
        
    Returns:
        IntegratedCryptoMonitor: Системный монитор
        
    Raises:
        RuntimeError: Если инициализация не удалась
        
    Example:
        >>> monitor = await initialize_monitor(config, db_manager)
        >>> status = monitor.get_status()
    """
    logger.debug("Starting monitor initialization")
    
    try:
        initializer = MonitorInitializer(config, db_manager)
        monitor = await initializer.initialize()
        
        logger.debug("Monitor initialization completed successfully")
        return monitor
        
    except Exception as e:
        logger.error(f"Monitor initialization failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize monitor: {e}") from e


# Публичный API
__all__ = [
    # Функции инициализации (основной API)
    'validate_environment',
    'initialize_database',
    'initialize_monitor',
    
    # Классы (для расширения)
    'EnvironmentInitializer',
    'DatabaseInitializer',
    'MonitorInitializer'
]


__version__ = '4.5.0'