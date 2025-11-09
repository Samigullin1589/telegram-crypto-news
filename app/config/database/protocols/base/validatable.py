# app/config/database/protocols/base/validatable.py
"""
Validation Protocols
Протоколы для валидации объектов
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Validatable(Protocol):
    """Протокол для объектов с валидацией"""
    
    def validate(self) -> bool:
        """
        Валидация объекта
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При ошибке валидации
        """
        ...
    
    def is_valid(self) -> bool:
        """
        Проверка валидности без исключений
        
        Returns:
            True если объект валиден
        """
        ...
    
    def get_validation_errors(self) -> list[str]:
        """
        Получение списка ошибок валидации
        
        Returns:
            Список строк с описанием ошибок
        """
        ...