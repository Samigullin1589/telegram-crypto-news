# app/config/paths.py
"""
Path management for configuration
"""

import os
from pathlib import Path
from typing import List


class PathManager:
    """Управление путями и директориями"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / 'state.json'
        self.wallet_db_path = self.data_dir / 'wallets' / 'tracked_wallets.json'
        self.watchlist_file = self.data_dir / 'wallets' / 'watchlist.json'
        self.history_file = self.data_dir / 'history' / 'events.json'
        self.positions_dir = self.data_dir / 'positions'
        self.performance_dir = self.data_dir / 'performance'
        self.backups_dir = self.data_dir / 'backups'
        self.cache_dir = self.data_dir / 'cache'
        self.learning_dir = self.data_dir / 'learning'
        self.logs_dir = Path('logs')
    
    def get_required_directories(self) -> List[Path]:
        """Возвращает список обязательных директорий"""
        return [
            self.data_dir,
            self.data_dir / 'history',
            self.data_dir / 'learning',
            self.data_dir / 'wallets',
            self.data_dir / 'positions',
            self.data_dir / 'performance',
            self.data_dir / 'backups',
            self.data_dir / 'cache',
            self.positions_dir,
            self.performance_dir,
            self.logs_dir
        ]
    
    def create_directories(self) -> List[str]:
        """
        Создает все необходимые директории
        
        Returns:
            Список ошибок при создании
        """
        errors = []
        
        for directory in self.get_required_directories():
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                error_msg = f'Не удалось создать директорию {directory}: {e}'
                errors.append(error_msg)
                print(f'⚠️  [CONFIG] {error_msg}')
        
        return errors
    
    def validate_paths(self) -> List[str]:
        """
        Проверяет существование критичных директорий
        
        Returns:
            Список предупреждений
        """
        warnings = []
        
        critical_dirs = [
            self.data_dir,
            self.data_dir / 'wallets'
        ]
        
        for directory in critical_dirs:
            if not directory.exists():
                warnings.append(f'Критичная директория не существует: {directory}')
        
        return warnings
    
    def get_absolute_path(self, relative_path: str) -> str:
        """Возвращает абсолютный путь"""
        return str(Path(relative_path).resolve())


class EnvironmentPaths:
    """Пути из переменных окружения"""
    
    @staticmethod
    def get_data_dir() -> str:
        """Получает DATA_DIR из env"""
        return os.getenv('DATA_DIR', 'data')
    
    @staticmethod
    def get_state_file() -> str:
        """Получает STATE_FILE из env"""
        return os.getenv('STATE_FILE', 'state.json')
    
    @staticmethod
    def get_wallet_db_path() -> str:
        """Получает WALLET_DB_JSON_PATH из env"""
        return os.getenv('WALLET_DB_JSON_PATH', 'data/wallets/tracked_wallets.json')
    
    @staticmethod
    def get_watchlist_file() -> str:
        """Получает WATCHLIST_FILE из env"""
        return os.getenv('WATCHLIST_FILE', 'data/wallets/watchlist.json')
    
    @staticmethod
    def get_history_file() -> str:
        """Получает HISTORY_FILE из env"""
        return os.getenv('HISTORY_FILE', 'data/history/events.json')
    
    @staticmethod
    def get_positions_dir() -> str:
        """Получает POSITIONS_DIR из env"""
        return os.getenv('POSITIONS_DIR', 'data/positions')
    
    @staticmethod
    def get_performance_dir() -> str:
        """Получает PERFORMANCE_DIR из env"""
        return os.getenv('PERFORMANCE_DIR', 'data/performance')