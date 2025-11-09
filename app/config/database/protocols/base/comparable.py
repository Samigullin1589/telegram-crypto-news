# app/config/database/protocols/base/comparable.py
"""
Comparison Protocols
Протоколы для сравнения объектов
"""

from typing import Protocol, Dict, Any, Tuple, runtime_checkable


@runtime_checkable
class Comparable(Protocol):
    """Протокол для сравнимых объектов"""
    
    def equals(self, other: Any) -> bool:
        """
        Сравнение с другим объектом
        
        Args:
            other: Объект для сравнения
            
        Returns:
            True если объекты равны
        """
        ...
    
    def diff(self, other: Any) -> Dict[str, Tuple[Any, Any]]:
        """
        Получение различий с другим объектом
        
        Args:
            other: Объект для сравнения
            
        Returns:
            Словарь {поле: (значение_self, значение_other)}
        """
        ...