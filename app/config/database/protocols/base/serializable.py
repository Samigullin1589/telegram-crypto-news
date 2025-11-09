# app/config/database/protocols/base/serializable.py
"""
Serialization Protocols
Протоколы для сериализации объектов
"""

from typing import Protocol, Dict, Any, TypeVar, runtime_checkable


T = TypeVar('T')


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
    
    def to_json(self) -> str:
        """
        Конвертация объекта в JSON строку
        
        Returns:
            JSON представление объекта
        """
        ...
    
    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        """
        Создание объекта из словаря
        
        Args:
            data: Словарь с данными
            
        Returns:
            Экземпляр объекта
        """
        ...
    
    @classmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """
        Создание объекта из JSON строки
        
        Args:
            json_str: JSON строка
            
        Returns:
            Экземпляр объекта
        """
        ...