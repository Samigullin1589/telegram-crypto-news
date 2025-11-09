# app/config/database/protocols/base/hashable.py
"""
Hashing Protocols
Протоколы для хеширования объектов
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfigHashable(Protocol):
    """Протокол для объектов с хешированием конфигурации"""
    
    def compute_hash(self) -> str:
        """
        Вычисление хеша объекта
        
        Returns:
            Строка с хешем (обычно SHA256)
        """
        ...
    
    def get_fingerprint(self) -> str:
        """
        Получение короткого отпечатка объекта
        
        Returns:
            Короткая строка-идентификатор (8-16 символов)
        """
        ...