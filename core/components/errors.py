# core/components/errors.py
"""
Custom Exceptions for Component System
Кастомные исключения для системы компонентов
"""


class ComponentError(Exception):
    """Базовое исключение для компонентов"""
    pass


class ComponentLoadError(ComponentError):
    """Ошибка загрузки компонента"""
    
    def __init__(self, component_name: str, reason: str):
        self.component_name = component_name
        self.reason = reason
        super().__init__(f"Failed to load {component_name}: {reason}")


class ComponentInitError(ComponentError):
    """Ошибка инициализации компонента"""
    
    def __init__(self, component_name: str, reason: str):
        self.component_name = component_name
        self.reason = reason
        super().__init__(f"Failed to initialize {component_name}: {reason}")


class ComponentStopError(ComponentError):
    """Ошибка остановки компонента"""
    
    def __init__(self, component_name: str, reason: str):
        self.component_name = component_name
        self.reason = reason
        super().__init__(f"Failed to stop {component_name}: {reason}")


class ComponentConfigError(ComponentError):
    """Ошибка конфигурации компонента"""
    
    def __init__(self, component_name: str, reason: str):
        self.component_name = component_name
        self.reason = reason
        super().__init__(f"Configuration error for {component_name}: {reason}")