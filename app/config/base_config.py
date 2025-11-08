"""
Base Configuration Module
Базовые настройки приложения и окружения
"""

import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """
    Базовая конфигурация приложения
    Содержит общие настройки окружения и режимов работы
    """
    
    def __init__(self):
        """Инициализация базовых настроек"""
        
        # Debug и Logging
        self.DEBUG_MODE = self._get_bool_env('DEBUG', False)
        self.DEBUG = self.DEBUG_MODE  # Алиас для совместимости
        self.VERBOSE_LOGGING = self._get_bool_env('VERBOSE_LOGGING', False)
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
        # Log Files
        self.LOG_FILE_ENABLED = self._get_bool_env('LOG_FILE_ENABLED', False)
        self.LOG_FILE_MAX_SIZE_MB = self._get_int_env('LOG_FILE_MAX_SIZE_MB', 50)
        self.LOG_FILE_BACKUP_COUNT = self._get_int_env('LOG_FILE_BACKUP_COUNT', 5)
        
        # Application
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
        self.APP_NAME = os.getenv('APP_NAME', 'CryptoCompass')
        self.APP_VERSION = os.getenv('APP_VERSION', '4.2.0')
        
        # Server
        self.PORT = self._get_int_env('PORT', 8000)
        self.HOST = os.getenv('HOST', '0.0.0.0')
        
        # Timeouts
        self.HTTP_TIMEOUT = self._get_int_env('HTTP_TIMEOUT', 30)
        self.RPC_TIMEOUT = self._get_int_env('RPC_TIMEOUT', 15)
        self.WEBHOOK_TIMEOUT = self._get_int_env('WEBHOOK_TIMEOUT', 10)
        
        # Session Settings
        self.SESSION_TIMEOUT_TOTAL = self._get_int_env('SESSION_TIMEOUT_TOTAL', 300)
        self.SESSION_TIMEOUT_CONNECT = self._get_int_env('SESSION_TIMEOUT_CONNECT', 30)
        self.SESSION_MAX_RETRIES = self._get_int_env('SESSION_MAX_RETRIES', 3)
        self.SESSION_RETRY_DELAY = self._get_int_env('SESSION_RETRY_DELAY', 5)
        
        # Connection Pool
        self.CONNECTION_POOL_SIZE = self._get_int_env('CONNECTION_POOL_SIZE', 100)
        self.CONNECTION_POOL_MAX_SIZE = self._get_int_env('CONNECTION_POOL_MAX_SIZE', 200)
        
        # Memory Management
        self.MAX_MEMORY_MB = self._get_int_env('MAX_MEMORY_MB', 450)
        self.GC_INTERVAL_SECONDS = self._get_int_env('GC_INTERVAL_SECONDS', 300)
        self.GC_THRESHOLD = (700, 10, 10)
        
        # Health Check
        self.HEALTH_CHECK_ENABLED = self._get_bool_env('HEALTH_CHECK_ENABLED', True)
        self.HEALTH_CHECK_INTERVAL = self._get_int_env('HEALTH_CHECK_INTERVAL', 300)
        self.HEALTH_CHECK_TIMEOUT = self._get_int_env('HEALTH_CHECK_TIMEOUT', 10)
        
        # Metrics
        self.METRICS_ENABLED = self._get_bool_env('METRICS_ENABLED', True)
        self.METRICS_INTERVAL = self._get_int_env('METRICS_INTERVAL', 60)
        self.METRICS_RETENTION_HOURS = self._get_int_env('METRICS_RETENTION_HOURS', 24)
        
        # HTTP Headers
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
            'Cache-Control': 'max-age=0'
        }
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Получение boolean переменной окружения"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Получение integer переменной окружения"""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """Получение float переменной окружения"""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def is_development(self) -> bool:
        """Проверка режима разработки"""
        return self.ENVIRONMENT.lower() in ('development', 'dev')
    
    def is_production(self) -> bool:
        """Проверка production режима"""
        return self.ENVIRONMENT.lower() in ('production', 'prod')
    
    def is_staging(self) -> bool:
        """Проверка staging режима"""
        return self.ENVIRONMENT.lower() in ('staging', 'stage')
    
    def get_timeout_config(self) -> Dict[str, int]:
        """Получение конфигурации таймаутов"""
        return {
            'http': self.HTTP_TIMEOUT,
            'rpc': self.RPC_TIMEOUT,
            'webhook': self.WEBHOOK_TIMEOUT,
            'session_total': self.SESSION_TIMEOUT_TOTAL,
            'session_connect': self.SESSION_TIMEOUT_CONNECT
        }
    
    def get_session_config(self) -> Dict[str, int]:
        """Получение конфигурации сессий"""
        return {
            'timeout_total': self.SESSION_TIMEOUT_TOTAL,
            'timeout_connect': self.SESSION_TIMEOUT_CONNECT,
            'max_retries': self.SESSION_MAX_RETRIES,
            'retry_delay': self.SESSION_RETRY_DELAY,
            'pool_size': self.CONNECTION_POOL_SIZE,
            'pool_max_size': self.CONNECTION_POOL_MAX_SIZE
        }
    
    def get_memory_config(self) -> Dict[str, Any]:
        """Получение конфигурации управления памятью"""
        return {
            'max_memory_mb': self.MAX_MEMORY_MB,
            'gc_interval_seconds': self.GC_INTERVAL_SECONDS,
            'gc_threshold': self.GC_THRESHOLD
        }
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Получение конфигурации health check"""
        return {
            'enabled': self.HEALTH_CHECK_ENABLED,
            'interval': self.HEALTH_CHECK_INTERVAL,
            'timeout': self.HEALTH_CHECK_TIMEOUT
        }
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """Получение конфигурации метрик"""
        return {
            'enabled': self.METRICS_ENABLED,
            'interval': self.METRICS_INTERVAL,
            'retention_hours': self.METRICS_RETENTION_HOURS
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
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