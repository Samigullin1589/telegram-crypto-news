# app/config/database/protocols/timing.py
"""
Timing Protocols
Протоколы для временных операций
"""

from typing import Protocol, Dict, Any, runtime_checkable


@runtime_checkable
class TimeBasedCheck(Protocol):
    """Протокол для проверок на основе времени"""
    
    def should_execute(self, last_time: float, current_time: float) -> bool:
        """
        Проверка необходимости выполнения операции
        
        Args:
            last_time: Время последнего выполнения (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если операцию нужно выполнить
        """
        ...
    
    def get_next_execution_time(self, last_time: float) -> float:
        """
        Расчет времени следующего выполнения
        
        Args:
            last_time: Время последнего выполнения
            
        Returns:
            Timestamp следующего выполнения
        """
        ...


@runtime_checkable
class ScheduledOperation(Protocol):
    """Протокол для запланированных операций"""
    
    def schedule(self, interval: float, immediate: bool = False) -> None:
        """
        Планирование операции
        
        Args:
            interval: Интервал выполнения в секундах
            immediate: Выполнить немедленно
        """
        ...
    
    def unschedule(self) -> None:
        """Отмена планирования"""
        ...
    
    def is_scheduled(self) -> bool:
        """
        Проверка планирования
        
        Returns:
            True если операция запланирована
        """
        ...
    
    def get_schedule_info(self) -> Dict[str, Any]:
        """
        Информация о расписании
        
        Returns:
            Словарь с информацией о расписании
        """
        ...


@runtime_checkable
class ThrottledOperation(Protocol):
    """Протокол для операций с троттлингом"""
    
    def can_execute(self) -> bool:
        """
        Проверка возможности выполнения
        
        Returns:
            True если можно выполнить
        """
        ...
    
    def record_execution(self) -> None:
        """Регистрация выполнения операции"""
        ...
    
    def get_time_until_available(self) -> float:
        """
        Время до доступности
        
        Returns:
            Секунды до следующего доступного выполнения
        """
        ...


@runtime_checkable
class RateLimited(Protocol):
    """Протокол для ограничения частоты"""
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Попытка получить токены
        
        Args:
            tokens: Количество токенов
            
        Returns:
            True если токены получены
        """
        ...
    
    async def acquire_async(self, tokens: int = 1) -> None:
        """
        Асинхронное получение токенов (ожидание при необходимости)
        
        Args:
            tokens: Количество токенов
        """
        ...
    
    def get_available_tokens(self) -> int:
        """
        Получение доступных токенов
        
        Returns:
            Количество доступных токенов
        """
        ...
    
    def reset(self) -> None:
        """Сброс лимита"""
        ...


@runtime_checkable
class TimedExecution(Protocol):
    """Протокол для измерения времени выполнения"""
    
    def start_timer(self, name: str) -> None:
        """
        Запуск таймера
        
        Args:
            name: Имя таймера
        """
        ...
    
    def stop_timer(self, name: str) -> float:
        """
        Остановка таймера
        
        Args:
            name: Имя таймера
            
        Returns:
            Время выполнения в секундах
        """
        ...
    
    def get_execution_time(self, name: str) -> float:
        """
        Получение времени выполнения
        
        Args:
            name: Имя таймера
            
        Returns:
            Время в секундах
        """
        ...
    
    def get_statistics(self, name: str) -> Dict[str, Any]:
        """
        Статистика выполнения
        
        Args:
            name: Имя таймера
            
        Returns:
            Словарь со статистикой (avg, min, max, count)
        """
        ...