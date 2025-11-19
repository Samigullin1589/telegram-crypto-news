"""
Base Configuration Module
Базовые настройки приложения и окружения

ВАЖНО: Этот модуль НЕ загружает .env файл напрямую.
Загрузка происходит в env_loader.py ДО инициализации конфигурации.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BaseConfig:
    """
    Базовая конфигурация приложения
    
    Содержит общие настройки окружения, режимов работы,
    таймаутов, управления памятью и метрик.
    
    Все значения читаются из переменных окружения с
    разумными значениями по умолчанию.
    """
    
    def __init__(self):
        """Инициализация базовых настроек"""
        
        # ====================================================================
        # DEBUG И LOGGING
        # ====================================================================
        
        self.DEBUG_MODE = self._get_bool_env('DEBUG', False)
        self.DEBUG = self.DEBUG_MODE  # Алиас для совместимости
        self.VERBOSE_LOGGING = self._get_bool_env('VERBOSE_LOGGING', False)
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
        # Log Files
        self.LOG_FILE_ENABLED = self._get_bool_env('LOG_FILE_ENABLED', False)
        self.LOG_FILE_MAX_SIZE_MB = self._get_int_env('LOG_FILE_MAX_SIZE_MB', 50)
        self.LOG_FILE_BACKUP_COUNT = self._get_int_env('LOG_FILE_BACKUP_COUNT', 5)
        
        # ====================================================================
        # APPLICATION
        # ====================================================================
        
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
        self.APP_NAME = os.getenv('APP_NAME', 'CryptoCompass')
        self.APP_VERSION = os.getenv('APP_VERSION', '3.0.0')
        
        # ====================================================================
        # SERVER
        # ====================================================================
        
        self.PORT = self._get_int_env('PORT', 8000)
        self.HOST = os.getenv('HOST', '0.0.0.0')
        
        # ====================================================================
        # TIMEOUTS
        # ====================================================================
        
        self.HTTP_TIMEOUT = self._get_int_env('HTTP_TIMEOUT', 30)
        self.RPC_TIMEOUT = self._get_int_env('RPC_TIMEOUT', 15)
        self.WEBHOOK_TIMEOUT = self._get_int_env('WEBHOOK_TIMEOUT', 10)
        
        # ====================================================================
        # SESSION SETTINGS
        # ====================================================================
        
        self.SESSION_TIMEOUT_TOTAL = self._get_int_env('SESSION_TIMEOUT_TOTAL', 300)
        self.SESSION_TIMEOUT_CONNECT = self._get_int_env('SESSION_TIMEOUT_CONNECT', 30)
        self.SESSION_MAX_RETRIES = self._get_int_env('SESSION_MAX_RETRIES', 3)
        self.SESSION_RETRY_DELAY = self._get_int_env('SESSION_RETRY_DELAY', 5)
        
        # ====================================================================
        # CONNECTION POOL
        # ====================================================================
        
        self.CONNECTION_POOL_SIZE = self._get_int_env('CONNECTION_POOL_SIZE', 100)
        self.CONNECTION_POOL_MAX_SIZE = self._get_int_env('CONNECTION_POOL_MAX_SIZE', 200)
        
        # ====================================================================
        # MEMORY MANAGEMENT
        # ====================================================================
        
        self.MAX_MEMORY_MB = self._get_int_env('MAX_MEMORY_MB', 450)
        self.GC_INTERVAL_SECONDS = self._get_int_env('GC_INTERVAL_SECONDS', 300)
        self.GC_THRESHOLD = (700, 10, 10)  # Пороги для garbage collector
        
        # ====================================================================
        # HEALTH CHECK
        # ====================================================================
        
        self.HEALTH_CHECK_ENABLED = self._get_bool_env('HEALTH_CHECK_ENABLED', True)
        self.HEALTH_CHECK_INTERVAL = self._get_int_env('HEALTH_CHECK_INTERVAL', 300)
        self.HEALTH_CHECK_TIMEOUT = self._get_int_env('HEALTH_CHECK_TIMEOUT', 10)
        
        # ====================================================================
        # METRICS
        # ====================================================================
        
        self.METRICS_ENABLED = self._get_bool_env('METRICS_ENABLED', False)
        self.METRICS_INTERVAL = self._get_int_env('METRICS_INTERVAL', 60)
        self.METRICS_RETENTION_HOURS = self._get_int_env('METRICS_RETENTION_HOURS', 24)
        
        # ====================================================================
        # HTTP HEADERS
        # ====================================================================
        
        self.COMMON_HEADERS = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }

        # Алиасы для обратной совместимости (маленькими буквами)
        self.port = self.PORT
        self.http_timeout = self.HTTP_TIMEOUT
        self.max_memory_mb = self.MAX_MEMORY_MB

        logger.debug("BaseConfig инициализирован")
    
    # ========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ========================================================================
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """
        Получение boolean переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            True если переменная установлена в 'true', '1', 'yes', 'on'
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """
        Получение integer переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            Целое число или default при ошибке парсинга
        """
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Некорректное значение для {key}, используется default: {default}")
            return default
    
    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """
        Получение float переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            Число с плавающей точкой или default при ошибке парсинга
        """
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Некорректное значение для {key}, используется default: {default}")
            return default
    
    # ========================================================================
    # ПРОВЕРКИ ОКРУЖЕНИЯ
    # ========================================================================
    
    def is_development(self) -> bool:
        """
        Проверка режима разработки
        
        Returns:
            True если окружение development или dev
        """
        return self.ENVIRONMENT.lower() in ('development', 'dev', 'local')
    
    def is_production(self) -> bool:
        """
        Проверка production режима
        
        Returns:
            True если окружение production или prod
        """
        return self.ENVIRONMENT.lower() in ('production', 'prod')
    
    def is_staging(self) -> bool:
        """
        Проверка staging режима
        
        Returns:
            True если окружение staging или stage
        """
        return self.ENVIRONMENT.lower() in ('staging', 'stage', 'test')
    
    # ========================================================================
    # ГЕТТЕРЫ КОНФИГУРАЦИИ
    # ========================================================================
    
    def get_timeout_config(self) -> Dict[str, int]:
        """
        Получение конфигурации таймаутов
        
        Returns:
            Словарь с настройками таймаутов
        """
        return {
            'http': self.HTTP_TIMEOUT,
            'rpc': self.RPC_TIMEOUT,
            'webhook': self.WEBHOOK_TIMEOUT,
            'session_total': self.SESSION_TIMEOUT_TOTAL,
            'session_connect': self.SESSION_TIMEOUT_CONNECT
        }
    
    def get_session_config(self) -> Dict[str, int]:
        """
        Получение конфигурации сессий
        
        Returns:
            Словарь с настройками сессий и пулов соединений
        """
        return {
            'timeout_total': self.SESSION_TIMEOUT_TOTAL,
            'timeout_connect': self.SESSION_TIMEOUT_CONNECT,
            'max_retries': self.SESSION_MAX_RETRIES,
            'retry_delay': self.SESSION_RETRY_DELAY,
            'pool_size': self.CONNECTION_POOL_SIZE,
            'pool_max_size': self.CONNECTION_POOL_MAX_SIZE
        }
    
    def get_memory_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации управления памятью
        
        Returns:
            Словарь с настройками памяти и GC
        """
        return {
            'max_memory_mb': self.MAX_MEMORY_MB,
            'gc_interval_seconds': self.GC_INTERVAL_SECONDS,
            'gc_threshold': self.GC_THRESHOLD
        }
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации health check
        
        Returns:
            Словарь с настройками health check
        """
        return {
            'enabled': self.HEALTH_CHECK_ENABLED,
            'interval': self.HEALTH_CHECK_INTERVAL,
            'timeout': self.HEALTH_CHECK_TIMEOUT
        }
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации метрик
        
        Returns:
            Словарь с настройками метрик
        """
        return {
            'enabled': self.METRICS_ENABLED,
            'interval': self.METRICS_INTERVAL,
            'retention_hours': self.METRICS_RETENTION_HOURS
        }
    
    # ========================================================================
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация в словарь
        
        Returns:
            Словарь со всеми параметрами базовой конфигурации
        """
        return {
            'environment': self.ENVIRONMENT,
            'app_name': self.APP_NAME,
            'app_version': self.APP_VERSION,
            'debug_mode': self.DEBUG_MODE,
            'log_level': self.LOG_LEVEL,
            'verbose_logging': self.VERBOSE_LOGGING,
            'port': self.PORT,
            'host': self.HOST,
            'timeouts': self.get_timeout_config(),
            'session': self.get_session_config(),
            'memory': self.get_memory_config(),
            'health_check': self.get_health_check_config(),
            'metrics': self.get_metrics_config()
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"BaseConfig("
            f"env={self.ENVIRONMENT}, "
            f"port={self.PORT}, "
            f"debug={self.DEBUG_MODE}"
            f")"
        )