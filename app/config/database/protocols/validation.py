# app/config/database/protocols/validation.py
"""
Validation Protocols
Протоколы для валидации
"""

from typing import Protocol, Any, Callable, List, Tuple, runtime_checkable


@runtime_checkable
class ValidationRule(Protocol):
    """Протокол для правила валидации"""
    
    def validate(self, value: Any) -> bool:
        """
        Валидация значения
        
        Args:
            value: Значение для проверки
            
        Returns:
            True если значение валидно
        """
        ...
    
    def get_error_message(self) -> str:
        """
        Получение сообщения об ошибке
        
        Returns:
            Описание ошибки валидации
        """
        ...
    
    def get_rule_name(self) -> str:
        """
        Название правила
        
        Returns:
            Имя правила
        """
        ...


@runtime_checkable
class ValidatorProtocol(Protocol):
    """Протокол для валидатора"""
    
    def validate(self, data: Any) -> Tuple[bool, List[str]]:
        """
        Валидация данных
        
        Args:
            data: Данные для валидации
            
        Returns:
            Кортеж (успех, список ошибок)
        """
        ...
    
    def add_rule(self, rule: ValidationRule) -> None:
        """
        Добавление правила валидации
        
        Args:
            rule: Правило валидации
        """
        ...
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Удаление правила
        
        Args:
            rule_name: Имя правила
            
        Returns:
            True если правило удалено
        """
        ...
    
    def get_rules(self) -> List[ValidationRule]:
        """
        Получение всех правил
        
        Returns:
            Список правил валидации
        """
        ...
    
    def clear_rules(self) -> None:
        """Очистка всех правил"""
        ...


@runtime_checkable
class AsyncValidatorProtocol(Protocol):
    """Протокол для асинхронного валидатора"""
    
    async def validate(self, data: Any) -> Tuple[bool, List[str]]:
        """
        Асинхронная валидация данных
        
        Args:
            data: Данные для валидации
            
        Returns:
            Кортеж (успех, список ошибок)
        """
        ...
    
    async def validate_field(self, 
                            field: str, 
                            value: Any) -> Tuple[bool, str]:
        """
        Валидация отдельного поля
        
        Args:
            field: Имя поля
            value: Значение поля
            
        Returns:
            Кортеж (успех, сообщение об ошибке)
        """
        ...
    
    async def validate_multiple_fields(self,
                                      fields: dict[str, Any]) -> Tuple[bool, dict[str, str]]:
        """
        Валидация множества полей
        
        Args:
            fields: Словарь {имя_поля: значение}
            
        Returns:
            Кортеж (успех, словарь {поле: ошибка})
        """
        ...


@runtime_checkable
class ChainableValidator(Protocol):
    """Протокол для цепочки валидаторов"""
    
    def chain(self, validator: 'ChainableValidator') -> 'ChainableValidator':
        """
        Добавление валидатора в цепочку
        
        Args:
            validator: Следующий валидатор
            
        Returns:
            Обновленная цепочка
        """
        ...
    
    def validate_chain(self, data: Any) -> Tuple[bool, List[str]]:
        """
        Валидация через цепочку валидаторов
        
        Args:
            data: Данные для валидации
            
        Returns:
            Кортеж (успех, список ошибок)
        """
        ...
    
    def get_chain_length(self) -> int:
        """
        Получение длины цепочки
        
        Returns:
            Количество валидаторов в цепочке
        """
        ...
    
    def get_validators(self) -> List['ChainableValidator']:
        """
        Получение всех валидаторов цепочки
        
        Returns:
            Список валидаторов
        """
        ...


@runtime_checkable
class ConditionalValidator(Protocol):
    """Протокол для условной валидации"""
    
    def validate_if(self, 
                    condition: Callable[[Any], bool], 
                    data: Any) -> Tuple[bool, List[str]]:
        """
        Валидация при выполнении условия
        
        Args:
            condition: Функция проверки условия
            data: Данные для валидации
            
        Returns:
            Кортеж (успех, список ошибок)
        """
        ...
    
    def validate_unless(self,
                       condition: Callable[[Any], bool],
                       data: Any) -> Tuple[bool, List[str]]:
        """
        Валидация если условие не выполнено
        
        Args:
            condition: Функция проверки условия
            data: Данные для валидации
            
        Returns:
            Кортеж (успех, список ошибок)
        """
        ...
    
    def add_condition(self, 
                     name: str,
                     condition: Callable[[Any], bool]) -> None:
        """
        Добавление именованного условия
        
        Args:
            name: Имя условия
            condition: Функция проверки условия
        """
        ...
    
    def remove_condition(self, name: str) -> bool:
        """
        Удаление условия
        
        Args:
            name: Имя условия
            
        Returns:
            True если условие удалено
        """
        ...
    
    def get_conditions(self) -> dict[str, Callable[[Any], bool]]:
        """
        Получение всех условий
        
        Returns:
            Словарь {имя: функция_условия}
        """
        ...