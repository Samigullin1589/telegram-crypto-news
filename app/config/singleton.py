# app/config/singleton.py
"""
Singleton Metaclass
Реализация паттерна Singleton через метакласс
"""

import logging
from threading import Lock
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """
    Потокобезопасная реализация паттерна Singleton через метакласс
    
    Гарантирует что в системе существует только один экземпляр класса.
    Потокобезопасна благодаря использованию Lock.
    """
    
    _instances: Dict[type, Any] = {}
    _lock: Lock = Lock()
    
    def __call__(cls, *args, **kwargs):
        """
        Создание или возврат существующего экземпляра
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Единственный экземпляр класса
        """
        if cls not in cls._instances:
            with cls._lock:
                # Двойная проверка для потокобезопасности
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    logger.debug(f"Создан новый экземпляр {cls.__name__} (Singleton)")
        
        return cls._instances[cls]