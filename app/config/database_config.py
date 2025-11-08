# app/config/database_config.py
"""
Database Configuration Module
Модульная конфигурация базы данных с разделением ответственности
"""

import os
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConnectionPoolConfig:
    """Конфигурация пула соединений"""
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600
    pool_timeout: int = 30
    pool_pre_ping: bool = True
    echo: bool = False
    echo_pool: bool = False
    
    def __post_init__(self):
        """Валидация параметров пула"""
        if self.pool_size < 1:
            raise ValueError(f"pool_size должен быть >= 1, получено: {self.pool_size}")
        if self.max_overflow < 0:
            raise ValueError(f"max_overflow должен быть >= 0, получено: {self.max_overflow}")
        if self.pool_recycle < 0:
            raise ValueError(f"pool_recycle должен быть >= 0, получено: {self.pool_recycle}")
        if self.pool_timeout < 1:
            raise ValueError(f"pool_timeout должен быть >= 1, получено: {self.pool_timeout}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_recycle': self.pool_recycle,
            'pool_timeout': self.pool_timeout,
            'pool_pre_ping': self.pool_pre_ping,
            'echo': self.echo,
            'echo_pool': self.echo_pool
        }


@dataclass
class DatabasePragmaConfig:
    """Конфигурация PRAGMA настроек SQLite"""
    journal_mode: str = 'WAL'
    synchronous: str = 'NORMAL'
    cache_size: int = -64000
    foreign_keys: str = 'ON'
    temp_store: str = 'MEMORY'
    mmap_size: int = 30000000000
    page_size: int = 4096
    locking_mode: str = 'NORMAL'
    auto_vacuum: str = 'INCREMENTAL'
    
    def __post_init__(self):
        """Валидация PRAGMA параметров"""
        valid_journal_modes = ['DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'WAL', 'OFF']
        if self.journal_mode.upper() not in valid_journal_modes:
            raise ValueError(f"Недопустимый journal_mode: {self.journal_mode}")
        
        valid_synchronous = ['OFF', 'NORMAL', 'FULL', 'EXTRA']
        if self.synchronous.upper() not in valid_synchronous:
            raise ValueError(f"Недопустимый synchronous: {self.synchronous}")
        
        if self.cache_size > 0 or self.cache_size < -2000000:
            raise ValueError(f"cache_size должен быть в диапазоне [-2000000, 0], получено: {self.cache_size}")
        
        valid_temp_store = ['DEFAULT', 'FILE', 'MEMORY']
        if self.temp_store.upper() not in valid_temp_store:
            raise ValueError(f"Недопустимый temp_store: {self.temp_store}")
        
        valid_page_sizes = [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
        if self.page_size not in valid_page_sizes:
            raise ValueError(f"page_size должен быть одним из {valid_page_sizes}, получено: {self.page_size}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'journal_mode': self.journal_mode,
            'synchronous': self.synchronous,
            'cache_size': self.cache_size,
            'foreign_keys': self.foreign_keys,
            'temp_store': self.temp_store,
            'mmap_size': self.mmap_size,
            'page_size': self.page_size,
            'locking_mode': self.locking_mode,
            'auto_vacuum': self.auto_vacuum
        }
    
    def get_pragma_string(self) -> str:
        """
        Генерация строки PRAGMA команд
        
        Returns:
            Многострочная строка с PRAGMA командами
        """
        pragmas = []
        for key, value in self.to_dict().items():
            pragmas.append(f"PRAGMA {key}={value};")
        return "\n".join(pragmas)


@dataclass
class DatabaseBackupConfig:
    """Конфигурация резервного копирования"""
    enabled: bool = True
    interval_hours: int = 24
    max_age_days: int = 90
    max_backups: int = 30
    compression_enabled: bool = True
    
    def __post_init__(self):
        """Валидация параметров бэкапа"""
        if self.interval_hours < 1:
            raise ValueError(f"interval_hours должен быть >= 1, получено: {self.interval_hours}")
        if self.max_age_days < 1:
            raise ValueError(f"max_age_days должен быть >= 1, получено: {self.max_age_days}")
        if self.max_backups < 1:
            raise ValueError(f"max_backups должен быть >= 1, получено: {self.max_backups}")
    
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
        return (current_time - last_backup_time) >= interval_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'enabled': self.enabled,
            'interval_hours': self.interval_hours,
            'max_age_days': self.max_age_days,
            'max_backups': self.max_backups,
            'compression_enabled': self.compression_enabled
        }


@dataclass
class DatabaseVacuumConfig:
    """Конфигурация VACUUM операций"""
    enabled: bool = True
    interval_days: int = 7
    auto_vacuum: bool = True
    incremental_vacuum_pages: int = 100
    
    def __post_init__(self):
        """Валидация параметров VACUUM"""
        if self.interval_days < 1:
            raise ValueError(f"interval_days должен быть >= 1, получено: {self.interval_days}")
        if self.incremental_vacuum_pages < 1:
            raise ValueError(f"incremental_vacuum_pages должен быть >= 1, получено: {self.incremental_vacuum_pages}")
    
    def should_vacuum(self, last_vacuum_time: float, current_time: float) -> bool:
        """
        Проверка необходимости VACUUM операции
        
        Args:
            last_vacuum_time: Время последнего VACUUM (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если необходим VACUUM
        """
        if not self.enabled:
            return False
        
        interval_seconds = self.interval_days * 86400
        return (current_time - last_vacuum_time) >= interval_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'enabled': self.enabled,
            'interval_days': self.interval_days,
            'auto_vacuum': self.auto_vacuum,
            'incremental_vacuum_pages': self.incremental_vacuum_pages
        }


