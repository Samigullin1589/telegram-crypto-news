# app/config/database/protocols/monitoring.py
"""
Monitoring Protocols
Протоколы для мониторинга и метрик
"""

from typing import Protocol, Dict, Any, List, Callable, runtime_checkable


@runtime_checkable
class Monitorable(Protocol):
    """Протокол для мониторинга компонентов"""
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса
        
        Returns:
            Словарь с информацией о статусе
        """
        ...
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики работы
        
        Returns:
            Словарь со статистическими данными
        """
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """Протокол для проверки здоровья компонента"""
    
    async def health_check(self) -> bool:
        """
        Проверка здоровья компонента
        
        Returns:
            True если компонент здоров
        """
        ...
    
    def get_health_status(self) -> str:
        """
        Получение статуса здоровья
        
        Returns:
            Статус (healthy, degraded, unhealthy, unknown)
        """
        ...
    
    def get_health_details(self) -> Dict[str, Any]:
        """
        Подробная информация о здоровье
        
        Returns:
            Словарь с деталями проверки
        """
        ...


@runtime_checkable
class MetricsCollectable(Protocol):
    """Протокол для сбора метрик"""
    
    def collect_metrics(self) -> Dict[str, float]:
        """
        Сбор текущих метрик
        
        Returns:
            Словарь {метрика: значение}
        """
        ...
    
    def get_metric(self, name: str) -> float:
        """
        Получение конкретной метрики
        
        Args:
            name: Название метрики
            
        Returns:
            Значение метрики
            
        Raises:
            KeyError: Если метрика не найдена
        """
        ...
    
    def reset_metrics(self) -> None:
        """Сброс всех метрик"""
        ...
    
    def get_metrics_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Метаданные метрик
        
        Returns:
            Словарь {метрика: {type, unit, description}}
        """
        ...


@runtime_checkable
class Alertable(Protocol):
    """Протокол для системы алертов"""
    
    def get_alerts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Получение списка алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Список алертов
        """
        ...
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Подтверждение алерта
        
        Args:
            alert_id: ID алерта
            
        Returns:
            True если алерт подтвержден
        """
        ...
    
    def clear_alert(self, alert_id: str) -> bool:
        """
        Очистка алерта
        
        Args:
            alert_id: ID алерта
            
        Returns:
            True если алерт очищен
        """
        ...


@runtime_checkable
class Loggable(Protocol):
    """Протокол для логирования"""
    
    def log_event(self, 
                  level: str, 
                  message: str, 
                  **kwargs: Any) -> None:
        """
        Логирование события
        
        Args:
            level: Уровень (debug, info, warning, error, critical)
            message: Сообщение
            **kwargs: Дополнительные данные
        """
        ...
    
    def get_log_level(self) -> str:
        """
        Получение текущего уровня логирования
        
        Returns:
            Уровень логирования
        """
        ...
    
    def set_log_level(self, level: str) -> None:
        """
        Установка уровня логирования
        
        Args:
            level: Новый уровень
        """
        ...


@runtime_checkable
class Traceable(Protocol):
    """Протокол для трассировки"""
    
    def start_trace(self, operation: str) -> str:
        """
        Начало трассировки операции
        
        Args:
            operation: Название операции
            
        Returns:
            ID трассировки
        """
        ...
    
    def end_trace(self, trace_id: str, success: bool = True) -> None:
        """
        Завершение трассировки
        
        Args:
            trace_id: ID трассировки
            success: Успешность операции
        """
        ...
    
    def get_trace_info(self, trace_id: str) -> Dict[str, Any]:
        """
        Получение информации о трассировке
        
        Args:
            trace_id: ID трассировки
            
        Returns:
            Информация о трассировке
        """
        ...