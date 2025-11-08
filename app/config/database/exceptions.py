"""
Database Configuration Exceptions
Кастомные исключения для системы конфигурации БД
"""


class DatabaseConfigError(Exception):
    """Базовое исключение для всех ошибок конфигурации БД"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ValidationError(DatabaseConfigError):
    """Ошибка валидации конфигурации"""
    
    def __init__(self, field: str, value: any, reason: str):
        message = f"Validation failed for '{field}'"
        details = {
            'field': field,
            'value': value,
            'reason': reason
        }
        super().__init__(message, details)


class ConfigurationError(DatabaseConfigError):
    """Ошибка в конфигурации"""
    pass


class EnvironmentError(DatabaseConfigError):
    """Ошибка загрузки из переменных окружения"""
    pass


class ComponentError(DatabaseConfigError):
    """Ошибка в компоненте конфигурации"""
    pass