# app/config/database/protocols/base.py
"""
Base Protocols
Базовые протоколы для всех компонентов
"""

from typing import Protocol, Dict, Any, TypeVar, runtime_checkable


T = TypeVar('T')


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


@runtime_checkable
class Serializable(Protocol):
    """Протокол для сериализуемых объектов"""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация объекта в словарь
        
        Returns:
            Словарь с данными объекта
        """
        ...
    
    def to_json(self) -> str:
        """
        Конвертация объекта в JSON строку
        
        Returns:
            JSON представление объекта
        """
        ...
    
    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        """
        Создание объекта из словаря
        
        Args:
            data: Словарь с данными
            
        Returns:
            Экземпляр объекта
        """
        ...
    
    @classmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """
        Создание объекта из JSON строки
        
        Args:
            json_str: JSON строка
            
        Returns:
            Экземпляр объекта
        """
        ...


@runtime_checkable
class Updatable(Protocol):
    """Протокол для обновляемых объектов"""
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Обновление объекта из словаря
        
        Args:
            data: Словарь с новыми значениями
        """
        ...
    
    def merge(self: T, other: T) -> T:
        """
        Слияние с другим объектом того же типа
        
        Args:
            other: Другой объект для слияния
            
        Returns:
            Новый объект с объединенными данными
        """
        ...
    
    def apply_defaults(self) -> None:
        """Применение значений по умолчанию для пустых полей"""
        ...


@runtime_checkable
class Configurable(Validatable, Serializable, Updatable, Protocol):
    """Полный протокол для конфигурационных объектов"""
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Получение схемы конфигурации
        
        Returns:
            Словарь со схемой (поля, типы, ограничения)
        """
        ...
    
    def get_config_version(self) -> str:
        """
        Версия схемы конфигурации
        
        Returns:
            Строка с версией (semver)
        """
        ...


@runtime_checkable
class Cloneable(Protocol[T]):
    """Протокол для клонируемых объектов"""
    
    def clone(self: T) -> T:
        """
        Создание глубокой копии объекта
        
        Returns:
            Новый экземпляр с теми же данными
        """
        ...
    
    def shallow_copy(self: T) -> T:
        """
        Создание поверхностной копии объекта
        
        Returns:
            Новый экземпляр с ссылками на те же вложенные объекты
        """
        ...


@runtime_checkable
class Comparable(Protocol):
    """Протокол для сравнимых объектов"""
    
    def equals(self, other: Any) -> bool:
        """
        Сравнение с другим объектом
        
        Args:
            other: Объект для сравнения
            
        Returns:
            True если объекты равны
        """
        ...
    
    def diff(self, other: Any) -> Dict[str, tuple[Any, Any]]:
        """
        Получение различий с другим объектом
        
        Args:
            other: Объект для сравнения
            
        Returns:
            Словарь {поле: (значение_self, значение_other)}
        """
        ...


@runtime_checkable
class ConfigHashable(Protocol):
    """Протокол для объектов с хешированием (renamed to avoid conflict with collections.abc.Hashable)"""
    
    def compute_hash(self) -> str:
        """
        Вычисление хеша объекта
        
        Returns:
            Строка с хешем (обычно SHA256)
        """
        ...
    
    def get_fingerprint(self) -> str:
        """
        Получение короткого отпечатка объекта
        
        Returns:
            Короткая строка-идентификатор (8-16 символов)
        """
        ...