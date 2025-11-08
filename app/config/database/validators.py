"""
Database Configuration Validators
Валидаторы и декораторы для проверки данных
"""

import logging
from typing import Any, Callable, TypeVar, Optional
from functools import wraps
from enum import Enum

from .exceptions import ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def validate_positive(
    field_name: str, 
    allow_zero: bool = False,
    max_value: Optional[int] = None
) -> Callable:
    """
    Декоратор валидации положительных значений
    
    Args:
        field_name: Имя поля для сообщений об ошибках
        allow_zero: Разрешить нулевое значение
        max_value: Максимальное допустимое значение
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            min_value = 0 if allow_zero else 1
            
            if value < min_value:
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be >= {min_value}"
                )
            
            if max_value is not None and value > max_value:
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be <= {max_value}"
                )
            
            return func(self, value)
        return wrapper
    return decorator


def validate_range(
    field_name: str, 
    min_val: Any, 
    max_val: Any,
    inclusive: bool = True
) -> Callable:
    """
    Декоратор валидации диапазона значений
    
    Args:
        field_name: Имя поля для сообщений об ошибках
        min_val: Минимальное значение
        max_val: Максимальное значение
        inclusive: Включать границы диапазона
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            if inclusive:
                in_range = min_val <= value <= max_val
            else:
                in_range = min_val < value < max_val
            
            if not in_range:
                bracket = "[]" if inclusive else "()"
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be in range {bracket[0]}{min_val}, {max_val}{bracket[1]}"
                )
            
            return func(self, value)
        return wrapper
    return decorator


def validate_enum(field_name: str, enum_class: type[Enum]) -> Callable:
    """
    Декоратор валидации enum значений
    
    Args:
        field_name: Имя поля для сообщений об ошибках
        enum_class: Класс Enum для валидации
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            if isinstance(value, str):
                try:
                    value = enum_class(value.upper())
                except ValueError:
                    valid_values = [e.value for e in enum_class]
                    raise ValidationError(
                        field=field_name,
                        value=value,
                        reason=f"must be one of {valid_values}"
                    )
            elif not isinstance(value, enum_class):
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be of type {enum_class.__name__}"
                )
            
            return func(self, value)
        return wrapper
    return decorator


def validate_type(field_name: str, expected_type: type) -> Callable:
    """
    Декоратор валидации типа значения
    
    Args:
        field_name: Имя поля для сообщений об ошибках
        expected_type: Ожидаемый тип
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            if not isinstance(value, expected_type):
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be of type {expected_type.__name__}, "
                           f"got {type(value).__name__}"
                )
            
            return func(self, value)
        return wrapper
    return decorator


def validate_in_list(field_name: str, valid_values: list) -> Callable:
    """
    Декоратор валидации значения из списка
    
    Args:
        field_name: Имя поля для сообщений об ошибках
        valid_values: Список допустимых значений
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            if value not in valid_values:
                raise ValidationError(
                    field=field_name,
                    value=value,
                    reason=f"must be one of {valid_values}"
                )
            
            return func(self, value)
        return wrapper
    return decorator


def warn_if_extreme(
    field_name: str,
    threshold: Any,
    condition: str = 'greater',
    message: Optional[str] = None
) -> Callable:
    """
    Декоратор для предупреждений о экстремальных значениях
    
    Args:
        field_name: Имя поля для сообщений
        threshold: Пороговое значение
        condition: Условие ('greater', 'less', 'equal')
        message: Кастомное сообщение
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, value: Any) -> Any:
            should_warn = False
            
            if condition == 'greater' and value > threshold:
                should_warn = True
            elif condition == 'less' and value < threshold:
                should_warn = True
            elif condition == 'equal' and value == threshold:
                should_warn = True
            
            if should_warn:
                warning_msg = message or (
                    f"{field_name}={value} is {condition} than threshold {threshold}. "
                    f"This may cause issues."
                )
                logger.warning(warning_msg)
            
            return func(self, value)
        return wrapper
    return decorator


class ValidatedProperty:
    """
    Дескриптор для валидированных свойств с поддержкой цепочки валидаторов
    """
    
    def __init__(
        self,
        validators: Optional[list[Callable]] = None,
        default: Any = None,
        doc: Optional[str] = None
    ):
        """
        Args:
            validators: Список функций-валидаторов
            default: Значение по умолчанию
            doc: Документация свойства
        """
        self.validators = validators or []
        self.default = default
        self.__doc__ = doc
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = f'_{name}'
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.name, self.default)
    
    def __set__(self, obj, value):
        # Применение всех валидаторов
        for validator in self.validators:
            value = validator(obj, value)
        
        setattr(obj, self.name, value)


def create_validator_chain(*validators: Callable) -> Callable:
    """
    Создание цепочки валидаторов
    
    Args:
        *validators: Функции-валидаторы
        
    Returns:
        Композитная функция-валидатор
    """
    def composite_validator(obj, value):
        for validator in validators:
            value = validator(obj, value)
        return value
    
    return composite_validator