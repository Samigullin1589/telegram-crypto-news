# core/components/loader_utils.py
"""
Loader Utilities
Вспомогательные функции для загрузчиков
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LoaderUtils:
    """
    Утилиты для загрузчиков компонентов
    
    Общие функции для всех загрузчиков
    """
    
    @staticmethod
    def check_feature_enabled(feature: str, default: bool = False) -> bool:
        """
        Проверка включена ли фича
        
        Args:
            feature: Название фичи
            default: Значение по умолчанию
            
        Returns:
            True если включена
        """
        try:
            from app.config import config
            return config.is_feature_enabled(feature)
        except Exception as e:
            logger.debug(f"Config check failed for {feature}: {e}")
            return default
    
    @staticmethod
    def validate_methods(obj: Any, required_methods: list) -> bool:
        """
        Валидация наличия методов
        
        Args:
            obj: Объект для проверки
            required_methods: Список обязательных методов
            
        Returns:
            True если все методы есть
        """
        for method in required_methods:
            if not hasattr(obj, method):
                logger.error(f"Missing required method: {method}")
                return False
        
        return True
    
    @staticmethod
    def safe_import(module_path: str, class_name: str) -> Optional[Any]:
        """
        Безопасный импорт класса
        
        Args:
            module_path: Путь к модулю
            class_name: Название класса
            
        Returns:
            Класс или None
        """
        try:
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.debug(f"Import failed {module_path}.{class_name}: {e}")
            return None
    
    @staticmethod
    def log_component_status(name: str, status: str, details: str = ""):
        """
        Логирование статуса компонента
        
        Args:
            name: Название компонента
            status: Статус (success, warning, error)
            details: Дополнительные детали
        """
        icons = {
            'success': '✅',
            'warning': '⚠️ ',
            'error': '❌',
            'info': 'ℹ️ '
        }
        
        icon = icons.get(status, '•')
        message = f"{icon} [{name}] {details}" if details else f"{icon} [{name}]"
        
        if status == 'error':
            logger.error(message)
        elif status == 'warning':
            logger.warning(message)
        elif status == 'info':
            logger.info(message)
        else:
            logger.info(message)


__all__ = ['LoaderUtils']