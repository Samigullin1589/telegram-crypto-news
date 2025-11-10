"""
Base configuration classes
Базовые классы для конфигурации
"""

import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseFeatureConfig:
    """Базовый класс для всех конфигурационных модулей"""
    
    @staticmethod
    def get_bool_env(key: str, default: bool = False) -> bool:
        """
        Получение boolean значения из переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            bool: Значение переменной
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def get_int_env(key: str, default: int) -> int:
        """
        Получение integer значения из переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            int: Значение переменной
        """
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Invalid value for {key}, using default: {default}")
            return default
    
    @staticmethod
    def get_float_env(key: str, default: float) -> float:
        """
        Получение float значения из переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            float: Значение переменной
        """
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Invalid value for {key}, using default: {default}")
            return default
    
    @staticmethod
    def get_str_env(key: str, default: str) -> str:
        """
        Получение string значения из переменной окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            str: Значение переменной
        """
        return os.getenv(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Dict: Конфигурация в виде словаря
        """
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        class_name = self.__class__.__name__
        params = ', '.join(f'{k}={v}' for k, v in self.to_dict().items())
        return f"{class_name}({params})"


__all__ = ['BaseFeatureConfig']