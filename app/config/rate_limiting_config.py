# app/config/rate_limiting_config.py
"""
Rate Limiting Configuration Module
Конфигурация ограничений частоты запросов
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RateLimitingConfig:
    """
    Конфигурация rate limiting
    Управление частотой запросов к различным API
    """
    
    def __init__(self):
        """Инициализация конфигурации rate limiting"""
        
        self.rate_limit_enabled = self._get_bool_env('RATE_LIMIT_ENABLED', True)
        
        self.max_requests_per_minute = int(
            os.getenv('MAX_REQUESTS_PER_MINUTE', '60')
        )
        self.max_api_calls_per_second = int(
            os.getenv('MAX_API_CALLS_PER_SECOND', '5')
        )
        self.rate_limit_burst = int(os.getenv('RATE_LIMIT_BURST', '10'))
        
        self.retry_enabled = self._get_bool_env('RETRY_ENABLED', True)
        self.retry_max_attempts = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
        self.retry_initial_delay = int(os.getenv('RETRY_INITIAL_DELAY', '1'))
        self.retry_max_delay = int(os.getenv('RETRY_MAX_DELAY', '60'))
        self.retry_exponential_base = int(os.getenv('RETRY_EXPONENTIAL_BASE', '2'))
        
        self.api_rate_limits = {
            'etherscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5
            },
            'bscscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5
            },
            'polygonscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5
            },
            'coingecko_free': {
                'calls_per_minute': 10,
                'calls_per_month': 10000,
                'burst': 3
            },
            'coingecko_pro': {
                'calls_per_minute': 500,
                'calls_per_month': 500000,
                'burst': 10
            },
            'openai': {
                'calls_per_minute': 60,
                'tokens_per_minute': 90000,
                'burst': 10
            },
            'anthropic': {
                'calls_per_minute': 50,
                'tokens_per_minute': 100000,
                'burst': 5
            },
            'gemini': {
                'calls_per_minute': 60,
                'tokens_per_minute': 32000,
                'burst': 10
            },
            'telegram': {
                'calls_per_second': 30,
                'messages_per_minute': 20,
                'burst': 1
            },
            'solana_public': {
                'calls_per_second': 1,
                'calls_per_minute': 40,
                'burst': 2
            },
            'solana_helius': {
                'calls_per_second': 10,
                'calls_per_day': 100000,
                'burst': 5
            }
        }
        
        logger.info(
            f"✅ [RATE_LIMIT] Enabled: {self.rate_limit_enabled}, "
            f"Max: {self.max_requests_per_minute}/min"
        )
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Получение boolean переменной"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_api_limits(self, api_name: str) -> Optional[Dict]:
        """
        Получение лимитов для конкретного API
        
        Args:
            api_name: Название API
            
        Returns:
            Словарь с лимитами или None
        """
        return self.api_rate_limits.get(api_name)
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Расчет задержки для retry
        
        Args:
            attempt: Номер попытки (0-based)
            
        Returns:
            Задержка в секундах
        """
        if not self.retry_enabled:
            return 0
        
        delay = self.retry_initial_delay * (
            self.retry_exponential_base ** attempt
        )
        
        return min(delay, self.retry_max_delay)
    
    def should_retry(self, attempt: int) -> bool:
        """
        Проверка необходимости повтора
        
        Args:
            attempt: Номер попытки (1-based)
            
        Returns:
            True если нужен повтор
        """
        if not self.retry_enabled:
            return False
        
        return attempt <= self.retry_max_attempts
    
    def get_burst_allowance(self, api_name: str = None) -> int:
        """
        Получение burst allowance
        
        Args:
            api_name: Название API (опционально)
            
        Returns:
            Burst allowance
        """
        if api_name and api_name in self.api_rate_limits:
            return self.api_rate_limits[api_name].get('burst', self.rate_limit_burst)
        
        return self.rate_limit_burst
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'enabled': self.rate_limit_enabled,
            'global': {
                'max_requests_per_minute': self.max_requests_per_minute,
                'max_calls_per_second': self.max_api_calls_per_second,
                'burst': self.rate_limit_burst
            },
            'retry': {
                'enabled': self.retry_enabled,
                'max_attempts': self.retry_max_attempts,
                'initial_delay': self.retry_initial_delay,
                'max_delay': self.retry_max_delay,
                'exponential_base': self.retry_exponential_base
            },
            'api_limits': {
                name: limits for name, limits in self.api_rate_limits.items()
            }
        }