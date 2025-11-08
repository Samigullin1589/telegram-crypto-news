"""
Database Backup Configuration
Конфигурация резервного копирования с продвинутыми стратегиями
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from enum import Enum
from datetime import datetime, timedelta

from ..base import BaseConfig, TimedConfig
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class BackupStrategy(str, Enum):
    """
    Стратегии резервного копирования
    
    NONE - Без бэкапов
    MINIMAL - Минимальные бэкапы (раз в неделю, 4 копии)
    STANDARD - Стандартные бэкапы (раз в день, 30 копий)
    AGGRESSIVE - Агрессивные бэкапы (каждые 6 часов, 60 копий)
    CONTINUOUS - Непрерывные бэкапы (каждый час, 168 копий)
    CUSTOM - Кастомная конфигурация
    """
    NONE = 'NONE'
    MINIMAL = 'MINIMAL'
    STANDARD = 'STANDARD'
    AGGRESSIVE = 'AGGRESSIVE'
    CONTINUOUS = 'CONTINUOUS'
    CUSTOM = 'CUSTOM'


class BackupType(str, Enum):
    """Типы бэкапов"""
    FULL = 'FULL'
    INCREMENTAL = 'INCREMENTAL'
    DIFFERENTIAL = 'DIFFERENTIAL'


class CompressionLevel(int, Enum):
    """Уровни сжатия"""
    NONE = 0
    FASTEST = 1
    FAST = 3
    BALANCED = 6
    HIGH = 9


@dataclass
class DatabaseBackupConfig(TimedConfig):
    """
    Конфигурация резервного копирования
    
    Attributes:
        enabled: Включение бэкапов
        interval_hours: Интервал между бэкапами (часы)
        max_age_days: Максимальный возраст бэкапов (дни)
        max_backups: Максимальное количество бэкапов
        compression_enabled: Включение сжатия
        compression_level: Уровень сжатия (0-9)
        incremental_enabled: Включение инкрементальных бэкапов
        strategy: Стратегия бэкапов
        backup_type: Тип бэкапов
    """
    
    enabled: bool = True
    interval_hours: int = 24
    max_age_days: int = 90
    max_backups: int = 30
    compression_enabled: bool = True
    compression_level: CompressionLevel = CompressionLevel.BALANCED
    incremental_enabled: bool = False
    strategy: BackupStrategy = BackupStrategy.STANDARD
    backup_type: BackupType = BackupType.FULL
    
    # Расширенные параметры
    verify_after_backup: bool = True
    parallel_compression: bool = True
    backup_wal: bool = True  # Бэкап WAL файлов
    backup_shm: bool = False  # Бэкап shared memory файлов
    exclude_temp_tables: bool = True
    
    # Callbacks (можно установить извне)
    on_backup_start: Optional[Callable] = field(default=None, repr=False)
    on_backup_complete: Optional[Callable] = field(default=None, repr=False)
    on_backup_error: Optional[Callable] = field(default=None, repr=False)
    
    # Метрики
    _total_backups_created: int = field(default=0, init=False, repr=False)
    _total_backups_failed: int = field(default=0, init=False, repr=False)
    _last_backup_size_bytes: int = field(default=0, init=False, repr=False)
    _last_backup_duration_seconds: float = field(default=0.0, init=False, repr=False)
    
    def __post_init__(self):
        """Применение стратегии и валидация"""
        self._apply_strategy()
        super().__post_init__()
    
    def _apply_strategy(self) -> None:
        """Применение выбранной стратегии"""
        if self.strategy == BackupStrategy.NONE:
            self.enabled = False
            logger.info("Applied NONE backup strategy - backups disabled")
        
        elif self.strategy == BackupStrategy.MINIMAL:
            self.interval_hours = 168  # 1 week
            self.max_backups = 4
            self.compression_enabled = True
            self.compression_level = CompressionLevel.HIGH
            logger.info("Applied MINIMAL backup strategy")
        
        elif self.strategy == BackupStrategy.STANDARD:
            self.interval_hours = 24  # 1 day
            self.max_backups = 30
            self.compression_enabled = True
            self.compression_level = CompressionLevel.BALANCED
            logger.info("Applied STANDARD backup strategy")
        
        elif self.strategy == BackupStrategy.AGGRESSIVE:
            self.interval_hours = 6
            self.max_backups = 60
            self.compression_enabled = True
            self.compression_level = CompressionLevel.FAST
            self.incremental_enabled = True
            logger.info("Applied AGGRESSIVE backup strategy")
        
        elif self.strategy == BackupStrategy.CONTINUOUS:
            self.interval_hours = 1
            self.max_backups = 168  # 1 week of hourly backups
            self.compression_enabled = True
            self.compression_level = CompressionLevel.FASTEST
            self.incremental_enabled = True
            logger.warning(
                "Applied CONTINUOUS backup strategy. "
                "This will consume significant storage!"
            )
    
    def validate(self) -> bool:
        """Валидация параметров бэкапа"""
        if not self.enabled:
            logger.info("Backups are disabled, skipping validation")
            return True
        
        # Валидация интервала
        if self.interval_hours < 1:
            raise ValidationError(
                field='interval_hours',
                value=self.interval_hours,
                reason='must be >= 1'
            )
        
        # Валидация возраста
        if self.max_age_days < 1:
            raise ValidationError(
                field='max_age_days',
                value=self.max_age_days,
                reason='must be >= 1'
            )
        
        # Валидация количества
        if self.max_backups < 1:
            raise ValidationError(
                field='max_backups',
                value=self.max_backups,
                reason='must be >= 1'
            )
        
        # Проверка логичности настроек
        backups_per_retention = (self.max_age_days * 24) // self.interval_hours
        if self.max_backups < backups_per_retention:
            logger.warning(
                f"max_backups ({self.max_backups}) is less than expected "
                f"backups during retention period ({backups_per_retention}). "
                f"Some backups may be deleted before max_age_days."
            )
        
        # Предупреждения
        if self.max_backups > 100:
            logger.warning(
                f"max_backups={self.max_backups} is very high. "
                f"This will consume significant storage."
            )
        
        if self.interval_hours < 6 and not self.incremental_enabled:
            logger.warning(
                f"Frequent full backups (every {self.interval_hours}h) without "
                f"incremental mode. Consider enabling incremental_enabled."
            )
        
        if self.compression_enabled and self.compression_level == CompressionLevel.NONE:
            logger.warning(
                "compression_enabled=True but compression_level=NONE. "
                "Backups will not be compressed!"
            )
        
        return True
    
    def should_execute(self, last_time: float, current_time: float) -> bool:
        """Проверка необходимости создания бэкапа (наследуется от TimedConfig)"""
        if not self.enabled:
            return False
        
        return self.should_backup(last_time, current_time)
    
    def should_backup(self, last_backup_time: float, current_time: float) -> bool:
        """
        Проверка необходимости создания бэкапа
        
        Args:
            last_backup_time: Время последнего бэкапа (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если необходим бэкап
        """
        if not self.enabled:
            return False
        
        interval_seconds = self.interval_hours * 3600
        elapsed = current_time - last_backup_time
        
        return elapsed >= interval_seconds
    
    def calculate_retention_timestamp(self, current_time: float) -> float:
        """
        Вычисление timestamp для удаления старых бэкапов
        
        Args:
            current_time: Текущее время (timestamp)
            
        Returns:
            Timestamp границы удаления
        """
        return current_time - (self.max_age_days * 86400)
    
    def estimate_storage_requirements(self, database_size_bytes: int) -> Dict[str, Any]:
        """
        Оценка требований к хранилищу
        
        Args:
            database_size_bytes: Размер БД в байтах
            
        Returns:
            Словарь с оценками
        """
        # Оценка сжатия
        compression_ratio = 1.0
        if self.compression_enabled:
            if self.compression_level == CompressionLevel.NONE:
                compression_ratio = 1.0
            elif self.compression_level <= CompressionLevel.FAST:
                compression_ratio = 0.7
            elif self.compression_level == CompressionLevel.BALANCED:
                compression_ratio = 0.5
            else:
                compression_ratio = 0.3
        
        # Размер одного бэкапа
        if self.incremental_enabled:
            full_backup_size = database_size_bytes * compression_ratio
            incremental_size = database_size_bytes * 0.1 * compression_ratio  # 10% от БД
            # Предположим 1 полный + остальные инкрементальные
            avg_backup_size = (full_backup_size + (self.max_backups - 1) * incremental_size) / self.max_backups
        else:
            avg_backup_size = database_size_bytes * compression_ratio
        
        total_size = avg_backup_size * self.max_backups
        
        return {
            'database_size_bytes': database_size_bytes,
            'database_size_mb': database_size_bytes / (1024 * 1024),
            'compression_ratio': compression_ratio,
            'avg_backup_size_bytes': avg_backup_size,
            'avg_backup_size_mb': avg_backup_size / (1024 * 1024),
            'total_storage_bytes': total_size,
            'total_storage_mb': total_size / (1024 * 1024),
            'total_storage_gb': total_size / (1024 * 1024 * 1024),
            'max_backups': self.max_backups,
            'incremental_enabled': self.incremental_enabled
        }
    
    def update_metrics(
        self,
        success: bool,
        size_bytes: int = 0,
        duration_seconds: float = 0.0
    ) -> None:
        """
        Обновление метрик бэкапов
        
        Args:
            success: Успешность бэкапа
            size_bytes: Размер бэкапа в байтах
            duration_seconds: Длительность создания бэкапа
        """
        if success:
            self._total_backups_created += 1
            self._last_backup_size_bytes = size_bytes
            self._last_backup_duration_seconds = duration_seconds
        else:
            self._total_backups_failed += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик бэкапов"""
        total_attempts = self._total_backups_created + self._total_backups_failed
        success_rate = 0.0
        if total_attempts > 0:
            success_rate = self._total_backups_created / total_attempts
        
        return {
            'enabled': self.enabled,
            'total_backups_created': self._total_backups_created,
            'total_backups_failed': self._total_backups_failed,
            'success_rate': success_rate,
            'last_backup_size_bytes': self._last_backup_size_bytes,
            'last_backup_size_mb': self._last_backup_size_bytes / (1024 * 1024),
            'last_backup_duration_seconds': self._last_backup_duration_seconds,
            'strategy': self.strategy.value,
            'interval_hours': self.interval_hours,
            'max_backups': self.max_backups
        }