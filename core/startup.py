# core/startup.py
"""
Startup validation and initialization
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple

logger = logging.getLogger(__name__)


class StartupValidator:
    """Валидация окружения при запуске"""
    
    REQUIRED_PACKAGES = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp',
        'feedparser': 'feedparser',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
        'psutil': 'psutil',
        'web3': 'web3',
        'solana': 'solana',
        'ccxt': 'ccxt',
        'sqlalchemy': 'sqlalchemy'
    }
    
    REQUIRED_DIRECTORIES = [
        'data',
        'data/history',
        'data/learning',
        'data/wallets',
        'data/positions',
        'data/performance',
        'data/backups',
        'data/cache',
        'logs'
    ]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> bool:
        """Выполняет все проверки"""
        self._print_system_info()
        
        deps_ok = self._check_dependencies()
        dirs_ok = self._create_directories()
        env_ok = self._check_environment()
        
        if self.warnings:
            logger.warning("\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for warning in self.warnings:
                logger.warning(f"   {warning}")
        
        if self.errors:
            logger.error("\n❌ ОШИБКИ:")
            for error in self.errors:
                logger.error(f"   {error}")
            return False
        
        logger.info("\n✅ Все проверки пройдены успешно\n")
        return True
    
    def _print_system_info(self):
        """Выводит информацию о системе"""
        logger.info("=" * 80)
        logger.info("💎 CRYPTO COMPASS - Integrated Monitoring System v4.5")
        logger.info("=" * 80)
        logger.info(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"🐍 Python {sys.version.split()[0]}")
        logger.info(f"💻 Platform: {sys.platform}")
        logger.info(f"📂 Working Directory: {os.getcwd()}")
        logger.info("=" * 80 + "\n")
    
    def _check_dependencies(self) -> bool:
        """Проверяет установленные зависимости"""
        logger.info("🔍 Проверка зависимостей...\n")
        
        missing = []
        
        for module, package in self.REQUIRED_PACKAGES.items():
            try:
                __import__(module)
                logger.info(f"   ✅ {package}")
            except ImportError:
                logger.error(f"   ❌ {package}")
                missing.append(package)
        
        if missing:
            error_msg = f"Отсутствуют зависимости: {', '.join(missing)}"
            self.errors.append(error_msg)
            logger.info(f"\nУстановите их: pip install {' '.join(missing)}")
            return False
        
        logger.info("\n✅ Все зависимости установлены")
        return True
    
    def _create_directories(self) -> bool:
        """Создает необходимые директории"""
        logger.info("\n📁 Создание директорий...\n")
        
        success = True
        
        for dir_path in self.REQUIRED_DIRECTORIES:
            directory = Path(dir_path)
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"   ✅ {directory}")
            except OSError as e:
                warning_msg = f"Не удалось создать {directory}: {e}"
                self.warnings.append(warning_msg)
                logger.warning(f"   ⚠️  {directory}: {e}")
                success = False
        
        logger.info("")
        return success
    
    def _check_environment(self) -> bool:
        """Проверяет переменные окружения"""
        logger.info("🔐 Проверка переменных окружения...\n")
        
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHANNEL_ID'
        ]
        
        missing_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
                logger.info(f"   ✅ {var}: {masked_value}")
            else:
                logger.error(f"   ❌ {var}: не установлена")
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Не установлены переменные: {', '.join(missing_vars)}"
            self.errors.append(error_msg)
            return False
        
        logger.info("\n✅ Все обязательные переменные установлены")
        return True


class DirectoryManager:
    """Управление директориями проекта"""
    
    @staticmethod
    def ensure_directories(directories: List[Path]) -> Tuple[List[Path], List[Tuple[Path, Exception]]]:
        """
        Создает директории и возвращает результаты
        
        Returns:
            (created_dirs, failed_dirs)
        """
        created = []
        failed = []
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                created.append(directory)
            except OSError as e:
                failed.append((directory, e))
        
        return created, failed
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Получает временную директорию"""
        tmp_dir = Path("/tmp") if Path("/tmp").exists() else Path("./tmp")
        tmp_dir.mkdir(exist_ok=True)
        return tmp_dir