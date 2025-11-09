# app/config/database/protocols/base/updatable.py
"""
Update Protocols
Протоколы для обновления объектов
"""

from typing import Protocol, Dict, Any, TypeVar, runtime_checkable


T = TypeVar('T')


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
    
    def merge(self: T, other: T) -> T:
        """
        Слияние с другим объектом того же типа
        
        Args:
            other: Другой объект для слияния
            
        Returns:
            Новый объект с объединенными данными
        """
        ...
    
    def apply_defaults(self) -> None:
        """Применение значений по умолчанию для пустых полей"""
        ...