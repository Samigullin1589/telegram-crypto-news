# app/config/database_config.py
"""
Database Configuration Module
Конфигурация базы данных и кэширования
"""

import os
import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Конфигурация базы данных
    Настройки SQLite, backups и кэширования
    """
    
    def __init__(self, db_path: Path):
        """
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.news_db_path = db_path
        
        self.db_backup_enabled = self._get_bool_env('DB_BACKUP_ENABLED', True)
        self.db_backup_interval_hours = int(
            os.getenv('DB_BACKUP_INTERVAL_HOURS', '24')
        )
        self.db_max_age_days = int(os.getenv('DB_MAX_AGE_DAYS', '90'))
        self.db_vacuum_enabled = self._get_bool_env('DB_VACUUM_ENABLED', True)
        self.db_vacuum_interval_days = int(
            os.getenv('DB_VACUUM_INTERVAL_DAYS', '7')
        )
        
        self.connection_timeout = 30
        self.busy_timeout = 5000
        self.max_connections = 10
        self.pool_size = 5
        self.pool_recycle = 3600
        
        self.pragma_settings = {
            'journal_mode': 'WAL',
            'synchronous': 'NORMAL',
            'cache_size': -64000,
            'foreign_keys': 'ON',
            'temp_store': 'MEMORY',
            'mmap_size': 30000000000,
            'page_size': 4096
        }
        
        self.cache_enabled = self._get_bool_env('CACHE_ENABLED', True)
        self.cache_ttl_seconds = int(os.getenv('CACHE_TTL_SECONDS', '3600'))
        self.cache_max_size_mb = int(os.getenv('CACHE_MAX_SIZE_MB', '100'))
        self.cache_cleanup_interval = 300
        
        logger.info(f"✅ [DATABASE] Path: {self.db_path}")
        logger.info(f"✅ [DATABASE] Backup: {'Enabled' if self.db_backup_enabled else 'Disabled'}")
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Получение boolean переменной"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_connection_string(self) -> str:
        """
        Получение строки подключения SQLite
        
        Returns:
            Connection string
        """
        return f"sqlite:///{self.db_path}"
    
    def get_pragma_string(self) -> str:
        """
        Получение PRAGMA команд для SQLite
        
        Returns:
            Строка с PRAGMA командами
        """
        pragmas = []
        for key, value in self.pragma_settings.items():
            pragmas.append(f"PRAGMA {key}={value};")
        return "\n".join(pragmas)
    
    def should_backup(self, last_backup_time: float, current_time: float) -> bool:
        """
        Проверка необходимости backup
        
        Args:
            last_backup_time: Время последнего backup (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если нужен backup
        """
        if not self.db_backup_enabled:
            return False
        
        interval_seconds = self.db_backup_interval_hours * 3600
        return (current_time - last_backup_time) >= interval_seconds
    
    def should_vacuum(self, last_vacuum_time: float, current_time: float) -> bool:
        """Проверка необходимости VACUUM"""
        if not self.db_vacuum_enabled:
            return False
        
        interval_seconds = self.db_vacuum_interval_days * 86400
        return (current_time - last_vacuum_time) >= interval_seconds
    
    def get_cache_config(self) -> Dict:
        """Получение конфигурации кэша"""
        return {
            'enabled': self.cache_enabled,
            'ttl_seconds': self.cache_ttl_seconds,
            'max_size_mb': self.cache_max_size_mb,
            'cleanup_interval': self.cache_cleanup_interval
        }
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'path': str(self.db_path),
            'backup_enabled': self.db_backup_enabled,
            'backup_interval_hours': self.db_backup_interval_hours,
            'max_age_days': self.db_max_age_days,
            'vacuum_enabled': self.db_vacuum_enabled,
            'pragma_settings': self.pragma_settings,
            'cache': self.get_cache_config()
        }