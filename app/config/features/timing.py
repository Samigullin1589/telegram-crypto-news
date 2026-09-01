"""
Timing configuration module
Настройки интервалов, задержек и таймаутов
"""

import logging
from typing import Dict
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class TimingConfig(BaseFeatureConfig):
    """
    Конфигурация таймингов системы
    
    Управляет:
    - Интервалами проверок
    - Задержками между действиями
    - Таймаутами запросов
    - Rate limiting
    """
    
    def __init__(self):
        """Инициализация таймингов"""
        
        # Интервалы проверок (секунды)
        self.fetch_interval = self.get_int_env('FETCH_INTERVAL', 900)
        self.news_check_interval = self.get_int_env('NEWS_CHECK_INTERVAL', self.fetch_interval)
        self.whale_check_interval = self.get_int_env('WHALE_CHECK_INTERVAL', 60)
        self.trading_check_interval = self.get_int_env('TRADING_CHECK_INTERVAL', 300)
        self.analytics_check_interval = self.get_int_env('ANALYTICS_CHECK_INTERVAL', 600)
        self.health_check_interval = self.get_int_env('HEALTH_CHECK_INTERVAL', 300)
        
        # Задержки между действиями (секунды)
        self.post_delay_seconds = self.get_int_env('POST_DELAY_SECONDS', 900)
        self.idle_delay_seconds = self.get_int_env('IDLE_DELAY_SECONDS', 300)
        self.rate_limit_delay_seconds = self.get_int_env('RATE_LIMIT_DELAY_SECONDS', 60)
        self.error_retry_delay = self.get_int_env('ERROR_RETRY_DELAY', 30)
        self.cooldown_period = self.get_int_env('COOLDOWN_PERIOD', 120)
        
        # Таймауты запросов (секунды)
        self.feed_fetch_timeout = self.get_int_env('FEED_FETCH_TIMEOUT', 30)
        self.blockchain_request_timeout = self.get_int_env('BLOCKCHAIN_REQUEST_TIMEOUT', 30)
        self.trading_analysis_timeout = self.get_int_env('TRADING_ANALYSIS_TIMEOUT', 60)
        self.api_request_timeout = self.get_int_env('API_REQUEST_TIMEOUT', 30)
        self.database_query_timeout = self.get_int_env('DATABASE_QUERY_TIMEOUT', 10)
        self.ai_request_timeout = self.get_int_env('AI_REQUEST_TIMEOUT', 60)
        
        # Интервалы повторных попыток
        self.max_retries = self.get_int_env('MAX_RETRIES', 3)
        self.retry_backoff_base = self.get_float_env('RETRY_BACKOFF_BASE', 2.0)
        self.retry_initial_delay = self.get_int_env('RETRY_INITIAL_DELAY', 5)
        self.retry_max_delay = self.get_int_env('RETRY_MAX_DELAY', 300)
        
        # Rate limiting
        self.rate_limit_enabled = self.get_bool_env('RATE_LIMIT_ENABLED', True)
        self.rate_limit_window = self.get_int_env('RATE_LIMIT_WINDOW', 60)
        self.rate_limit_max_requests = self.get_int_env('RATE_LIMIT_MAX_REQUESTS', 100)
        
        # Логирование
        self._log_configuration()
    
    def _log_configuration(self):
        """Логирование конфигурации таймингов"""
        logger.debug(f"[TIMING] Check intervals: news={self.news_check_interval}s, "
                    f"whale={self.whale_check_interval}s, "
                    f"trading={self.trading_check_interval}s")
        logger.debug(f"[TIMING] Timeouts: feed={self.feed_fetch_timeout}s, "
                    f"blockchain={self.blockchain_request_timeout}s, "
                    f"api={self.api_request_timeout}s")
    
    def get_check_interval(self, feature: str) -> int:
        """
        Получение интервала проверки для модуля
        
        Args:
            feature: Название модуля
            
        Returns:
            int: Интервал проверки в секундах
        """
        intervals_map = {
            'news': self.news_check_interval,
            'whale': self.whale_check_interval,
            'whale_alerts': self.whale_check_interval,
            'trading': self.trading_check_interval,
            'analytics': self.analytics_check_interval,
            'health': self.health_check_interval
        }
        
        return intervals_map.get(feature.lower(), self.fetch_interval)
    
    def get_timeout(self, operation: str) -> int:
        """
        Получение таймаута для операции
        
        Args:
            operation: Тип операции
            
        Returns:
            int: Таймаут в секундах
        """
        timeouts_map = {
            'feed': self.feed_fetch_timeout,
            'blockchain': self.blockchain_request_timeout,
            'trading': self.trading_analysis_timeout,
            'api': self.api_request_timeout,
            'database': self.database_query_timeout,
            'ai': self.ai_request_timeout
        }
        
        return timeouts_map.get(operation.lower(), self.api_request_timeout)
    
    def calculate_retry_delay(self, attempt: int) -> int:
        """
        Вычисление задержки для повторной попытки с экспоненциальным backoff
        
        Args:
            attempt: Номер попытки (начиная с 1)
            
        Returns:
            int: Задержка в секундах
        """
        delay = self.retry_initial_delay * (self.retry_backoff_base ** (attempt - 1))
        return min(int(delay), self.retry_max_delay)
    
    def get_all_timings(self) -> Dict[str, int]:
        """
        Получение всех настроек таймингов
        
        Returns:
            Dict: Словарь всех таймингов
        """
        return {
            'fetch_interval': self.fetch_interval,
            'news_check_interval': self.news_check_interval,
            'whale_check_interval': self.whale_check_interval,
            'trading_check_interval': self.trading_check_interval,
            'analytics_check_interval': self.analytics_check_interval,
            'health_check_interval': self.health_check_interval,
            'post_delay': self.post_delay_seconds,
            'idle_delay': self.idle_delay_seconds,
            'rate_limit_delay': self.rate_limit_delay_seconds,
            'error_retry_delay': self.error_retry_delay,
            'cooldown_period': self.cooldown_period,
            'feed_timeout': self.feed_fetch_timeout,
            'blockchain_timeout': self.blockchain_request_timeout,
            'trading_timeout': self.trading_analysis_timeout,
            'api_timeout': self.api_request_timeout,
            'database_timeout': self.database_query_timeout,
            'ai_timeout': self.ai_request_timeout,
            'max_retries': self.max_retries,
            'retry_initial_delay': self.retry_initial_delay,
            'retry_max_delay': self.retry_max_delay
        }


__all__ = ['TimingConfig']