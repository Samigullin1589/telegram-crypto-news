"""
Database Configuration Protocols
Протоколы и интерфейсы для типизации
"""

from typing import Protocol, Dict, Any, runtime_checkable


@runtime_checkable
class Validatable(Protocol):
    """Протокол для объектов с валидацией"""
    
    def validate(self) -> bool:
        """
        Валидация объекта
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При ошибке валидации
        """
        ...


@runtime_checkable
class Serializable(Protocol):
    """Протокол для сериализуемых объектов"""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация объекта в словарь
        
        Returns:
            Словарь с данными объекта
        """
        ...


@runtime_checkable
class Updatable(Protocol):
    """Протокол для обновляемых объектов"""
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Обновление объекта из словаря
        
        Args:
            data: Словарь с новыми значениями
        """
        ...


@runtime_checkable
class Configurable(Validatable, Serializable, Updatable, Protocol):
    """Полный протокол для конфигурационных объектов"""
    pass


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