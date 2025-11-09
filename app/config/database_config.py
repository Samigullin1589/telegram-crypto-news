"""
Extended Database Configuration
Расширенная конфигурация БД с интеграцией менеджера и дополнительными возможностями
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .database.base import DatabaseConfigBase
from .database.enums import DatabaseEngine, HealthStatus
from .database.loader import DatabaseConfigLoader, EnvironmentLoader
from .database.manager import DatabaseManager, get_db_manager
from .database.validators import DatabaseConfigValidator
from .database.exceptions import ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# EXTENDED DATABASE CONFIGURATION
# ============================================================================

@dataclass
class DatabaseConfig(DatabaseConfigBase):
    """
    Расширенная конфигурация базы данных
    
    Наследует все базовые параметры подключения и добавляет:
    - Интеграцию с DatabaseManager
    - Дополнительные флаги управления
    - Удобные методы для работы с менеджером
    - Автоматическую инициализацию компонентов
    
    Attributes:
        enable_manager: Автоматически создавать менеджер
        auto_initialize: Автоматическая инициализация при создании
        enable_health_checks: Включить проверки здоровья
        health_check_interval_seconds: Интервал проверок здоровья
    
    Example:
        >>> config = DatabaseConfig.from_env()
        >>> await config.initialize()
        >>> status = config.get_status()
        >>> await config.shutdown()
    """
    
    # ===== Управление менеджером =====
    enable_manager: bool = True
    auto_initialize: bool = False
    
    # ===== Проверки здоровья =====
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 300
    
    # ===== Автоматическое обслуживание =====
    enable_auto_vacuum: bool = True
    enable_auto_analyze: bool = True
    enable_auto_backup: bool = False
    backup_retention_days: int = 7
    
    # ===== Дополнительные опции =====
    enable_query_logging: bool = False
    enable_performance_tracking: bool = True
    enable_connection_pooling: bool = True
    
    # ===== Приватные поля =====
    _manager: Optional[DatabaseManager] = field(default=None, init=False, repr=False)
    _initialized: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        """Пост-инициализация с автоматическим созданием менеджера"""
        # Вызываем родительскую валидацию
        super().__post_init__()
        
        # Создаём менеджер если требуется
        if self.enable_manager:
            self._create_manager()
        
        logger.debug(
            f"DatabaseConfig initialized: "
            f"{self.engine.value}://{self.host}:{self.port}/{self.database}"
        )
    
    def _create_manager(self) -> None:
        """Создание менеджера БД"""
        if self._manager is None:
            try:
                self._manager = DatabaseManager(
                    config=self,
                    enable_monitoring=self.monitoring.enabled
                )
                logger.debug("DatabaseManager created successfully")
            except Exception as e:
                logger.error(f"Failed to create DatabaseManager: {e}", exc_info=True)
                raise
    
    @property
    def manager(self) -> DatabaseManager:
        """
        Получение менеджера БД (lazy creation)
        
        Returns:
            DatabaseManager инстанс
        """
        if self._manager is None:
            self._create_manager()
        
        return self._manager
    
    @property
    def is_initialized(self) -> bool:
        """Проверка инициализации"""
        return self._initialized
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Инициализация конфигурации и менеджера
        
        Returns:
            Результаты инициализации
        """
        if self._initialized:
            logger.warning("DatabaseConfig already initialized")
            return {'status': 'already_initialized'}
        
        logger.info("Initializing DatabaseConfig")
        
        results = {
            'status': 'initializing',
            'config': {
                'engine': self.engine.value,
                'host': self.host,
                'database': self.database
            }
        }
        
        try:
            # Инициализация менеджера если включен
            if self.enable_manager:
                manager_results = await self.manager.initialize()
                results['manager'] = manager_results
            
            self._initialized = True
            results['status'] = 'initialized'
            
            logger.info("DatabaseConfig initialized successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseConfig initialization failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['error'] = str(e)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение полного статуса конфигурации и менеджера
        
        Returns:
            Словарь со статусом
        """
        status = {
            'initialized': self._initialized,
            'config': self.to_dict(mask_sensitive=True),
            'diagnostic_info': self.get_diagnostic_info()
        }
        
        # Добавляем статус менеджера если есть
        if self._manager is not None:
            status['manager'] = self.manager.get_status()
            status['health'] = self.manager.get_health_status().value
        else:
            status['manager'] = None
            status['health'] = 'unknown'
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик конфигурации и менеджера
        
        Returns:
            Словарь с метриками
        """
        metrics = {
            'config': {
                'engine': self.engine.value,
                'pool_size': f"{self.pool.min_size}-{self.pool.max_size}",
                'ssl_enabled': self.ssl.enabled,
                'monitoring_enabled': self.monitoring.enabled
            }
        }
        
        # Добавляем метрики менеджера если есть
        if self._manager is not None:
            metrics['manager'] = self.manager.get_metrics()
        
        return metrics
    
    def get_health_status(self) -> HealthStatus:
        """
        Получение статуса здоровья
        
        Returns:
            Статус здоровья системы
        """
        if not self._initialized:
            return HealthStatus.UNKNOWN
        
        if self._manager is not None:
            return self.manager.get_health_status()
        
        return HealthStatus.HEALTHY
    
    def get_alerts(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Получение алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Словарь с алертами
        """
        if self._manager is None:
            return {'alerts': [], 'total': 0}
        
        return self.manager.get_alerts(active_only)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Выполнение проверки здоровья
        
        Returns:
            Результаты проверки
        """
        if self._manager is None:
            return {
                'healthy': False,
                'reason': 'manager_not_initialized'
            }
        
        return await self.manager.health_check()
    
    async def shutdown(self) -> Dict[str, Any]:
        """
        Graceful shutdown конфигурации и менеджера
        
        Returns:
            Результаты завершения
        """
        if not self._initialized:
            logger.warning("DatabaseConfig not initialized, nothing to shutdown")
            return {'status': 'not_initialized'}
        
        logger.info("Starting DatabaseConfig shutdown")
        
        results = {
            'status': 'shutting_down'
        }
        
        try:
            # Shutdown менеджера если есть
            if self._manager is not None:
                manager_results = await self.manager.shutdown()
                results['manager'] = manager_results
            
            self._initialized = False
            results['status'] = 'shutdown_complete'
            
            logger.info("DatabaseConfig shutdown complete")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseConfig shutdown error: {e}", exc_info=True)
            results['status'] = 'shutdown_error'
            results['error'] = str(e)
            return results
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_") -> "DatabaseConfig":
        """
        Создание конфигурации из переменных окружения
        
        Args:
            prefix: Префикс для переменных окружения
            
        Returns:
            Инстанс DatabaseConfig
        """
        logger.info(f"Loading DatabaseConfig from environment (prefix: {prefix})")
        
        # Загружаем базовые параметры через loader
        loader = DatabaseConfigLoader(prefix)
        base_config = loader.load_from_env()
        
        # Загружаем дополнительные параметры
        env_loader = EnvironmentLoader(prefix)
        
        # Собираем все параметры
        config_dict = base_config.to_dict(mask_sensitive=False)
        
        # Добавляем расширенные параметры
        config_dict.update({
            'enable_manager': env_loader.get_bool('ENABLE_MANAGER', True),
            'auto_initialize': env_loader.get_bool('AUTO_INITIALIZE', False),
            'enable_health_checks': env_loader.get_bool('ENABLE_HEALTH_CHECKS', True),
            'health_check_interval_seconds': env_loader.get_int(
                'HEALTH_CHECK_INTERVAL', 300, min_value=30
            ),
            'enable_auto_vacuum': env_loader.get_bool('ENABLE_AUTO_VACUUM', True),
            'enable_auto_analyze': env_loader.get_bool('ENABLE_AUTO_ANALYZE', True),
            'enable_auto_backup': env_loader.get_bool('ENABLE_AUTO_BACKUP', False),
            'backup_retention_days': env_loader.get_int(
                'BACKUP_RETENTION_DAYS', 7, min_value=1
            ),
            'enable_query_logging': env_loader.get_bool('ENABLE_QUERY_LOGGING', False),
            'enable_performance_tracking': env_loader.get_bool(
                'ENABLE_PERFORMANCE_TRACKING', True
            ),
            'enable_connection_pooling': env_loader.get_bool(
                'ENABLE_CONNECTION_POOLING', True
            )
        })
        
        config = cls(**config_dict)
        
        logger.info(f"DatabaseConfig loaded from environment successfully")
        
        return config
    
    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Args:
            mask_sensitive: Маскировать чувствительные поля
            
        Returns:
            Словарь с конфигурацией
        """
        # Получаем базовый словарь
        base_dict = super().to_dict(mask_sensitive)
        
        # Добавляем расширенные параметры
        base_dict.update({
            'enable_manager': self.enable_manager,
            'auto_initialize': self.auto_initialize,
            'enable_health_checks': self.enable_health_checks,
            'health_check_interval_seconds': self.health_check_interval_seconds,
            'enable_auto_vacuum': self.enable_auto_vacuum,
            'enable_auto_analyze': self.enable_auto_analyze,
            'enable_auto_backup': self.enable_auto_backup,
            'backup_retention_days': self.backup_retention_days,
            'enable_query_logging': self.enable_query_logging,
            'enable_performance_tracking': self.enable_performance_tracking,
            'enable_connection_pooling': self.enable_connection_pooling,
            'is_initialized': self._initialized
        })
        
        return base_dict
    
    def validate(self) -> bool:
        """
        Полная валидация конфигурации
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При ошибках валидации
        """
        # Базовая валидация
        super().validate()
        
        # Дополнительная валидация расширенных параметров
        if self.health_check_interval_seconds < 30:
            raise ValidationError(
                "health_check_interval_seconds must be >= 30"
            )
        
        if self.backup_retention_days < 1:
            raise ValidationError(
                "backup_retention_days must be >= 1"
            )
        
        return True
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"DatabaseConfig("
            f"engine={self.engine.value}, "
            f"host={self.host}, "
            f"database={self.database}, "
            f"initialized={self._initialized}, "
            f"manager_enabled={self.enable_manager}"
            f")"
        )


# ============================================================================
# GLOBAL INSTANCE MANAGEMENT
# ============================================================================

_global_db_config: Optional[DatabaseConfig] = None


def get_database_config(auto_create: bool = True) -> DatabaseConfig:
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
        _global_db_config = DatabaseConfig.from_env()
    
    return _global_db_config


def set_database_config(config: DatabaseConfig) -> None:
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


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Main class
    'DatabaseConfig',
    
    # Global instance management
    'get_database_config',
    'set_database_config',
    'reset_database_config',
    'has_database_config',
    
    # Convenience functions
    'initialize_database',
    'shutdown_database',
    'get_database_status'
]