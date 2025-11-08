"""
Интеграция нового оптимизатора в существующую конфигурацию БД

Добавляет поддержку DatabaseManager и всех компонентов оптимизации
в основной конфигурации базы данных.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .database.base import DatabaseConfigBase
from .database.enums import DatabaseEngine, PoolStrategy, SSLMode
from .database import DatabaseManager, get_db_manager
from .database.optimizer import DatabaseOptimizer


@dataclass
class DatabaseConfig(DatabaseConfigBase):
    """
    Расширенная конфигурация базы данных с оптимизацией
    
    Включает все настройки из базового класса плюс:
    - Менеджер оптимизации
    - Мониторинг
    - Статистику
    - Автоматическое обслуживание
    """
    
    # Оптимизация
    enable_optimization: bool = True
    optimization_interval_hours: int = 1
    
    # Мониторинг
    enable_monitoring: bool = True
    monitoring_interval_seconds: int = 60
    
    # Статистика
    enable_statistics: bool = True
    statistics_retention_days: int = 30
    
    # Автообслуживание
    enable_auto_vacuum: bool = True
    enable_auto_analyze: bool = True
    enable_auto_backup: bool = True
    
    # Менеджер (создается при первом обращении)
    _manager: Optional[DatabaseManager] = field(default=None, init=False, repr=False)
    _optimizer: Optional[DatabaseOptimizer] = field(default=None, init=False, repr=False)
    
    @property
    def manager(self) -> DatabaseManager:
        """
        Получение менеджера БД
        
        Returns:
            DatabaseManager инстанс
        """
        if self._manager is None:
            self._manager = DatabaseManager(
                config=self,
                enable_optimization=self.enable_optimization,
                enable_monitoring=self.enable_monitoring,
                enable_statistics=self.enable_statistics
            )
        
        return self._manager
    
    @property
    def optimizer(self) -> DatabaseOptimizer:
        """
        Получение оптимизатора
        
        Returns:
            DatabaseOptimizer инстанс
        """
        if self._optimizer is None:
            self._optimizer = self.manager.optimizer
        
        return self._optimizer
    
    async def initialize_optimization(self) -> Dict[str, Any]:
        """
        Инициализация системы оптимизации
        
        Returns:
            Результаты инициализации
        """
        return await self.manager.initialize()
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """
        Запуск цикла оптимизации
        
        Returns:
            Результаты оптимизации
        """
        return await self.manager.run_optimization()
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Получение статуса оптимизации
        
        Returns:
            Полный статус системы оптимизации
        """
        return self.manager.get_status()
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик оптимизации
        
        Returns:
            Метрики всех компонентов
        """
        return self.manager.get_metrics()
    
    def get_recommendations(self) -> Dict[str, Any]:
        """
        Получение рекомендаций по оптимизации
        
        Returns:
            Рекомендации от всех компонентов
        """
        return self.manager.get_recommendations()
    
    def get_alerts(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Получение алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Список алертов
        """
        return self.manager.get_alerts(active_only)
    
    async def shutdown_optimization(self) -> Dict[str, Any]:
        """
        Graceful shutdown оптимизации
        
        Returns:
            Результаты завершения
        """
        if self._manager is not None:
            return await self._manager.shutdown()
        
        return {'status': 'not_initialized'}
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_") -> "DatabaseConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс для переменных окружения
            
        Returns:
            Инстанс DatabaseConfig
        """
        # Базовые параметры
        config_dict = {
            'engine': DatabaseEngine(os.getenv(f'{prefix}ENGINE', 'postgresql')),
            'host': os.getenv(f'{prefix}HOST', 'localhost'),
            'port': int(os.getenv(f'{prefix}PORT', '5432')),
            'database': os.getenv(f'{prefix}NAME', 'mydb'),
            'user': os.getenv(f'{prefix}USER', 'postgres'),
            'password': os.getenv(f'{prefix}PASSWORD', ''),
            
            # Оптимизация
            'enable_optimization': os.getenv(f'{prefix}ENABLE_OPTIMIZATION', 'true').lower() == 'true',
            'optimization_interval_hours': int(os.getenv(f'{prefix}OPTIMIZATION_INTERVAL_HOURS', '1')),
            
            # Мониторинг
            'enable_monitoring': os.getenv(f'{prefix}ENABLE_MONITORING', 'true').lower() == 'true',
            'monitoring_interval_seconds': int(os.getenv(f'{prefix}MONITORING_INTERVAL_SECONDS', '60')),
            
            # Статистика
            'enable_statistics': os.getenv(f'{prefix}ENABLE_STATISTICS', 'true').lower() == 'true',
            'statistics_retention_days': int(os.getenv(f'{prefix}STATISTICS_RETENTION_DAYS', '30')),
            
            # Автообслуживание
            'enable_auto_vacuum': os.getenv(f'{prefix}ENABLE_AUTO_VACUUM', 'true').lower() == 'true',
            'enable_auto_analyze': os.getenv(f'{prefix}ENABLE_AUTO_ANALYZE', 'true').lower() == 'true',
            'enable_auto_backup': os.getenv(f'{prefix}ENABLE_AUTO_BACKUP', 'true').lower() == 'true'
        }
        
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Словарь с конфигурацией
        """
        base_dict = super().to_dict() if hasattr(super(), 'to_dict') else {}
        
        base_dict.update({
            'enable_optimization': self.enable_optimization,
            'optimization_interval_hours': self.optimization_interval_hours,
            'enable_monitoring': self.enable_monitoring,
            'monitoring_interval_seconds': self.monitoring_interval_seconds,
            'enable_statistics': self.enable_statistics,
            'statistics_retention_days': self.statistics_retention_days,
            'enable_auto_vacuum': self.enable_auto_vacuum,
            'enable_auto_analyze': self.enable_auto_analyze,
            'enable_auto_backup': self.enable_auto_backup
        })
        
        return base_dict


# Создание глобального инстанса конфигурации
_global_db_config: Optional[DatabaseConfig] = None


def get_database_config() -> DatabaseConfig:
    """
    Получение глобальной конфигурации БД
    
    Returns:
        DatabaseConfig инстанс
    """
    global _global_db_config
    
    if _global_db_config is None:
        _global_db_config = DatabaseConfig.from_env()
    
    return _global_db_config


def set_database_config(config: DatabaseConfig) -> None:
    """
    Установка глобальной конфигурации БД
    
    Args:
        config: DatabaseConfig для установки
    """
    global _global_db_config
    _global_db_config = config


__all__ = [
    'DatabaseConfig',
    'get_database_config',
    'set_database_config'
]