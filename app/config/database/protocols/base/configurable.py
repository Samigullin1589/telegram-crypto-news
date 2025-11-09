# app/config/database/protocols/base/configurable.py
"""
Configuration Protocols
Протоколы для конфигурируемых объектов
"""

from typing import Protocol, Dict, Any, runtime_checkable

from .validatable import Validatable
from .serializable import Serializable
from .updatable import Updatable


@runtime_checkable
class Configurable(Validatable, Serializable, Updatable, Protocol):
    """Полный протокол для конфигурационных объектов"""
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Получение схемы конфигурации
        
        Returns:
            Словарь со схемой (поля, типы, ограничения)
        """
        ...
    
    def get_config_version(self) -> str:
        """
        Версия схемы конфигурации
        
        Returns:
            Строка с версией (semver)
        """
        ...