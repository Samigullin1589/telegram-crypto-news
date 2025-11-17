"""
Rate Limiting Configuration Module
Конфигурация ограничений частоты запросов

Управляет:
- Глобальными лимитами запросов
- API-специфичными лимитами
- Retry политиками
- Burst allowance
"""

import os
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class RateLimitingConfig:
    """
    Конфигурация rate limiting
    
    Управляет частотой запросов к различным API и внутренним сервисам.
    Поддерживает глобальные лимиты, API-специфичные настройки,
    retry механизмы и burst allowance.
    
    Attributes:
        enabled: Глобальное включение/выключение rate limiting
        max_requests_per_minute: Максимум запросов в минуту (глобально)
        max_api_calls_per_second: Максимум вызовов API в секунду
        burst_size: Размер burst для пиковых нагрузок
        retry_enabled: Включение автоматических повторов
        retry_max_attempts: Максимум попыток повтора
        api_rate_limits: Словарь с лимитами для каждого API
    """
    
    def __init__(self):
        """Инициализация конфигурации rate limiting из переменных окружения"""
        
        # Глобальное включение rate limiting
        self.enabled = self._get_bool_env('RATE_LIMIT_ENABLED', True)
        
        # Для обратной совместимости
        self.rate_limit_enabled = self.enabled

        # Глобальные лимиты
        self.max_requests_per_minute = self._get_int_env(
            'MAX_REQUESTS_PER_MINUTE',
            60
        )

        # Для обратной совместимости
        self.calls_per_minute = self.max_requests_per_minute
        
        self.max_api_calls_per_second = self._get_int_env(
            'MAX_API_CALLS_PER_SECOND', 
            5
        )
        
        self.burst_size = self._get_int_env('RATE_LIMIT_BURST', 10)
        
        # Для обратной совместимости
        self.rate_limit_burst = self.burst_size
        
        # Retry настройки
        self.retry_enabled = self._get_bool_env('RETRY_ENABLED', True)
        self.retry_max_attempts = self._get_int_env('RETRY_MAX_ATTEMPTS', 3)
        self.retry_initial_delay = self._get_int_env('RETRY_INITIAL_DELAY', 1)
        self.retry_max_delay = self._get_int_env('RETRY_MAX_DELAY', 60)
        self.retry_exponential_base = self._get_int_env('RETRY_EXPONENTIAL_BASE', 2)
        
        # API-специфичные лимиты
        self.api_rate_limits = self._initialize_api_limits()
        
        # Логирование конфигурации
        self._log_configuration()
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """
        Получение boolean значения из переменной окружения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            
        Returns:
            Boolean значение
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """
        Получение целочисленного значения из переменной окружения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            
        Returns:
            Целочисленное значение
        """
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid integer value for {key}, using default: {default}"
            )
            return default
    
    def _initialize_api_limits(self) -> Dict[str, Dict[str, Any]]:
        """
        Инициализация API-специфичных лимитов
        
        Returns:
            Словарь с лимитами для каждого API
        """
        return {
            # Blockchain explorers
            'etherscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Ethereum blockchain explorer'
            },
            'bscscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'BSC blockchain explorer'
            },
            'polygonscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Polygon blockchain explorer'
            },
            'arbiscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Arbitrum blockchain explorer'
            },
            'basescan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Base blockchain explorer'
            },
            'optimistic_etherscan': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Optimism blockchain explorer'
            },
            'snowtrace': {
                'calls_per_second': 5,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Avalanche blockchain explorer'
            },
            'tronscan': {
                'calls_per_second': 3,
                'calls_per_day': 50000,
                'burst': 3,
                'description': 'Tron blockchain explorer'
            },
            
            # Crypto price APIs
            'coingecko_free': {
                'calls_per_minute': 10,
                'calls_per_month': 10000,
                'burst': 3,
                'description': 'CoinGecko free tier'
            },
            'coingecko_pro': {
                'calls_per_minute': 500,
                'calls_per_month': 500000,
                'burst': 10,
                'description': 'CoinGecko pro tier'
            },
            'coinmarketcap': {
                'calls_per_minute': 30,
                'calls_per_day': 10000,
                'burst': 5,
                'description': 'CoinMarketCap API'
            },
            
            # AI APIs
            'openai': {
                'calls_per_minute': 60,
                'tokens_per_minute': 90000,
                'burst': 10,
                'description': 'OpenAI GPT API'
            },
            'anthropic': {
                'calls_per_minute': 50,
                'tokens_per_minute': 100000,
                'burst': 5,
                'description': 'Anthropic Claude API'
            },
            'gemini': {
                'calls_per_minute': 60,
                'tokens_per_minute': 32000,
                'burst': 10,
                'description': 'Google Gemini API'
            },
            
            # Messaging APIs
            'telegram': {
                'calls_per_second': 30,
                'messages_per_minute': 20,
                'messages_per_chat_per_second': 1,
                'burst': 1,
                'description': 'Telegram Bot API'
            },
            
            # Blockchain RPC nodes
            'ethereum_public': {
                'calls_per_second': 1,
                'calls_per_minute': 10,
                'burst': 2,
                'description': 'Public Ethereum RPC'
            },
            'ethereum_alchemy': {
                'calls_per_second': 25,
                'calls_per_day': 300000,
                'burst': 10,
                'description': 'Alchemy Ethereum RPC'
            },
            'solana_public': {
                'calls_per_second': 1,
                'calls_per_minute': 40,
                'burst': 2,
                'description': 'Public Solana RPC'
            },
            'solana_helius': {
                'calls_per_second': 10,
                'calls_per_day': 100000,
                'burst': 5,
                'description': 'Helius Solana RPC'
            },
            'bsc_public': {
                'calls_per_second': 2,
                'calls_per_minute': 50,
                'burst': 3,
                'description': 'Public BSC RPC'
            },
            'polygon_public': {
                'calls_per_second': 2,
                'calls_per_minute': 50,
                'burst': 3,
                'description': 'Public Polygon RPC'
            }
        }
    
    def _log_configuration(self) -> None:
        """Логирование загруженной конфигурации"""
        if self.enabled:
            logger.info(
                f"✅ Rate limiting enabled: "
                f"{self.max_requests_per_minute} req/min, "
                f"{self.max_api_calls_per_second} calls/sec, "
                f"burst: {self.burst_size}"
            )
        else:
            logger.warning("⚠️ Rate limiting DISABLED")
        
        if self.retry_enabled:
            logger.info(
                f"✅ Retry enabled: max {self.retry_max_attempts} attempts, "
                f"delay: {self.retry_initial_delay}-{self.retry_max_delay}s"
            )
        else:
            logger.info("ℹ️ Retry disabled")
        
        logger.debug(f"Loaded API limits for {len(self.api_rate_limits)} services")
    
    def get_api_limits(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение лимитов для конкретного API
        
        Args:
            api_name: Название API (например, 'etherscan', 'openai')
            
        Returns:
            Словарь с лимитами или None если API не найден
        """
        limits = self.api_rate_limits.get(api_name)
        
        if limits is None:
            logger.debug(f"No specific limits found for API: {api_name}")
        
        return limits
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Расчет задержки для retry с экспоненциальным backoff
        
        Args:
            attempt: Номер попытки (0-based)
            
        Returns:
            Задержка в секундах
        """
        if not self.retry_enabled:
            return 0.0
        
        # Экспоненциальный backoff
        delay = self.retry_initial_delay * (
            self.retry_exponential_base ** attempt
        )
        
        # Ограничиваем максимальной задержкой
        return float(min(delay, self.retry_max_delay))
    
    def should_retry(self, attempt: int) -> bool:
        """
        Проверка необходимости повтора запроса
        
        Args:
            attempt: Номер попытки (1-based: 1, 2, 3, ...)
            
        Returns:
            True если нужен повтор
        """
        if not self.retry_enabled:
            return False
        
        return attempt <= self.retry_max_attempts
    
    def get_burst_allowance(self, api_name: Optional[str] = None) -> int:
        """
        Получение burst allowance для API
        
        Args:
            api_name: Название API (опционально)
            
        Returns:
            Burst allowance (количество запросов в burst)
        """
        if api_name and api_name in self.api_rate_limits:
            return self.api_rate_limits[api_name].get('burst', self.burst_size)
        
        return self.burst_size
    
    def get_calls_per_second(self, api_name: Optional[str] = None) -> float:
        """
        Получение лимита вызовов в секунду для API
        
        Args:
            api_name: Название API (опционально)
            
        Returns:
            Количество вызовов в секунду
        """
        if api_name and api_name in self.api_rate_limits:
            limits = self.api_rate_limits[api_name]
            
            # Проверяем различные варианты лимитов
            if 'calls_per_second' in limits:
                return float(limits['calls_per_second'])
            elif 'calls_per_minute' in limits:
                return float(limits['calls_per_minute']) / 60.0
            elif 'calls_per_day' in limits:
                return float(limits['calls_per_day']) / 86400.0
        
        return float(self.max_api_calls_per_second)
    
    def get_api_description(self, api_name: str) -> str:
        """
        Получение описания API
        
        Args:
            api_name: Название API
            
        Returns:
            Описание API или пустая строка
        """
        limits = self.get_api_limits(api_name)
        
        if limits and 'description' in limits:
            return limits['description']
        
        return ''
    
    def list_configured_apis(self) -> list:
        """
        Получение списка сконфигурированных API
        
        Returns:
            Список названий API
        """
        return list(self.api_rate_limits.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Словарь с полной конфигурацией
        """
        return {
            'enabled': self.enabled,
            'global': {
                'max_requests_per_minute': self.max_requests_per_minute,
                'max_calls_per_second': self.max_api_calls_per_second,
                'burst': self.burst_size
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
    
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если конфигурация валидна
            
        Raises:
            ValueError: При невалидной конфигурации
        """
        # Проверка глобальных лимитов
        if self.max_requests_per_minute < 1:
            raise ValueError("max_requests_per_minute must be >= 1")
        
        if self.max_api_calls_per_second < 1:
            raise ValueError("max_api_calls_per_second must be >= 1")
        
        if self.burst_size < 1:
            raise ValueError("burst_size must be >= 1")
        
        # Проверка retry настроек
        if self.retry_enabled:
            if self.retry_max_attempts < 1:
                raise ValueError("retry_max_attempts must be >= 1")
            
            if self.retry_initial_delay < 0:
                raise ValueError("retry_initial_delay must be >= 0")
            
            if self.retry_max_delay < self.retry_initial_delay:
                raise ValueError("retry_max_delay must be >= retry_initial_delay")
            
            if self.retry_exponential_base < 1:
                raise ValueError("retry_exponential_base must be >= 1")
        
        return True
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        return (
            f"RateLimitingConfig("
            f"enabled={self.enabled}, "
            f"max_rpm={self.max_requests_per_minute}, "
            f"max_cps={self.max_api_calls_per_second}, "
            f"burst={self.burst_size}, "
            f"apis={len(self.api_rate_limits)}"
            f")"
        )