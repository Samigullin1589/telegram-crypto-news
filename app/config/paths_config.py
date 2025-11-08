"""
Paths Configuration Module
Конфигурация путей к файлам и директориям

Этот модуль автоматически создает необходимые директории
при инициализации если они не существуют.
"""

import os
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class PathsConfig:
    """
    Конфигурация путей приложения
    
    Управляет путями к файлам баз данных, логам, state файлам
    и другим критическим файлам системы.
    
    Автоматически создает директории при инициализации.
    """
    
    def __init__(self):
        """Инициализация путей с автоматическим созданием директорий"""
        
        # ====================================================================
        # БАЗОВЫЕ ДИРЕКТОРИИ
        # ====================================================================
        
        # Главная data директория
        data_dir_str = os.getenv('DATA_DIR', 'data')
        self.data_dir = Path(data_dir_str).resolve()
        
        # Директория для логов
        logs_dir_str = os.getenv('LOGS_DIR', str(self.data_dir / 'logs'))
        self.logs_dir = Path(logs_dir_str).resolve()
        
        # Директория для бэкапов
        backups_dir_str = os.getenv('BACKUPS_DIR', str(self.data_dir / 'backups'))
        self.backups_dir = Path(backups_dir_str).resolve()
        
        # Директория для wallets
        wallets_dir_str = os.getenv('WALLETS_DIR', str(self.data_dir / 'wallets'))
        self.wallets_dir = Path(wallets_dir_str).resolve()
        
        # Директория для exports
        exports_dir_str = os.getenv('EXPORTS_DIR', str(self.data_dir / 'exports'))
        self.exports_dir = Path(exports_dir_str).resolve()
        
        # ====================================================================
        # ФАЙЛЫ БАЗ ДАННЫХ
        # ====================================================================
        
        # Основная база данных
        db_path_str = os.getenv('DB_PATH', str(self.data_dir / 'crypto_monitor.db'))
        self.db_path = Path(db_path_str).resolve()
        
        # База данных новостей
        news_db_str = os.getenv('NEWS_DB_PATH', str(self.data_dir / 'news_database.sqlite'))
        self.news_db_path = Path(news_db_str).resolve()
        
        # База данных метрик
        metrics_db_str = os.getenv('METRICS_DB_PATH', str(self.data_dir / 'metrics.db'))
        self.metrics_db_path = Path(metrics_db_str).resolve()
        
        # ====================================================================
        # STATE И CONFIG ФАЙЛЫ
        # ====================================================================
        
        # State файл (для сохранения состояния между перезапусками)
        state_file_str = os.getenv('STATE_FILE', str(self.data_dir / 'state.json'))
        self.state_file = Path(state_file_str).resolve()
        
        # Wallet tracking JSON
        wallet_db_json_str = os.getenv(
            'WALLET_DB_JSON_PATH',
            str(self.wallets_dir / 'tracked_wallets.json')
        )
        self.wallet_db_json_path = Path(wallet_db_json_str).resolve()
        
        # Cache файлы
        cache_dir_str = os.getenv('CACHE_DIR', str(self.data_dir / 'cache'))
        self.cache_dir = Path(cache_dir_str).resolve()
        
        # ====================================================================
        # ФАЙЛЫ ЛОГОВ
        # ====================================================================
        
        # Основной лог
        main_log_str = os.getenv('MAIN_LOG_FILE', str(self.logs_dir / 'app.log'))
        self.main_log_file = Path(main_log_str).resolve()
        
        # Лог ошибок
        error_log_str = os.getenv('ERROR_LOG_FILE', str(self.logs_dir / 'error.log'))
        self.error_log_file = Path(error_log_str).resolve()
        
        # Лог доступа
        access_log_str = os.getenv('ACCESS_LOG_FILE', str(self.logs_dir / 'access.log'))
        self.access_log_file = Path(access_log_str).resolve()
        
        # ====================================================================
        # СОЗДАНИЕ ДИРЕКТОРИЙ
        # ====================================================================
        
        self._ensure_directories_exist()
        
        logger.debug("PathsConfig инициализирован")
    
    def _ensure_directories_exist(self) -> None:
        """
        Создание всех необходимых директорий
        
        Создает директории если они не существуют.
        Логирует ошибки если не удается создать.
        """
        directories = [
            self.data_dir,
            self.logs_dir,
            self.backups_dir,
            self.wallets_dir,
            self.exports_dir,
            self.cache_dir,
        ]
        
        for directory in directories:
            try:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Создана директория: {directory}")
                else:
                    logger.debug(f"Директория существует: {directory}")
            except Exception as e:
                logger.error(f"Не удалось создать директорию {directory}: {e}")
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    def get_backup_path(self, filename: str) -> Path:
        """
        Получение пути к файлу бэкапа
        
        Args:
            filename: Имя файла бэкапа
            
        Returns:
            Полный путь к файлу бэкапа
        """
        return self.backups_dir / filename
    
    def get_export_path(self, filename: str) -> Path:
        """
        Получение пути к файлу экспорта
        
        Args:
            filename: Имя файла экспорта
            
        Returns:
            Полный путь к файлу экспорта
        """
        return self.exports_dir / filename
    
    def get_cache_path(self, filename: str) -> Path:
        """
        Получение пути к файлу кэша
        
        Args:
            filename: Имя файла кэша
            
        Returns:
            Полный путь к файлу кэша
        """
        return self.cache_dir / filename
    
    def get_wallet_path(self, filename: str) -> Path:
        """
        Получение пути к файлу wallet
        
        Args:
            filename: Имя файла wallet
            
        Returns:
            Полный путь к файлу wallet
        """
        return self.wallets_dir / filename
    
    def cleanup_old_files(self, directory: Path, days: int = 30) -> int:
        """
        Очистка старых файлов в директории
        
        Args:
            directory: Директория для очистки
            days: Удалять файлы старше N дней
            
        Returns:
            Количество удаленных файлов
        """
        import time
        
        if not directory.exists():
            logger.warning(f"Директория не существует: {directory}")
            return 0
        
        deleted_count = 0
        cutoff_time = time.time() - (days * 86400)
        
        try:
            for file_path in directory.iterdir():
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Удален старый файл: {file_path}")
                        except Exception as e:
                            logger.error(f"Не удалось удалить файл {file_path}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при очистке директории {directory}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Удалено старых файлов: {deleted_count} из {directory}")
        
        return deleted_count
    
    def get_directory_size(self, directory: Path) -> int:
        """
        Получение размера директории в байтах
        
        Args:
            directory: Путь к директории
            
        Returns:
            Размер в байтах
        """
        if not directory.exists():
            return 0
        
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.error(f"Ошибка при подсчете размера {directory}: {e}")
        
        return total_size
    
    def get_directory_info(self) -> Dict[str, Dict[str, any]]:
        """
        Получение информации о всех директориях
        
        Returns:
            Словарь с информацией о каждой директории
        """
        directories = {
            'data': self.data_dir,
            'logs': self.logs_dir,
            'backups': self.backups_dir,
            'wallets': self.wallets_dir,
            'exports': self.exports_dir,
            'cache': self.cache_dir,
        }
        
        info = {}
        for name, path in directories.items():
            info[name] = {
                'path': str(path),
                'exists': path.exists(),
                'size_bytes': self.get_directory_size(path) if path.exists() else 0,
                'size_mb': round(self.get_directory_size(path) / (1024 * 1024), 2) if path.exists() else 0,
            }
        
        return info
    
    # ========================================================================
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict[str, str]:
        """
        Конвертация в словарь
        
        Все Path объекты конвертируются в строки.
        
        Returns:
            Словарь со всеми путями (в виде строк)
        """
        return {
            # Директории
            'data_dir': str(self.data_dir),
            'logs_dir': str(self.logs_dir),
            'backups_dir': str(self.backups_dir),
            'wallets_dir': str(self.wallets_dir),
            'exports_dir': str(self.exports_dir),
            'cache_dir': str(self.cache_dir),
            
            # База данных
            'db_path': str(self.db_path),
            'news_db_path': str(self.news_db_path),
            'metrics_db_path': str(self.metrics_db_path),
            
            # State и config
            'state_file': str(self.state_file),
            'wallet_db_json_path': str(self.wallet_db_json_path),
            
            # Логи
            'main_log_file': str(self.main_log_file),
            'error_log_file': str(self.error_log_file),
            'access_log_file': str(self.access_log_file),
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return f"PathsConfig(data_dir={self.data_dir})"