@dataclass
class DatabaseCacheConfig:
    """Конфигурация кэширования"""
    enabled: bool = True
    ttl_seconds: int = 3600
    max_size_mb: int = 100
    cleanup_interval_seconds: int = 300
    max_items: int = 10000
    eviction_policy: str = 'LRU'
    
    def __post_init__(self):
        """Валидация параметров кэша"""
        if self.ttl_seconds < 1:
            raise ValueError(f"ttl_seconds должен быть >= 1, получено: {self.ttl_seconds}")
        if self.max_size_mb < 1:
            raise ValueError(f"max_size_mb должен быть >= 1, получено: {self.max_size_mb}")
        if self.cleanup_interval_seconds < 1:
            raise ValueError(f"cleanup_interval_seconds должен быть >= 1, получено: {self.cleanup_interval_seconds}")
        if self.max_items < 1:
            raise ValueError(f"max_items должен быть >= 1, получено: {self.max_items}")
        
        valid_policies = ['LRU', 'LFU', 'FIFO', 'LIFO']
        if self.eviction_policy.upper() not in valid_policies:
            raise ValueError(f"eviction_policy должен быть одним из {valid_policies}, получено: {self.eviction_policy}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'enabled': self.enabled,
            'ttl_seconds': self.ttl_seconds,
            'max_size_mb': self.max_size_mb,
            'cleanup_interval_seconds': self.cleanup_interval_seconds,
            'max_items': self.max_items,
            'eviction_policy': self.eviction_policy
        }


@dataclass
class DatabaseConnectionConfig:
    """Конфигурация соединения с БД"""
    connection_timeout: int = 30
    busy_timeout: int = 5000
    max_retries: int = 3
    retry_delay: float = 1.0
    check_same_thread: bool = False
    isolation_level: Optional[str] = None
    
    def __post_init__(self):
        """Валидация параметров соединения"""
        if self.connection_timeout < 1:
            raise ValueError(f"connection_timeout должен быть >= 1, получено: {self.connection_timeout}")
        if self.busy_timeout < 1:
            raise ValueError(f"busy_timeout должен быть >= 1, получено: {self.busy_timeout}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries должен быть >= 0, получено: {self.max_retries}")
        if self.retry_delay < 0:
            raise ValueError(f"retry_delay должен быть >= 0, получено: {self.retry_delay}")
        
        valid_isolation_levels = [None, 'DEFERRED', 'IMMEDIATE', 'EXCLUSIVE']
        if self.isolation_level not in valid_isolation_levels:
            raise ValueError(f"isolation_level должен быть одним из {valid_isolation_levels}, получено: {self.isolation_level}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'connection_timeout': self.connection_timeout,
            'busy_timeout': self.busy_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'check_same_thread': self.check_same_thread,
            'isolation_level': self.isolation_level
        }


