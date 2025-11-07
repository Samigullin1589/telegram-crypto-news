# app/whales/monitor/circuit_breaker.py
"""
Circuit Breaker for API Protection
"""

import time


class CircuitBreaker:
    """
    Circuit Breaker для защиты от перегрузки API
    
    States:
    - CLOSED: Нормальная работа
    - OPEN: API перегружен, все запросы блокируются
    - HALF_OPEN: Тестирование восстановления
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def record_success(self):
        """Записывает успешный запрос"""
        self.failures = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Записывает неудачный запрос"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            print(f"⚠️ [CIRCUIT] Circuit breaker OPEN ({self.failures} failures)")
    
    def can_execute(self) -> bool:
        """Проверяет можно ли выполнять запросы"""
        
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "HALF_OPEN"
                print(f"🔄 [CIRCUIT] Circuit breaker HALF_OPEN (testing)")
                return True
            return False
        
        return True