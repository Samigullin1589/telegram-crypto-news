"""
Database Configuration Base Classes
Базовые классы для всех конфигураций
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import fields
from pathlib import Path
from enum import Enum

from .protocols import Configurable
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseConfig(ABC, Configurable):
    """
    Абстрактный базовый класс для всех конфигураций
    
    Обеспечивает:
    - Автоматическую валидацию после инициализации
    - Сериализацию в словарь
    - Обновление из словаря
    - Логирование
    """
    
    def __post_init__(self):
        """Автоматическая валидация после инициализации"""
        try:
            self.validate()
        except ValidationError as e:
            logger.error(f"Validation failed for {self.__class__.__name__}: {e}")
            raise
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При ошибке валидации
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Словарь с данными конфигурации
        """
        result = {}
        
        # Используем dataclass fields для получения всех атрибутов
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            result[field_info.name] = self._serialize_value(value)
        
        return result
    
    def _serialize_value(self, value: Any) -> Any:
        """
        Сериализация отдельного значения
        
        Args:
            value: Значение для сериализации
            
        Returns:
            Сериализованное значение
        """
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, Path):
            return str(value)
        elif hasattr(value, 'to_dict'):
            return value.to_dict()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        else:
            return value
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Обновление конфигурации из словаря
        
        Args:
            data: Словарь с новыми значениями
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Повторная валидация после обновления
        self.validate()
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        class_name = self.__class__.__name__
        field_strs = []
        
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            field_strs.append(f"{field_info.name}={value!r}")
        
        return f"{class_name}({', '.join(field_strs)})"
    
    def __eq__(self, other) -> bool:
        """Сравнение конфигураций"""
        if not isinstance(other, self.__class__):
            return False
        
        return self.to_dict() == other.to_dict()


class TimedConfig(BaseConfig):
    """
    Базовый класс для конфигураций с временными проверками
    """
    
    @abstractmethod
    def should_execute(self, last_time: float, current_time: float) -> bool:
        """
        Проверка необходимости выполнения операции
        
        Args:
            last_time: Время последнего выполнения (timestamp)
            current_time: Текущее время (timestamp)
            
        Returns:
            True если операцию нужно выполнить
        """
        pass
    
    def calculate_next_execution(self, last_time: float, interval_seconds: int) -> float:
        """
        Вычисление времени следующего выполнения
        
        Args:
            last_time: Время последнего выполнения (timestamp)
            interval_seconds: Интервал в секундах
            
        Returns:
            Timestamp следующего выполнения
        """
        return last_time + interval_seconds
    
    def time_until_next(self, last_time: float, current_time: float, interval_seconds: int) -> float:
        """
        Время до следующего выполнения
        
        Args:
            last_time: Время последнего выполнения
            current_time: Текущее время
            interval_seconds: Интервал в секундах
            
        Returns:
            Секунд до следующего выполнения (0 если пора выполнять)
        """
        next_time = self.calculate_next_execution(last_time, interval_seconds)
        remaining = next_time - current_time
        return max(0, remaining)