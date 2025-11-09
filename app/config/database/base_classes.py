"""
Base Configuration Classes
Абстрактные базовые классы для всех конфигураций БД
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set
from dataclasses import fields as dataclass_fields
from pathlib import Path
from enum import Enum

from .protocols import Configurable
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZATION HELPER
# ============================================================================

class ConfigSerializer:
    """
    Вспомогательный класс для сериализации конфигураций
    
    Отвечает за преобразование различных типов данных в сериализуемый формат
    """
    
    @staticmethod
    def serialize_value(value: Any) -> Any:
        """
        Сериализация отдельного значения
        
        Args:
            value: Значение для сериализации
            
        Returns:
            Сериализованное значение
        """
        if value is None:
            return None
        
        # Перечисления
        if isinstance(value, Enum):
            return value.value
        
        # Пути
        if isinstance(value, Path):
            return str(value)
        
        # Объекты с методом to_dict
        if hasattr(value, 'to_dict') and callable(value.to_dict):
            return value.to_dict()
        
        # Списки и кортежи
        if isinstance(value, (list, tuple)):
            return [ConfigSerializer.serialize_value(item) for item in value]
        
        # Словари
        if isinstance(value, dict):
            return {
                k: ConfigSerializer.serialize_value(v) 
                for k, v in value.items()
            }
        
        # Множества
        if isinstance(value, set):
            return [ConfigSerializer.serialize_value(item) for item in value]
        
        # Примитивные типы
        if isinstance(value, (str, int, float, bool)):
            return value
        
        # Для остальных - строковое представление
        return str(value)
    
    @staticmethod
    def mask_sensitive_fields(data: Dict[str, Any], sensitive_keys: Set[str]) -> Dict[str, Any]:
        """
        Маскирование чувствительных полей в словаре
        
        Args:
            data: Словарь с данными
            sensitive_keys: Множество ключей для маскирования
            
        Returns:
            Словарь с замаскированными значениями
        """
        masked = {}
        
        for key, value in data.items():
            # Проверяем по точному совпадению и по вхождению подстроки
            is_sensitive = (
                key in sensitive_keys or
                any(sensitive in key.lower() for sensitive in ['password', 'secret', 'token', 'key'])
            )
            
            if is_sensitive and value:
                masked[key] = '***'
            elif isinstance(value, dict):
                masked[key] = ConfigSerializer.mask_sensitive_fields(value, sensitive_keys)
            else:
                masked[key] = value
        
        return masked


# ============================================================================
# BASE CONFIG
# ============================================================================

class BaseConfig(ABC, Configurable):
    """
    Абстрактный базовый класс для всех конфигураций
    
    Предоставляет базовую функциональность:
    - Автоматическая валидация при инициализации
    - Сериализация в словарь с умным преобразованием типов
    - Обновление из словаря с повторной валидацией
    - Сравнение конфигураций
    - Логирование операций
    - Маскирование чувствительных данных
    
    Подклассы должны реализовать метод validate()
    """
    
    # Поля, которые нужно маскировать при выводе
    _sensitive_fields: Set[str] = {'password', 'secret', 'token', 'api_key'}
    
    def __post_init__(self):
        """
        Автоматическая валидация после инициализации
        
        Вызывается автоматически для dataclass после __init__
        """
        try:
            self.validate()
            logger.debug(
                f"{self.__class__.__name__} initialized and validated successfully"
            )
        except ValidationError as e:
            logger.error(
                f"Validation failed for {self.__class__.__name__}: {e}",
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during {self.__class__.__name__} initialization: {e}",
                exc_info=True
            )
            raise ValidationError(f"Configuration initialization failed: {e}")
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Подклассы должны реализовать этот метод для проверки
        корректности своих параметров
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При обнаружении некорректных параметров
        """
        pass
    
    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Args:
            mask_sensitive: Маскировать чувствительные поля
            
        Returns:
            Словарь с данными конфигурации
        """
        result = {}
        
        # Проверяем, является ли объект dataclass
        try:
            fields = dataclass_fields(self)
            for field_info in fields:
                # Пропускаем приватные поля (начинающиеся с _)
                if field_info.name.startswith('_'):
                    continue
                
                value = getattr(self, field_info.name)
                result[field_info.name] = ConfigSerializer.serialize_value(value)
        
        except TypeError:
            # Если не dataclass, берём все публичные атрибуты
            for key, value in self.__dict__.items():
                if not key.startswith('_'):
                    result[key] = ConfigSerializer.serialize_value(value)
        
        # Маскируем чувствительные данные если требуется
        if mask_sensitive:
            result = ConfigSerializer.mask_sensitive_fields(
                result, 
                self._sensitive_fields
            )
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], validate: bool = True) -> None:
        """
        Обновление конфигурации из словаря
        
        Args:
            data: Словарь с новыми значениями
            validate: Выполнить валидацию после обновления
            
        Raises:
            ValidationError: При ошибке валидации (если validate=True)
        """
        updated_fields = []
        
        for key, value in data.items():
            # Пропускаем приватные поля и несуществующие атрибуты
            if key.startswith('_'):
                logger.warning(
                    f"Skipping private field update: {key} in {self.__class__.__name__}"
                )
                continue
            
            if not hasattr(self, key):
                logger.warning(
                    f"Skipping unknown field: {key} in {self.__class__.__name__}"
                )
                continue
            
            # Обновляем значение
            old_value = getattr(self, key, None)
            setattr(self, key, value)
            updated_fields.append(key)
            
            logger.debug(
                f"Updated {self.__class__.__name__}.{key}: {old_value} -> {value}"
            )
        
        # Повторная валидация после обновления
        if validate and updated_fields:
            try:
                self.validate()
                logger.info(
                    f"{self.__class__.__name__} updated and re-validated. "
                    f"Fields changed: {', '.join(updated_fields)}"
                )
            except ValidationError as e:
                logger.error(
                    f"Validation failed after update for {self.__class__.__name__}: {e}"
                )
                raise
    
    def get_field_names(self) -> List[str]:
        """
        Получение списка имён полей конфигурации
        
        Returns:
            Список имён полей (без приватных)
        """
        try:
            fields = dataclass_fields(self)
            return [f.name for f in fields if not f.name.startswith('_')]
        except TypeError:
            return [k for k in self.__dict__.keys() if not k.startswith('_')]
    
    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """
        Безопасное получение значения поля
        
        Args:
            field_name: Имя поля
            default: Значение по умолчанию
            
        Returns:
            Значение поля или default
        """
        return getattr(self, field_name, default)
    
    def has_field(self, field_name: str) -> bool:
        """
        Проверка наличия поля в конфигурации
        
        Args:
            field_name: Имя поля
            
        Returns:
            True если поле существует
        """
        return hasattr(self, field_name)
    
    def clone(self) -> "BaseConfig":
        """
        Создание копии конфигурации
        
        Returns:
            Новый экземпляр с теми же значениями
        """
        config_dict = self.to_dict(mask_sensitive=False)
        return self.__class__(**config_dict)
    
    def __repr__(self) -> str:
        """
        Строковое представление конфигурации
        
        Returns:
            Строка с именем класса и маскированными значениями полей
        """
        class_name = self.__class__.__name__
        
        try:
            fields = dataclass_fields(self)
            field_strs = []
            
            for field_info in fields:
                # Пропускаем приватные поля
                if field_info.name.startswith('_'):
                    continue
                
                value = getattr(self, field_info.name)
                
                # Маскируем чувствительные данные
                is_sensitive = any(
                    sensitive in field_info.name.lower() 
                    for sensitive in self._sensitive_fields
                )
                
                if is_sensitive and value:
                    value = '***'
                
                field_strs.append(f"{field_info.name}={value!r}")
            
            return f"{class_name}({', '.join(field_strs)})"
        
        except TypeError:
            return f"{class_name}(...)"
    
    def __str__(self) -> str:
        """
        Человекочитаемое строковое представление
        
        Returns:
            Строка с основной информацией о конфигурации
        """
        return self.__repr__()
    
    def __eq__(self, other: Any) -> bool:
        """
        Сравнение конфигураций
        
        Args:
            other: Другая конфигурация для сравнения
            
        Returns:
            True если конфигурации идентичны
        """
        if not isinstance(other, self.__class__):
            return False
        
        return self.to_dict(mask_sensitive=False) == other.to_dict(mask_sensitive=False)
    
    def __ne__(self, other: Any) -> bool:
        """Неравенство конфигураций"""
        return not self.__eq__(other)
    
    def __hash__(self) -> int:
        """
        Хеш конфигурации для использования в множествах/словарях
        
        Returns:
            Хеш-значение конфигурации
        """
        # Используем tuple из значений для хеширования
        try:
            config_dict = self.to_dict(mask_sensitive=False)
            # Сортируем для стабильности хеша
            items = tuple(sorted(config_dict.items()))
            return hash(items)
        except TypeError:
            # Если не можем захешировать, используем id объекта
            return hash(id(self))


# ============================================================================
# TIMED CONFIG
# ============================================================================

class TimedConfig(BaseConfig):
    """
    Базовый класс для конфигураций с временными проверками
    
    Предоставляет функциональность для:
    - Проверки необходимости выполнения по времени
    - Вычисления следующего времени выполнения
    - Расчёта оставшегося времени до выполнения
    
    Используется для периодических задач, таймаутов и расписаний
    """
    
    @abstractmethod
    def should_execute(self, last_time: float, current_time: float) -> bool:
        """
        Проверка необходимости выполнения операции
        
        Args:
            last_time: Время последнего выполнения (Unix timestamp)
            current_time: Текущее время (Unix timestamp)
            
        Returns:
            True если операцию нужно выполнить сейчас
        """
        pass
    
    def calculate_next_execution(
        self, 
        last_time: float, 
        interval_seconds: int
    ) -> float:
        """
        Вычисление времени следующего выполнения
        
        Args:
            last_time: Время последнего выполнения (Unix timestamp)
            interval_seconds: Интервал между выполнениями в секундах
            
        Returns:
            Unix timestamp следующего выполнения
        """
        if last_time < 0:
            logger.warning(f"Invalid last_time: {last_time}, using 0")
            last_time = 0
        
        if interval_seconds < 0:
            logger.warning(f"Invalid interval: {interval_seconds}, using 1")
            interval_seconds = 1
        
        return last_time + interval_seconds
    
    def time_until_next(
        self, 
        last_time: float, 
        current_time: float, 
        interval_seconds: int
    ) -> float:
        """
        Вычисление времени до следующего выполнения
        
        Args:
            last_time: Время последнего выполнения (Unix timestamp)
            current_time: Текущее время (Unix timestamp)
            interval_seconds: Интервал между выполнениями в секундах
            
        Returns:
            Количество секунд до следующего выполнения (0 если пора выполнять)
        """
        next_time = self.calculate_next_execution(last_time, interval_seconds)
        remaining = next_time - current_time
        
        return max(0.0, remaining)
    
    def is_overdue(
        self,
        last_time: float,
        current_time: float,
        interval_seconds: int,
        grace_period_seconds: float = 0.0
    ) -> bool:
        """
        Проверка просроченности выполнения
        
        Args:
            last_time: Время последнего выполнения
            current_time: Текущее время
            interval_seconds: Интервал между выполнениями
            grace_period_seconds: Льготный период перед пометкой как просроченное
            
        Returns:
            True если выполнение просрочено за пределами льготного периода
        """
        next_time = self.calculate_next_execution(last_time, interval_seconds)
        overdue_threshold = next_time + grace_period_seconds
        
        return current_time > overdue_threshold
    
    def get_execution_stats(
        self,
        last_time: float,
        current_time: float,
        interval_seconds: int
    ) -> Dict[str, Any]:
        """
        Получение статистики по выполнению
        
        Args:
            last_time: Время последнего выполнения
            current_time: Текущее время
            interval_seconds: Интервал между выполнениями
            
        Returns:
            Словарь со статистикой выполнения
        """
        next_time = self.calculate_next_execution(last_time, interval_seconds)
        time_until = self.time_until_next(last_time, current_time, interval_seconds)
        elapsed = current_time - last_time if last_time > 0 else 0
        
        return {
            'last_execution': last_time,
            'next_execution': next_time,
            'current_time': current_time,
            'interval_seconds': interval_seconds,
            'time_until_next': time_until,
            'elapsed_since_last': elapsed,
            'should_execute': self.should_execute(last_time, current_time),
            'is_overdue': self.is_overdue(last_time, current_time, interval_seconds)
        }


# ============================================================================
# VALIDATION MIXIN
# ============================================================================

class ValidationMixin:
    """
    Миксин для общих методов валидации
    
    Предоставляет переиспользуемые методы валидации для различных типов данных
    """
    
    @staticmethod
    def validate_positive_number(
        value: float,
        field_name: str,
        min_value: float = 0.0,
        allow_zero: bool = False
    ) -> None:
        """
        Валидация положительного числа
        
        Args:
            value: Значение для проверки
            field_name: Имя поля (для сообщения об ошибке)
            min_value: Минимальное допустимое значение
            allow_zero: Разрешить ноль
            
        Raises:
            ValidationError: Если значение некорректно
        """
        if allow_zero and value == 0:
            return
        
        if value < min_value:
            raise ValidationError(
                f"{field_name} must be >= {min_value}, got {value}"
            )
    
    @staticmethod
    def validate_non_empty_string(value: str, field_name: str) -> None:
        """
        Валидация непустой строки
        
        Args:
            value: Значение для проверки
            field_name: Имя поля
            
        Raises:
            ValidationError: Если строка пустая
        """
        if not value or not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")
    
    @staticmethod
    def validate_port(port: int, field_name: str = "port") -> None:
        """
        Валидация номера порта
        
        Args:
            port: Номер порта
            field_name: Имя поля
            
        Raises:
            ValidationError: Если порт некорректен
        """
        if not isinstance(port, int):
            raise ValidationError(f"{field_name} must be an integer, got {type(port)}")
        
        if not 1 <= port <= 65535:
            raise ValidationError(
                f"{field_name} must be between 1 and 65535, got {port}"
            )
    
    @staticmethod
    def validate_file_path(
        path: Optional[Path],
        field_name: str,
        must_exist: bool = True,
        required: bool = False
    ) -> None:
        """
        Валидация пути к файлу
        
        Args:
            path: Путь для проверки
            field_name: Имя поля
            must_exist: Файл должен существовать
            required: Путь обязателен
            
        Raises:
            ValidationError: Если путь некорректен
        """
        if path is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return
        
        if must_exist and not path.exists():
            raise ValidationError(f"{field_name} file not found: {path}")


__all__ = [
    'ConfigSerializer',
    'BaseConfig',
    'TimedConfig',
    'ValidationMixin'
]