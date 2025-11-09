# core/logging_config.py
"""
Production Logging Configuration
Оптимизировано для Render.com (только stdout, без файлов)
"""

import sys
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler
import os


class RenderCompatibleFormatter(logging.Formatter):
    """Форматтер с поддержкой цветного вывода и Render"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True):
        """
        Args:
            fmt: Формат сообщения
            use_colors: Использовать цвета (отключается в production)
        """
        super().__init__(fmt or '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование с опциональными цветами"""
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class LoggingConfig:
    """Централизованная конфигурация логирования"""
    
    def __init__(self):
        """Инициализация конфигурации"""
        self.is_production = os.getenv('RENDER', '').lower() == 'true'
        self.log_level = self._determine_log_level()
        self.log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'
    
    def _determine_log_level(self) -> int:
        """
        Определение уровня логирования
        
        Returns:
            int: Уровень логирования
        """
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        return level_map.get(level_str, logging.INFO)
    
    def setup(self) -> None:
        """Настройка логирования"""
        # Очищаем существующие handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Устанавливаем уровень
        root_logger.setLevel(self.log_level)
        
        # Создаем форматтер
        use_colors = not self.is_production
        formatter = RenderCompatibleFormatter(
            fmt=self.log_format,
            use_colors=use_colors
        )
        
        # Stdout handler (основной для Render)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(self.log_level)
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)
        
        # Опциональный файловый handler (только для локальной разработки)
        if not self.is_production:
            self._add_file_handler(root_logger, formatter)
        
        # Настраиваем уровни для сторонних библиотек
        self._configure_third_party_loggers()
    
    def _add_file_handler(
        self,
        logger: logging.Logger,
        formatter: logging.Formatter
    ) -> None:
        """
        Добавление файлового handler для локальной разработки
        
        Args:
            logger: Logger для настройки
            formatter: Форматтер
        """
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, 'crypto_monitor.log')
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        except (OSError, PermissionError) as e:
            # Если не удалось создать файл - продолжаем без него
            logging.warning(f"Cannot create log file: {e}")
    
    def _configure_third_party_loggers(self) -> None:
        """Настройка уровней логирования сторонних библиотек"""
        # Снижаем уровень для шумных библиотек
        noisy_loggers = [
            'asyncio',
            'aiohttp',
            'telegram',
            'httpx',
            'urllib3',
            'web3',
            'solana'
        ]
        
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def setup_logging() -> None:
    """
    Публичная функция для настройки логирования
    Вызывается из main.py
    """
    config = LoggingConfig()
    config.setup()
    
    logger = logging.getLogger(__name__)
    logger.info("✅ Logging configured successfully")
    
    if config.is_production:
        logger.info("🔧 Running in PRODUCTION mode (Render)")
    else:
        logger.info("🔧 Running in DEVELOPMENT mode")


def get_logger(name: str) -> logging.Logger:
    """
    Получение настроенного логгера
    
    Args:
        name: Имя логгера
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    return logging.getLogger(name)