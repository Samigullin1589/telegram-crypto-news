# app/whales/monitor/evm_components/circuit_breaker.py
"""
Circuit Breaker Pattern
Защита от постоянных запросов к упавшим сервисам
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Состояния circuit breaker"""
    CLOSED = "closed"      # Все работает
    OPEN = "open"          # Сервис недоступен
    HALF_OPEN = "half_open"  # Проверка восстановления


class CircuitBreaker:
    """
    Circuit Breaker для защиты от постоянных запросов к недоступным сервисам
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Args:
            name: Название сервиса
            failure_threshold: Количество ошибок для открытия circuit
            recovery_timeout: Время в секундах до попытки восстановления
            success_threshold: Количество успехов для закрытия circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.total_requests = 0
        self.total_failures = 0
    
    def can_execute(self) -> bool:
        """
        Проверка возможности выполнения запроса
        
        Returns:
            True если можно выполнять запрос
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"🔄 [CIRCUIT] {self.name}: OPEN -> HALF_OPEN (попытка восстановления)")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self) -> None:
        """Регистрация успешного запроса"""
        self.total_requests += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                self._close_circuit()
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Регистрация неудачного запроса"""
        self.total_requests += 1
        self.total_failures += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
            return
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()
    
    def _open_circuit(self) -> None:
        """Открытие circuit (блокировка запросов)"""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        logger.warning(
            f"⚠️ [CIRCUIT] {self.name}: Circuit ОТКРЫТ "
            f"(слишком много ошибок, блокировка на {self.recovery_timeout.seconds}s)"
        )
    
    def _close_circuit(self) -> None:
        """Закрытие circuit (разрешение запросов)"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"✅ [CIRCUIT] {self.name}: Circuit ЗАКРЫТ (сервис восстановлен)")
    
    def _should_attempt_reset(self) -> bool:
        """Проверка необходимости попытки восстановления"""
        if not self.last_failure_time:
            return True
        
        return datetime.utcnow() - self.last_failure_time >= self.recovery_timeout
    
    def get_stats(self) -> Dict[str, any]:
        """Статистика работы circuit breaker"""
        failure_rate = (
            (self.total_failures / self.total_requests * 100)
            if self.total_requests > 0 else 0.0
        )
        
        return {
            "state": self.state.value,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "failure_rate": round(failure_rate, 2),
            "current_failures": self.failure_count
        }