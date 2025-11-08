# core/components/__init__.py
"""
Component Loading and Management System v2.0
Модульная система управления компонентами приложения
"""

from .manager import ComponentManager
from .loaders import ComponentLoader
from .errors import (
    ComponentError,
    ComponentLoadError,
    ComponentInitError,
    ComponentStopError
)

__all__ = [
    'ComponentManager',
    'ComponentLoader',
    'ComponentError',
    'ComponentLoadError',
    'ComponentInitError',
    'ComponentStopError'
]

__version__ = '2.0.0'