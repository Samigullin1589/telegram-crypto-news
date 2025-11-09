# core/initialization/environment.py
"""
Environment Initializer - Валидация окружения
"""

from typing import List, Dict, Any
from core.logging_config import get_logger
from core.startup import StartupValidator

logger = get_logger(__name__)


class EnvironmentInitializer:
    """
    Валидация окружения и конфигурации
    
    Проверяет:
    - Переменные окружения
    - Права доступа
    - Зависимости
    - Конфигурационные файлы
    """
    
    def __init__(self):
        """Инициализация валидатора"""
        self.validator = StartupValidator()
        self.validation_results: Dict[str, Any] = {}
    
    def validate(self) -> bool:
        """
        Выполнение валидации
        
        Returns:
            bool: True если валидация успешна
        """
        try:
            # Запуск валидации
            is_valid = self.validator.validate_all()
            
            if is_valid:
                logger.info("✅ Environment validation passed")
                return True
            else:
                logger.error("❌ Environment validation failed")
                self._log_validation_errors()
                return False
        
        except Exception as e:
            logger.error(f"❌ Environment validation error: {e}", exc_info=True)
            return False
    
    def _log_validation_errors(self) -> None:
        """Логирование ошибок валидации"""
        # Если валидатор предоставляет детали ошибок
        try:
            errors = getattr(self.validator, 'errors', [])
            for error in errors:
                logger.error(f"  • {error}")
        except:
            pass