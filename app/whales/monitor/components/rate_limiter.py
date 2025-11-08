# app/whales/monitor/components/rate_limiter.py
"""
Rate Limiter
Контроль частоты запросов к внешним API
"""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter с sliding window"""
    
    def __init__(self, requests_per_second: int = 10):
        """
        Args:
            requests_per_second: Максимальное количество запросов в секунду
        """
        self.requests_per_second = requests_per_second
        self.window_size = timedelta(seconds=1)
        self.request_times = deque()
        self.lock = asyncio.Lock()
        
        logger.debug(f"🔧 [RATE] Инициализирован: {requests_per_second} req/s")
    
    async def acquire(self):
        """
        Ожидание разрешения на выполнение запроса
        Блокирует выполнение если превышен лимит
        """
        async with self.lock:
            now = datetime.utcnow()
            
            # Очистка старых записей за пределами окна
            while self.request_times and (now - self.request_times[0]) > self.window_size:
                self.request_times.popleft()
            
            # Проверка лимита
            if len(self.request_times) >= self.requests_per_second:
                # Расчёт времени ожидания
                oldest_request = self.request_times[0]
                wait_time = (oldest_request + self.window_size - now).total_seconds()
                
                if wait_time > 0:
                    logger.debug(f"⏱️ [RATE] Ожидание {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
                    # Рекурсивный вызов после ожидания
                    await self.acquire()
                    return
            
            # Регистрация нового запроса
            self.request_times.append(now)
    
    def get_stats(self) -> dict:
        """
        Получение статистики rate limiter
        
        Returns:
            Dict со статистикой
        """
        now = datetime.utcnow()
        
        # Подсчёт активных запросов в текущем окне
        active_requests = sum(
            1 for req_time in self.request_times
            if (now - req_time) <= self.window_size
        )
        
        return {
            'requests_per_second': self.requests_per_second,
            'active_requests_in_window': active_requests,
            'utilization_percent': round(
                (active_requests / self.requests_per_second) * 100, 2
            )
        }