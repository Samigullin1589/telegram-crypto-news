"""
SOLANA RATE LIMITER
Дополнительный слой rate limiting для критичных операций
"""

import asyncio
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token Bucket алгоритм для rate limiting
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Максимум токенов
            refill_rate: Токенов в секунду
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Попытка взять токены
        
        Returns:
            True если токены получены
        """
        
        async with self.lock:
            # Refill токенов
            now = time.time()
            elapsed = now - self.last_refill
            refill_amount = elapsed * self.refill_rate
            
            self.tokens = min(self.capacity, self.tokens + refill_amount)
            self.last_refill = now
            
            # Проверяем доступность
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: float = 60.0):
        """
        Ждать пока токены станут доступны
        
        Args:
            tokens: Количество токенов
            timeout: Максимальное время ожидания
        """
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.acquire(tokens):
                return True
            
            # Рассчитываем время ожидания
            async with self.lock:
                if self.tokens < tokens:
                    needed = tokens - self.tokens
                    wait_time = needed / self.refill_rate
                    wait_time = min(wait_time, 1.0)
                else:
                    wait_time = 0.1
            
            await asyncio.sleep(wait_time)
        
        raise TimeoutError(f"Не удалось получить {tokens} токенов за {timeout}s")


class SlidingWindowRateLimiter:
    """
    Sliding Window алгоритм rate limiting
    """
    
    def __init__(self, max_requests: int, window_seconds: float):
        """
        Args:
            max_requests: Максимум запросов
            window_seconds: Размер окна в секундах
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = asyncio.Lock()
    
    async def can_proceed(self) -> bool:
        """
        Проверка, можно ли сделать запрос
        """
        
        async with self.lock:
            now = time.time()
            
            # Удаляем старые запросы
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Проверяем лимит
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    async def wait_for_slot(self, timeout: float = 60.0):
        """
        Ждать пока появится слот
        """
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.can_proceed():
                return True
            
            # Рассчитываем время ожидания
            async with self.lock:
                if self.requests:
                    oldest_request = self.requests[0]
                    wait_time = (oldest_request + self.window_seconds) - time.time()
                    wait_time = max(0.1, min(wait_time, 1.0))
                else:
                    wait_time = 0.1
            
            await asyncio.sleep(wait_time)
        
        raise TimeoutError(f"Не удалось получить слот за {timeout}s")


class AdaptiveRateLimiter:
    """
    Адаптивный rate limiter который подстраивается под 429 ошибки
    """
    
    def __init__(self, initial_rate: int = 10, min_rate: int = 1, max_rate: int = 50):
        """
        Args:
            initial_rate: Начальная скорость (req/s)
            min_rate: Минимальная скорость
            max_rate: Максимальная скорость
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        
        self.token_bucket = TokenBucket(capacity=initial_rate * 2, refill_rate=initial_rate)
        
        self.success_count = 0
        self.error_429_count = 0
        self.last_adjustment = time.time()
        
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Получить разрешение на запрос"""
        await self.token_bucket.wait_for_tokens(1)
    
    async def record_success(self):
        """Записать успешный запрос"""
        
        async with self.lock:
            self.success_count += 1
            
            # Увеличиваем rate после серии успехов
            if self.success_count >= 20 and time.time() - self.last_adjustment > 30:
                if self.current_rate < self.max_rate:
                    old_rate = self.current_rate
                    self.current_rate = min(self.max_rate, self.current_rate * 1.2)
                    
                    # Обновляем token bucket
                    self.token_bucket = TokenBucket(
                        capacity=int(self.current_rate * 2),
                        refill_rate=self.current_rate
                    )
                    
                    logger.info(f"📈 [RATE LIMITER] Увеличен rate: {old_rate:.1f} → {self.current_rate:.1f} req/s")
                    
                    self.success_count = 0
                    self.last_adjustment = time.time()
    
    async def record_429_error(self):
        """Записать 429 ошибку"""
        
        async with self.lock:
            self.error_429_count += 1
            
            # Немедленно уменьшаем rate
            old_rate = self.current_rate
            self.current_rate = max(self.min_rate, self.current_rate * 0.5)
            
            # Обновляем token bucket
            self.token_bucket = TokenBucket(
                capacity=int(self.current_rate * 2),
                refill_rate=self.current_rate
            )
            
            logger.warning(f"📉 [RATE LIMITER] Уменьшен rate после 429: {old_rate:.1f} → {self.current_rate:.1f} req/s")
            
            self.success_count = 0
            self.last_adjustment = time.time()
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            "current_rate": self.current_rate,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate,
            "success_count": self.success_count,
            "error_429_count": self.error_429_count
        }


# Глобальный adaptive rate limiter
_global_rate_limiter: Optional[AdaptiveRateLimiter] = None


def get_rate_limiter() -> AdaptiveRateLimiter:
    """Получить глобальный rate limiter"""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = AdaptiveRateLimiter(
            initial_rate=10,
            min_rate=1,
            max_rate=50
        )
    
    return _global_rate_limiter


__all__ = [
    'TokenBucket',
    'SlidingWindowRateLimiter',
    'AdaptiveRateLimiter',
    'get_rate_limiter'
]