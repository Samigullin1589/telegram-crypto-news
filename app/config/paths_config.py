# app/config/paths_config.py
"""
Paths Configuration Module
Конфигурация путей к файлам и директориям
"""

import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class PathsConfig:
    """
    Конфигурация путей к данным и файлам
    Автоматическое создание необходимых директорий
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Args:
            base_dir: Базовая директория (по умолчанию текущая)
        """
        self.base_dir = base_dir or Path.cwd()
        
        self.data_dir = self.base_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / 'news_database.sqlite'
        self.news_db_path = self.db_path
        
        self.state_file = self.data_dir / 'state.json'
        self.wallet_db_json_path = self.data_dir / 'wallets.json'
        
        self.cache_dir = self.data_dir / 'cache'
        self.logs_dir = self.data_dir / 'logs'
        self.history_dir = self.data_dir / 'history'
        self.learning_dir = self.data_dir / 'learning'
        self.wallets_dir = self.data_dir / 'wallets'
        self.positions_dir = self.data_dir / 'positions'
        self.performance_dir = self.data_dir / 'performance'
        self.backups_dir = self.data_dir / 'backups'
        self.temp_dir = self.data_dir / 'temp'
        
        self._create_directories()
        
        self.log_file_path = self.logs_dir / 'bot.log'
        
        logger.info(f"✅ [PATHS] Data directory: {self.data_dir.absolute()}")
        logger.info(f"✅ [PATHS] Database: {self.db_path.absolute()}")
    
    def _create_directories(self):
        """Создание всех необходимых директорий"""
        directories = [
            self.cache_dir,
            self.logs_dir,
            self.history_dir,
            self.learning_dir,
            self.wallets_dir,
            self.positions_dir,
            self.performance_dir,
            self.backups_dir,
            self.temp_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_backup_path(self, filename: str) -> Path:
        """
        Получение пути для backup файла
        
        Args:
            filename: Имя файла
            
        Returns:
            Путь к backup файлу
        """
        return self.backups_dir / filename
    
    def get_cache_path(self, filename: str) -> Path:
        """Получение пути для кэш файла"""
        return self.cache_dir / filename
    
    def get_log_path(self, filename: str) -> Path:
        """Получение пути для лог файла"""
        return self.logs_dir / filename
    
    def cleanup_temp_dir(self):
        """Очистка временной директории"""
        for file in self.temp_dir.glob('*'):
            try:
                if file.is_file():
                    file.unlink()
            except Exception as e:
                logger.warning(f"⚠️ [PATHS] Не удалось удалить {file}: {e}")
    
    def get_size_mb(self, path: Path = None) -> float:
        """
        Получение размера директории в MB
        
        Args:
            path: Путь к директории (по умолчанию data_dir)
            
        Returns:
            Размер в мегабайтах
        """
        target = path or self.data_dir
        
        if not target.exists():
            return 0.0
        
        total_size = 0
        
        if target.is_file():
            return target.stat().st_size / (1024 * 1024)
        
        for item in target.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                except (OSError, PermissionError):
                    continue
        
        return total_size / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, str]:
        """Конвертация в словарь"""
        return {
            'base_dir': str(self.base_dir),
            'data_dir': str(self.data_dir),
            'db_path': str(self.db_path),
            'cache_dir': str(self.cache_dir),
            'logs_dir': str(self.logs_dir),
            'backups_dir': str(self.backups_dir),
            'data_size_mb': round(self.get_size_mb(), 2)
        }