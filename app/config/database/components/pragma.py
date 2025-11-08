"""
Database PRAGMA Configuration
Конфигурация SQLite PRAGMA с пресетами и оптимизацией
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

from ..base import BaseConfig
from ..enums import (
    JournalMode, SynchronousMode, TempStoreMode, 
    LockingMode, AutoVacuumMode
)
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class PragmaPreset(str, Enum):
    """
    Пресеты PRAGMA конфигураций для разных сценариев
    
    MAXIMUM_SAFETY - Максимальная безопасность данных
    BALANCED - Баланс производительности и безопасности
    MAXIMUM_PERFORMANCE - Максимальная производительность
    MEMORY_OPTIMIZED - Оптимизация для работы в памяти
    DISK_OPTIMIZED - Оптимизация для работы с диском
    READ_HEAVY - Оптимизация для чтения
    WRITE_HEAVY - Оптимизация для записи
    CUSTOM - Кастомная конфигурация
    """
    MAXIMUM_SAFETY = 'MAXIMUM_SAFETY'
    BALANCED = 'BALANCED'
    MAXIMUM_PERFORMANCE = 'MAXIMUM_PERFORMANCE'
    MEMORY_OPTIMIZED = 'MEMORY_OPTIMIZED'
    DISK_OPTIMIZED = 'DISK_OPTIMIZED'
    READ_HEAVY = 'READ_HEAVY'
    WRITE_HEAVY = 'WRITE_HEAVY'
    CUSTOM = 'CUSTOM'


@dataclass
class DatabasePragmaConfig(BaseConfig):
    """
    Конфигурация PRAGMA настроек SQLite
    
    Attributes:
        journal_mode: Режим журналирования
        synchronous: Режим синхронизации
        cache_size: Размер кэша страниц (отрицательное = КБ)
        foreign_keys: Включение проверки внешних ключей
        temp_store: Хранилище временных таблиц
        mmap_size: Размер memory-mapped I/O
        page_size: Размер страницы БД в байтах
        locking_mode: Режим блокировки
        auto_vacuum: Режим автоочистки
        preset: Пресет конфигурации
    """
    
    journal_mode: JournalMode = JournalMode.WAL
    synchronous: SynchronousMode = SynchronousMode.NORMAL
    cache_size: int = -64000  # 64MB в килобайтах
    foreign_keys: bool = True
    temp_store: TempStoreMode = TempStoreMode.MEMORY
    mmap_size: int = 30000000000  # 30GB
    page_size: int = 4096
    locking_mode: LockingMode = LockingMode.NORMAL
    auto_vacuum: AutoVacuumMode = AutoVacuumMode.INCREMENTAL
    preset: PragmaPreset = PragmaPreset.BALANCED
    
    # Дополнительные PRAGMA
    busy_timeout: int = 5000  # milliseconds
    checkpoint_fullfsync: bool = False
    fullfsync: bool = False
    ignore_check_constraints: bool = False
    query_only: bool = False
    read_uncommitted: bool = False
    recursive_triggers: bool = True
    secure_delete: bool = False
    wal_autocheckpoint: int = 1000  # pages
    
    # Метаданные
    _applied_preset: Optional[PragmaPreset] = field(
        default=None, 
        init=False, 
        repr=False
    )
    
    def __post_init__(self):
        """Применение пресета и валидация"""
        self._apply_preset()
        super().__post_init__()
    
    def _apply_preset(self) -> None:
        """Применение выбранного пресета"""
        if self.preset == PragmaPreset.MAXIMUM_SAFETY:
            self.journal_mode = JournalMode.WAL
            self.synchronous = SynchronousMode.FULL
            self.temp_store = TempStoreMode.FILE
            self.secure_delete = True
            self.fullfsync = True
            logger.info("Applied MAXIMUM_SAFETY pragma preset")
        
        elif self.preset == PragmaPreset.BALANCED:
            self.journal_mode = JournalMode.WAL
            self.synchronous = SynchronousMode.NORMAL
            self.temp_store = TempStoreMode.MEMORY
            logger.info("Applied BALANCED pragma preset")
        
        elif self.preset == PragmaPreset.MAXIMUM_PERFORMANCE:
            self.journal_mode = JournalMode.MEMORY
            self.synchronous = SynchronousMode.OFF
            self.temp_store = TempStoreMode.MEMORY
            self.locking_mode = LockingMode.EXCLUSIVE
            self.cache_size = -128000  # 128MB
            logger.warning(
                "Applied MAXIMUM_PERFORMANCE preset. "
                "Data safety is minimal - use only for non-critical data!"
            )
        
        elif self.preset == PragmaPreset.MEMORY_OPTIMIZED:
            self.temp_store = TempStoreMode.MEMORY
            self.cache_size = -256000  # 256MB
            self.mmap_size = 0  # Disable mmap
            logger.info("Applied MEMORY_OPTIMIZED pragma preset")
        
        elif self.preset == PragmaPreset.DISK_OPTIMIZED:
            self.mmap_size = 30000000000  # 30GB
            self.page_size = 8192  # Larger pages
            self.cache_size = -32000  # Smaller cache
            logger.info("Applied DISK_OPTIMIZED pragma preset")
        
        elif self.preset == PragmaPreset.READ_HEAVY:
            self.journal_mode = JournalMode.WAL
            self.cache_size = -128000  # 128MB
            self.query_only = True
            self.read_uncommitted = True
            logger.info("Applied READ_HEAVY pragma preset")
        
        elif self.preset == PragmaPreset.WRITE_HEAVY:
            self.journal_mode = JournalMode.WAL
            self.synchronous = SynchronousMode.NORMAL
            self.wal_autocheckpoint = 10000  # Less frequent checkpoints
            logger.info("Applied WRITE_HEAVY pragma preset")
        
        self._applied_preset = self.preset
    
    def validate(self) -> bool:
        """Валидация PRAGMA параметров"""
        # Валидация cache_size
        if self.cache_size > 0 or self.cache_size < -2000000:
            raise ValidationError(
                field='cache_size',
                value=self.cache_size,
                reason='must be in range [-2000000, 0] (KB)'
            )
        
        # Валидация page_size
        valid_page_sizes = [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
        if self.page_size not in valid_page_sizes:
            raise ValidationError(
                field='page_size',
                value=self.page_size,
                reason=f'must be one of {valid_page_sizes}'
            )
        
        # Валидация mmap_size
        if self.mmap_size < 0:
            raise ValidationError(
                field='mmap_size',
                value=self.mmap_size,
                reason='must be >= 0'
            )
        
        # Валидация busy_timeout
        if self.busy_timeout < 0:
            raise ValidationError(
                field='busy_timeout',
                value=self.busy_timeout,
                reason='must be >= 0'
            )
        
        # Валидация wal_autocheckpoint
        if self.wal_autocheckpoint < 0:
            raise ValidationError(
                field='wal_autocheckpoint',
                value=self.wal_autocheckpoint,
                reason='must be >= 0 (0 = disabled)'
            )
        
        # Предупреждения о безопасности
        if self.synchronous == SynchronousMode.OFF:
            logger.warning(
                "⚠️ synchronous=OFF is UNSAFE! "
                "Database may be corrupted if system crashes. "
                "Use only for disposable/test data."
            )
        
        if self.journal_mode == JournalMode.OFF:
            logger.warning(
                "⚠️ journal_mode=OFF disables rollback! "
                "Transactions cannot be rolled back. Very dangerous!"
            )
        
        if self.journal_mode == JournalMode.MEMORY:
            logger.warning(
                "⚠️ journal_mode=MEMORY: Rollback journal in RAM. "
                "System crash will corrupt database!"
            )
        
        # Предупреждения о производительности
        if self.synchronous == SynchronousMode.EXTRA:
            logger.info(
                "synchronous=EXTRA provides redundant safety at performance cost. "
                "FULL is usually sufficient."
            )
        
        if self.journal_mode == JournalMode.DELETE and self.synchronous == SynchronousMode.FULL:
            logger.warning(
                "DELETE journal mode + FULL sync is very slow. "
                "Consider WAL mode for better performance."
            )
        
        # Проверка комбинаций
        if self.query_only and not self.read_uncommitted:
            logger.info(
                "query_only mode detected. "
                "Consider enabling read_uncommitted for better read performance."
            )
        
        if self.locking_mode == LockingMode.EXCLUSIVE:
            logger.warning(
                "⚠️ EXCLUSIVE locking mode: Only one process can access database. "
                "Not suitable for multi-process applications!"
            )
        
        return True
    
    def get_pragma_commands(self) -> Dict[str, Any]:
        """
        Получение всех PRAGMA команд в виде словаря
        
        Returns:
            Словарь PRAGMA команд
        """
        commands = {
            'journal_mode': self.journal_mode.value,
            'synchronous': self.synchronous.value,
            'cache_size': self.cache_size,
            'foreign_keys': 'ON' if self.foreign_keys else 'OFF',
            'temp_store': self.temp_store.value,
            'mmap_size': self.mmap_size,
            'page_size': self.page_size,
            'locking_mode': self.locking_mode.value,
            'auto_vacuum': self.auto_vacuum.value,
            'busy_timeout': self.busy_timeout,
            'checkpoint_fullfsync': 'ON' if self.checkpoint_fullfsync else 'OFF',
            'fullfsync': 'ON' if self.fullfsync else 'OFF',
            'ignore_check_constraints': 'ON' if self.ignore_check_constraints else 'OFF',
            'query_only': 'ON' if self.query_only else 'OFF',
            'read_uncommitted': 'ON' if self.read_uncommitted else 'OFF',
            'recursive_triggers': 'ON' if self.recursive_triggers else 'OFF',
            'secure_delete': 'ON' if self.secure_delete else 'OFF',
            'wal_autocheckpoint': self.wal_autocheckpoint,
        }
        
        return commands
    
    def get_pragma_string(self) -> str:
        """
        Генерация строки PRAGMA команд для выполнения
        
        Returns:
            Многострочная строка с PRAGMA командами
        """
        commands = []
        for key, value in self.get_pragma_commands().items():
            commands.append(f"PRAGMA {key}={value};")
        
        return "\n".join(commands)
    
    def get_initialization_pragmas(self) -> List[str]:
        """
        Получение PRAGMA команд для инициализации соединения
        
        Returns:
            Список команд для выполнения при создании соединения
        """
        return [
            f"PRAGMA {key}={value};"
            for key, value in self.get_pragma_commands().items()
        ]
    
    def estimate_memory_usage(self) -> Dict[str, int]:
        """
        Оценка использования памяти на основе настроек
        
        Returns:
            Словарь с оценками памяти в байтах
        """
        # Cache size в байтах (отрицательное значение = KB)
        cache_bytes = abs(self.cache_size) * 1024 if self.cache_size < 0 else self.cache_size * self.page_size
        
        # Temp store
        temp_store_bytes = 0
        if self.temp_store == TempStoreMode.MEMORY:
            temp_store_bytes = 50 * 1024 * 1024  # Примерно 50MB
        
        # mmap не использует оперативную память напрямую
        
        total = cache_bytes + temp_store_bytes
        
        return {
            'cache_bytes': cache_bytes,
            'temp_store_bytes': temp_store_bytes,
            'total_estimated_bytes': total,
            'cache_mb': cache_bytes / (1024 * 1024),
            'total_mb': total / (1024 * 1024)
        }