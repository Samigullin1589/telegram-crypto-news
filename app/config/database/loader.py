"""
Database Configuration Environment Loader
Загрузчик конфигурации из переменных окружения
"""

import os
import logging
from typing import Optional, TypeVar, Callable, Any
from enum import Enum

from .exceptions import EnvironmentError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EnvironmentConfigLoader:
    """
    Загрузчик конфигурации из переменных окружения
    
    Поддерживает:
    - Различные типы данных (bool, int, float, str, enum)
    - Значения по умолчанию
    - Валидацию и конвертацию типов
    - Логирование ошибок
    """
    
    def __init__(self, prefix: str = ''):
        """
        Args:
            prefix: Префикс для всех ключей (например 'DB_')
        """
        self.prefix = prefix
    
    def _get_key(self, key: str) -> str:
        """Получение полного ключа с префиксом"""
        return f"{self.prefix}{key}" if self.prefix else key
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Получение boolean значения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            
        Returns:
            Boolean значение
        """
        full_key = self._get_key(key)
        value = os.getenv(full_key, str(default)).lower()
        
        true_values = ('true', '1', 'yes', 'on', 'enabled')
        false_values = ('false', '0', 'no', 'off', 'disabled')
        
        if value in true_values:
            return True
        elif value in false_values:
            return False
        else:
            logger.warning(
                f"Invalid boolean value for {full_key}={value}, using default: {default}"
            )
            return default
    
    def get_int(self, key: str, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        """
        Получение integer значения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            min_value: Минимальное допустимое значение
            max_value: Максимальное допустимое значение
            
        Returns:
            Integer значение
        """
        full_key = self._get_key(key)
        value_str = os.getenv(full_key, str(default))
        
        try:
            value = int(value_str)
            
            if min_value is not None and value < min_value:
                logger.warning(
                    f"{full_key}={value} is less than min={min_value}, using min"
                )
                return min_value
            
            if max_value is not None and value > max_value:
                logger.warning(
                    f"{full_key}={value} is greater than max={max_value}, using max"
                )
                return max_value
            
            return value
            
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid integer value for {full_key}={value_str}, "
                f"using default: {default}. Error: {e}"
            )
            return default
    
    def get_float(self, key: str, default: float, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
        """
        Получение float значения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            min_value: Минимальное допустимое значение
            max_value: Максимальное допустимое значение
            
        Returns:
            Float значение
        """
        full_key = self._get_key(key)
        value_str = os.getenv(full_key, str(default))
        
        try:
            value = float(value_str)
            
            if min_value is not None and value < min_value:
                logger.warning(
                    f"{full_key}={value} is less than min={min_value}, using min"
                )
                return min_value
            
            if max_value is not None and value > max_value:
                logger.warning(
                    f"{full_key}={value} is greater than max={max_value}, using max"
                )
                return max_value
            
            return value
            
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid float value for {full_key}={value_str}, "
                f"using default: {default}. Error: {e}"
            )
            return default
    
    def get_str(self, key: str, default: str = '', allowed_values: Optional[list] = None) -> str:
        """
        Получение string значения
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            allowed_values: Список допустимых значений
            
        Returns:
            String значение
        """
        full_key = self._get_key(key)
        value = os.getenv(full_key, default)
        
        if allowed_values and value not in allowed_values:
            logger.warning(
                f"{full_key}={value} is not in allowed values {allowed_values}, "
                f"using default: {default}"
            )
            return default
        
        return value
    
    def get_enum(self, key: str, enum_class: type[Enum], default: Enum) -> Enum:
        """
        Получение enum значения
        
        Args:
            key: Ключ переменной окружения
            enum_class: Класс Enum
            default: Значение по умолчанию
            
        Returns:
            Enum значение
        """
        full_key = self._get_key(key)
        value = os.getenv(full_key, default.value).upper()
        
        try:
            return enum_class(value)
        except ValueError:
            valid_values = [e.value for e in enum_class]
            logger.warning(
                f"Invalid enum value for {full_key}={value}, "
                f"valid values: {valid_values}, using default: {default.value}"
            )
            return default
    
    def get_optional_enum(
        self, 
        key: str, 
        enum_class: type[Enum], 
        default: Optional[Enum] = None
    ) -> Optional[Enum]:
        """
        Получение опционального enum значения
        
        Args:
            key: Ключ переменной окружения
            enum_class: Класс Enum
            default: Значение по умолчанию (может быть None)
            
        Returns:
            Enum значение или None
        """
        full_key = self._get_key(key)
        value = os.getenv(full_key)
        
        if value is None:
            return default
        
        try:
            return enum_class(value.upper())
        except ValueError:
            valid_values = [e.value for e in enum_class]
            logger.warning(
                f"Invalid enum value for {full_key}={value}, "
                f"valid values: {valid_values}, using default: {default}"
            )
            return default
    
    def get_list(
        self, 
        key: str, 
        default: list = None, 
        separator: str = ',',
        converter: Optional[Callable[[str], Any]] = None
    ) -> list:
        """
        Получение списка значений
        
        Args:
            key: Ключ переменной окружения
            default: Значение по умолчанию
            separator: Разделитель элементов
            converter: Функция конвертации элементов
            
        Returns:
            Список значений
        """
        if default is None:
            default = []
        
        full_key = self._get_key(key)
        value = os.getenv(full_key)
        
        if not value:
            return default
        
        items = [item.strip() for item in value.split(separator)]
        
        if converter:
            try:
                return [converter(item) for item in items]
            except Exception as e:
                logger.warning(
                    f"Failed to convert list items for {full_key}, "
                    f"using default: {e}"
                )
                return default
        
        return items
    
    def require(self, key: str, error_message: Optional[str] = None) -> str:
        """
        Получение обязательной переменной окружения
        
        Args:
            key: Ключ переменной окружения
            error_message: Кастомное сообщение об ошибке
            
        Returns:
            Значение переменной
            
        Raises:
            EnvironmentError: Если переменная не установлена
        """
        full_key = self._get_key(key)
        value = os.getenv(full_key)
        
        if value is None:
            message = error_message or f"Required environment variable {full_key} is not set"
            raise EnvironmentError(message, {'key': full_key})
        
        return value
    
    def has(self, key: str) -> bool:
        """
        Проверка наличия переменной окружения
        
        Args:
            key: Ключ переменной окружения
            
        Returns:
            True если переменная установлена
        """
        full_key = self._get_key(key)
        return os.getenv(full_key) is not None