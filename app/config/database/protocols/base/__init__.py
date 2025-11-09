# app/config/database/protocols/base/__init__.py
"""
Base Protocols Package
Базовые протоколы с максимальным разделением ответственности
"""

from .validatable import Validatable
from .serializable import Serializable
from .updatable import Updatable
from .configurable import Configurable
from .cloneable import Cloneable
from .comparable import Comparable
from .hashable import ConfigHashable

# Алиас для обратной совместимости (если где-то используется Hashable)
Hashable = ConfigHashable

__all__ = [
    'Validatable',
    'Serializable',
    'Updatable',
    'Configurable',
    'Cloneable',
    'Comparable',
    'ConfigHashable',
    'Hashable',  # Экспортируем оба имени
]