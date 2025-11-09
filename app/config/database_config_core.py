"""
Database Configuration Core
Основной класс расширенной конфигурации БД
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from .database.base import DatabaseConfigBase
from .database.enums import DatabaseEngine
from .database.manager import DatabaseManager
from .database.exceptions import ValidationError

logger = logging.getLogger(__name__)


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
                message="health_check_interval_seconds must be >= 30",
                field="health_check_interval_seconds",
                value=self.health_check_interval_seconds,
                reason="Minimum interval is 30 seconds"
            )
        
        if self.backup_retention_days < 1:
            raise ValidationError(
                message="backup_retention_days must be >= 1",
                field="backup_retention_days",
                value=self.backup_retention_days,
                reason="Minimum retention is 1 day"
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


__all__ = ['DatabaseConfig']