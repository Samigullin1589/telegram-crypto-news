# core/components.py
"""
Component Loading and Management System
Backward compatibility wrapper
"""

import warnings
from core.components.manager import ComponentManager
from core.components.loaders import ComponentLoader

# Предупреждение о deprecated импорте
warnings.warn(
    "Importing from 'core.components' is deprecated. "
    "Use 'from core.components import ComponentManager' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['ComponentManager', 'ComponentLoader']