class DatabaseConfig:
    """
    Главный класс конфигурации базы данных
    Объединяет все компоненты конфигурации
    """
    
    def __init__(self, db_path: Path):
        """
        Инициализация конфигурации базы данных
        
        Args:
            db_path: Путь к файлу базы данных
        """
        if not isinstance(db_path, Path):
            db_path = Path(db_path)
        
        self.db_path = db_path
        self.news_db_path = db_path
        
        # Инициализация всех компонентов конфигурации
        self._init_pool_config()
        self._init_pragma_config()
        self._init_backup_config()
        self._init_vacuum_config()
        self._init_cache_config()
        self._init_connection_config()
        
        # Логирование инициализации
        logger.info(f"✅ [DATABASE] Path: {self.db_path}")
        logger.info(f"✅ [DATABASE] Backup: {'Enabled' if self.backup.enabled else 'Disabled'}")
        logger.info(f"✅ [DATABASE] Pool size: {self.pool.pool_size}, Max overflow: {self.pool.max_overflow}")
    
    def _init_pool_config(self) -> None:
        """Инициализация конфигурации пула соединений"""
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        
        self.pool = DatabaseConnectionPoolConfig(
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_timeout=self.pool_timeout,
            pool_pre_ping=self._get_bool_env('DB_POOL_PRE_PING', True),
            echo=self._get_bool_env('DB_ECHO', False),
            echo_pool=self._get_bool_env('DB_ECHO_POOL', False)
        )
    
    def _init_pragma_config(self) -> None:
        """Инициализация PRAGMA конфигурации"""
        self.pragma = DatabasePragmaConfig(
            journal_mode=os.getenv('DB_JOURNAL_MODE', 'WAL'),
            synchronous=os.getenv('DB_SYNCHRONOUS', 'NORMAL'),
            cache_size=int(os.getenv('DB_CACHE_SIZE', '-64000')),
            foreign_keys=os.getenv('DB_FOREIGN_KEYS', 'ON'),
            temp_store=os.getenv('DB_TEMP_STORE', 'MEMORY'),
            mmap_size=int(os.getenv('DB_MMAP_SIZE', '30000000000')),
            page_size=int(os.getenv('DB_PAGE_SIZE', '4096')),
            locking_mode=os.getenv('DB_LOCKING_MODE', 'NORMAL'),
            auto_vacuum=os.getenv('DB_AUTO_VACUUM', 'INCREMENTAL')
        )
        
        # Обратная совместимость
        self.pragma_settings = self.pragma.to_dict()
    
    def _init_backup_config(self) -> None:
        """Инициализация конфигурации бэкапа"""
        self.backup = DatabaseBackupConfig(
            enabled=self._get_bool_env('DB_BACKUP_ENABLED', True),
            interval_hours=int(os.getenv('DB_BACKUP_INTERVAL_HOURS', '24')),
            max_age_days=int(os.getenv('DB_MAX_AGE_DAYS', '90')),
            max_backups=int(os.getenv('DB_MAX_BACKUPS', '30')),
            compression_enabled=self._get_bool_env('DB_BACKUP_COMPRESSION', True)
        )
        
        # Обратная совместимость
        self.db_backup_enabled = self.backup.enabled
        self.db_backup_interval_hours = self.backup.interval_hours
        self.db_max_age_days = self.backup.max_age_days
    
    def _init_vacuum_config(self) -> None:
        """Инициализация конфигурации VACUUM"""
        self.vacuum = DatabaseVacuumConfig(
            enabled=self._get_bool_env('DB_VACUUM_ENABLED', True),
            interval_days=int(os.getenv('DB_VACUUM_INTERVAL_DAYS', '7')),
            auto_vacuum=self._get_bool_env('DB_AUTO_VACUUM', True),
            incremental_vacuum_pages=int(os.getenv('DB_INCREMENTAL_VACUUM_PAGES', '100'))
        )
        
        # Обратная совместимость
        self.db_vacuum_enabled = self.vacuum.enabled
        self.db_vacuum_interval_days = self.vacuum.interval_days
    
    def _init_cache_config(self) -> None:
        """Инициализация конфигурации кэша"""
        self.cache = DatabaseCacheConfig(
            enabled=self._get_bool_env('CACHE_ENABLED', True),
            ttl_seconds=int(os.getenv('CACHE_TTL_SECONDS', '3600')),
            max_size_mb=int(os.getenv('CACHE_MAX_SIZE_MB', '100')),
            cleanup_interval_seconds=int(os.getenv('CACHE_CLEANUP_INTERVAL', '300')),
            max_items=int(os.getenv('CACHE_MAX_ITEMS', '10000')),
            eviction_policy=os.getenv('CACHE_EVICTION_POLICY', 'LRU')
        )
        
        # Обратная совместимость
        self.cache_enabled = self.cache.enabled
        self.cache_ttl_seconds = self.cache.ttl_seconds
        self.cache_max_size_mb = self.cache.max_size_mb
        self.cache_cleanup_interval = self.cache.cleanup_interval_seconds
    
    def _init_connection_config(self) -> None:
        """Инициализация конфигурации соединения"""
        self.connection = DatabaseConnectionConfig(
            connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', '30')),
            busy_timeout=int(os.getenv('DB_BUSY_TIMEOUT', '5000')),
            max_retries=int(os.getenv('DB_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('DB_RETRY_DELAY', '1.0')),
            check_same_thread=self._get_bool_env('DB_CHECK_SAME_THREAD', False),
            isolation_level=os.getenv('DB_ISOLATION_LEVEL', None)
        )
        
        # Обратная совместимость
        self.connection_timeout = self.connection.connection_timeout
        self.busy_timeout = self.connection.busy_timeout
        self.max_connections = self.pool.pool_size + self.pool.max_overflow
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """
        Получение boolean переменной окружения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            
        Returns:
            Boolean значение
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def get_connection_string(self) -> str:
        """
        Получение строки подключения SQLite
        
        Returns:
            SQLite connection string
        """
        return f"sqlite:///{self.db_path}"
    
    def get_pragma_string(self) -> str:
        """
        Получение PRAGMA команд для SQLite
        
        Returns:
            Строка с PRAGMA командами
        """
        return self.pragma.get_pragma_string()
    
    def should_backup(self, last_backup_time: float, current_time: float) -> bool:
        """
        Проверка необходимости backup
        
        Args:
            last_backup_time: Время последнего backup (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если нужен backup
        """
        return self.backup.should_backup(last_backup_time, current_time)
    
    def should_vacuum(self, last_vacuum_time: float, current_time: float) -> bool:
        """
        Проверка необходимости VACUUM
        
        Args:
            last_vacuum_time: Время последнего VACUUM (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если нужен VACUUM
        """
        return self.vacuum.should_vacuum(last_vacuum_time, current_time)
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации кэша
        
        Returns:
            Словарь с параметрами кэша
        """
        return self.cache.to_dict()
    
    def get_pool_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации пула соединений
        
        Returns:
            Словарь с параметрами пула
        """
        return self.pool.to_dict()
    
    def get_connection_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации соединения
        
        Returns:
            Словарь с параметрами соединения
        """
        return self.connection.to_dict()
    
    def get_sqlalchemy_kwargs(self) -> Dict[str, Any]:
        """
        Получение параметров для SQLAlchemy engine
        
        Returns:
            Словарь параметров для create_engine
        """
        return {
            'pool_size': self.pool.pool_size,
            'max_overflow': self.pool.max_overflow,
            'pool_recycle': self.pool.pool_recycle,
            'pool_timeout': self.pool.pool_timeout,
            'pool_pre_ping': self.pool.pool_pre_ping,
            'echo': self.pool.echo,
            'echo_pool': self.pool.echo_pool,
            'connect_args': {
                'timeout': self.connection.connection_timeout,
                'check_same_thread': self.connection.check_same_thread
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация всей конфигурации в словарь
        
        Returns:
            Полный словарь конфигурации
        """
        return {
            'path': str(self.db_path),
            'pool': self.pool.to_dict(),
            'pragma': self.pragma.to_dict(),
            'backup': self.backup.to_dict(),
            'vacuum': self.vacuum.to_dict(),
            'cache': self.cache.to_dict(),
            'connection': self.connection.to_dict()
        }
    
    def validate(self) -> bool:
        """
        Валидация всей конфигурации
        
        Returns:
            True если конфигурация валидна
            
        Raises:
            ValueError: Если конфигурация невалидна
        """
        # Проверка пути к БД
        if not self.db_path:
            raise ValueError("Путь к базе данных не может быть пустым")
        
        # Проверка родительской директории
        parent_dir = self.db_path.parent
        if not parent_dir.exists():
            logger.warning(f"Родительская директория не существует: {parent_dir}")
        
        # Все компоненты валидируются в __post_init__
        logger.info("✅ [DATABASE] Конфигурация валидна")
        return True


def create_database_config(db_path: Path) -> DatabaseConfig:
    """
    Фабричная функция для создания DatabaseConfig
    
    Args:
        db_path: Путь к файлу базы данных
        
    Returns:
        Настроенный экземпляр DatabaseConfig
    """
    config = DatabaseConfig(db_path)
    config.validate()
    return config