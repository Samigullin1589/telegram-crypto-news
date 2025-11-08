"""
Database Configuration Enums
Все enum типы для конфигурации БД
"""

from enum import Enum


class JournalMode(str, Enum):
    """
    Режимы журналирования SQLite
    
    DELETE - Удаление журнала после каждой транзакции (по умолчанию)
    TRUNCATE - Обнуление журнала вместо удаления
    PERSIST - Журнал остаётся на диске
    MEMORY - Журнал в памяти (небезопасно при сбоях)
    WAL - Write-Ahead Logging (рекомендуется для современных приложений)
    OFF - Без журналирования (максимальная производительность, небезопасно)
    """
    DELETE = 'DELETE'
    TRUNCATE = 'TRUNCATE'
    PERSIST = 'PERSIST'
    MEMORY = 'MEMORY'
    WAL = 'WAL'
    OFF = 'OFF'


class SynchronousMode(str, Enum):
    """
    Режимы синхронизации SQLite с диском
    
    OFF - Без синхронизации (максимальная скорость, риск повреждения)
    NORMAL - Синхронизация в критических моментах (баланс)
    FULL - Полная синхронизация (максимальная безопасность)
    EXTRA - Дополнительная синхронизация (избыточная безопасность)
    """
    OFF = 'OFF'
    NORMAL = 'NORMAL'
    FULL = 'FULL'
    EXTRA = 'EXTRA'


class TempStoreMode(str, Enum):
    """
    Режимы хранения временных данных
    
    DEFAULT - По умолчанию (зависит от compile-time настроек)
    FILE - Временные таблицы на диске
    MEMORY - Временные таблицы в памяти (быстрее)
    """
    DEFAULT = 'DEFAULT'
    FILE = 'FILE'
    MEMORY = 'MEMORY'


class LockingMode(str, Enum):
    """
    Режимы блокировки базы данных
    
    NORMAL - Стандартная блокировка (рекомендуется)
    EXCLUSIVE - Эксклюзивная блокировка (один процесс)
    """
    NORMAL = 'NORMAL'
    EXCLUSIVE = 'EXCLUSIVE'


class AutoVacuumMode(str, Enum):
    """
    Режимы автоматической очистки БД
    
    NONE - Без автоочистки (требуется ручной VACUUM)
    FULL - Полная автоочистка при каждом COMMIT
    INCREMENTAL - Инкрементальная очистка (рекомендуется)
    """
    NONE = 'NONE'
    FULL = 'FULL'
    INCREMENTAL = 'INCREMENTAL'


class IsolationLevel(str, Enum):
    """
    Уровни изоляции транзакций SQLite
    
    DEFERRED - Транзакция начинается при первом чтении (по умолчанию)
    IMMEDIATE - Резервирование записи сразу
    EXCLUSIVE - Эксклюзивная блокировка сразу
    """
    DEFERRED = 'DEFERRED'
    IMMEDIATE = 'IMMEDIATE'
    EXCLUSIVE = 'EXCLUSIVE'


class CacheEvictionPolicy(str, Enum):
    """
    Политики вытеснения элементов из кэша
    
    LRU - Least Recently Used (самый давно используемый)
    LFU - Least Frequently Used (самый редко используемый)
    FIFO - First In First Out (первым пришёл - первым ушёл)
    LIFO - Last In First Out (последним пришёл - первым ушёл)
    """
    LRU = 'LRU'
    LFU = 'LFU'
    FIFO = 'FIFO'
    LIFO = 'LIFO'