"""
Database Configuration Global Instance Management
Управление глобальным экземпляром конфигурации
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_global_db_config: Optional['DatabaseConfig'] = None


# ============================================================================
# GLOBAL MANAGEMENT FUNCTIONS
# ============================================================================

def get_database_config(auto_create: bool = True) -> 'DatabaseConfig':
    """
    Получение глобальной конфигурации БД
    
    Args:
        auto_create: Автоматически создать если не существует
        
    Returns:
        DatabaseConfig инстанс
        
    Raises:
        RuntimeError: Если конфигурация не установлена и auto_create=False
    """
    global _global_db_config
    
    if _global_db_config is None:
        if not auto_create:
            raise RuntimeError("Global database config not set")
        
        logger.info("Creating global database config from environment")
        from .database_config_loader import DatabaseConfigLoader
        _global_db_config = DatabaseConfigLoader.from_env()
    
    return _global_db_config


def set_database_config(config: 'DatabaseConfig') -> None:
    """
    Установка глобальной конфигурации БД
    
    Args:
        config: DatabaseConfig для установки
    """
    global _global_db_config
    
    if _global_db_config is not None:
        logger.warning("Overwriting existing global database config")
    
    _global_db_config = config
    logger.info("Global database config set")


def reset_database_config() -> None:
    """Сброс глобальной конфигурации"""
    global _global_db_config
    _global_db_config = None
    logger.info("Global database config reset")


def has_database_config() -> bool:
    """
    Проверка наличия глобальной конфигурации
    
    Returns:
        True если конфигурация установлена
    """
    return _global_db_config is not None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def initialize_database() -> Dict[str, Any]:
    """
    Инициализация глобальной БД
    
    Returns:
        Результаты инициализации
    """
    config = get_database_config()
    return await config.initialize()


async def shutdown_database() -> Dict[str, Any]:
    """
    Shutdown глобальной БД
    
    Returns:
        Результаты завершения
    """
    if not has_database_config():
        return {'status': 'no_config'}
    
    config = get_database_config(auto_create=False)
    return await config.shutdown()


def get_database_status() -> Dict[str, Any]:
    """
    Получение статуса глобальной БД
    
    Returns:
        Словарь со статусом
    """
    if not has_database_config():
        return {'status': 'no_config'}
    
    config = get_database_config(auto_create=False)
    return config.get_status()


async def restart_database() -> Dict[str, Any]:
    """
    Перезапуск глобальной БД
    
    Returns:
        Результаты перезапуска
    """
    if not has_database_config():
        return {'status': 'no_config'}
    
    config = get_database_config(auto_create=False)
    return await config.restart()


def get_database_metrics() -> Dict[str, Any]:
    """
    Получение метрик глобальной БД
    
    Returns:
        Словарь с метриками
    """
    if not has_database_config():
        return {'status': 'no_config'}
    
    config = get_database_config(auto_create=False)
    return config.get_metrics()


async def check_database_health() -> Dict[str, Any]:
    """
    Проверка здоровья глобальной БД
    
    Returns:
        Результаты проверки
    """
    if not has_database_config():
        return {
            'healthy': False,
            'reason': 'no_config'
        }
    
    config = get_database_config(auto_create=False)
    return await config.health_check()


__all__ = [
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