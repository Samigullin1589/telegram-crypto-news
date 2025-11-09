# app/config/database/protocols/base/cloneable.py
"""
Clone Protocols
Протоколы для клонирования объектов
"""

from typing import Protocol, TypeVar, runtime_checkable


T = TypeVar('T')


@runtime_checkable
class Cloneable(Protocol[T]):
    """Протокол для клонируемых объектов"""
    
    def clone(self: T) -> T:
        """
        Создание глубокой копии объекта
        
        Returns:
            Новый экземпляр с теми же данными
        """
        ...
    
    def shallow_copy(self: T) -> T:
        """
        Создание поверхностной копии объекта
        
        Returns:
            Новый экземпляр с ссылками на те же вложенные объекты
        """
        ...