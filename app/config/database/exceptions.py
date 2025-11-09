"""
Database Configuration Exceptions
Полная система исключений для конфигурации и управления БД

Иерархия исключений:
    DatabaseConfigError (базовое)
    ├── ValidationError
    │   ├── DatabaseValidationError
    │   ├── FieldValidationError
    │   ├── TypeValidationError
    │   └── RangeValidationError
    ├── ConnectionError
    │   ├── DatabaseConnectionError
    │   ├── PoolConnectionError
    │   ├── TimeoutError
    │   └── AuthenticationError
    ├── ConfigurationError
    │   ├── MissingConfigError
    │   ├── InvalidConfigError
    │   └── ConfigConflictError
    ├── EnvironmentError
    │   ├── MissingEnvironmentError
    │   └── InvalidEnvironmentError
    ├── ComponentError
    │   ├── ComponentInitError
    │   ├── ComponentStateError
    │   └── ComponentNotFoundError
    ├── OperationError
    │   ├── QueryError
    │   ├── TransactionError
    │   └── LockError
    └── ResourceError
        ├── PoolExhaustedError
        ├── MemoryError
        └── DiskSpaceError
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================================================
# BASE EXCEPTION
# ============================================================================

class DatabaseConfigError(Exception):
    """
    Базовое исключение для всех ошибок конфигурации БД
    
    Attributes:
        message: Описание ошибки
        details: Дополнительные детали ошибки
        timestamp: Время возникновения ошибки
        context: Контекст выполнения
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.context = context or {}
        self.timestamp = datetime.utcnow()
    
    def __str__(self) -> str:
        parts = [self.message]
        
        if self.details:
            details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"Details: {details_str}")
        
        if self.context:
            context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        
        return ' | '.join(parts)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация исключения в словарь"""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(DatabaseConfigError):
    """Базовая ошибка валидации"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
        if reason:
            details['reason'] = reason
        
        super().__init__(message, details, **kwargs)
        self.field = field
        self.value = value
        self.reason = reason


class DatabaseValidationError(ValidationError):
    """Ошибка валидации конфигурации базы данных"""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []
        if self.validation_errors:
            self.details['validation_errors'] = self.validation_errors


class FieldValidationError(ValidationError):
    """Ошибка валидации конкретного поля"""
    
    def __init__(
        self,
        field: str,
        value: Any,
        expected_type: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        message = f"Field validation failed: {field}"
        super().__init__(message, field=field, value=value, **kwargs)
        self.expected_type = expected_type
        self.constraints = constraints or {}
        
        if expected_type:
            self.details['expected_type'] = expected_type
        if constraints:
            self.details['constraints'] = constraints


class TypeValidationError(ValidationError):
    """Ошибка валидации типа данных"""
    
    def __init__(
        self,
        field: str,
        value: Any,
        expected_type: type,
        actual_type: type,
        **kwargs
    ):
        message = f"Type mismatch for field '{field}': expected {expected_type.__name__}, got {actual_type.__name__}"
        super().__init__(
            message,
            field=field,
            value=value,
            reason=f"expected {expected_type.__name__}, got {actual_type.__name__}",
            **kwargs
        )
        self.expected_type = expected_type
        self.actual_type = actual_type


class RangeValidationError(ValidationError):
    """Ошибка валидации диапазона значений"""
    
    def __init__(
        self,
        field: str,
        value: Any,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        **kwargs
    ):
        constraints = []
        if min_value is not None:
            constraints.append(f">= {min_value}")
        if max_value is not None:
            constraints.append(f"<= {max_value}")
        
        message = f"Value {value} for field '{field}' is out of range ({', '.join(constraints)})"
        super().__init__(message, field=field, value=value, **kwargs)
        self.min_value = min_value
        self.max_value = max_value


# ============================================================================
# CONNECTION EXCEPTIONS
# ============================================================================

class ConnectionError(DatabaseConfigError):
    """Базовая ошибка подключения"""
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if host:
            details['host'] = host
        if port:
            details['port'] = port
        if database:
            details['database'] = database
        
        super().__init__(message, details, **kwargs)
        self.host = host
        self.port = port
        self.database = database


class DatabaseConnectionError(ConnectionError):
    """Ошибка подключения к базе данных"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.error_code = error_code
        self.original_error = original_error
        
        if error_code:
            self.details['error_code'] = error_code
        if original_error:
            self.details['original_error'] = str(original_error)


class PoolConnectionError(ConnectionError):
    """Ошибка получения соединения из пула"""
    
    def __init__(
        self,
        message: str,
        pool_size: Optional[int] = None,
        active_connections: Optional[int] = None,
        waiting_requests: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.pool_size = pool_size
        self.active_connections = active_connections
        self.waiting_requests = waiting_requests
        
        if pool_size is not None:
            self.details['pool_size'] = pool_size
        if active_connections is not None:
            self.details['active_connections'] = active_connections
        if waiting_requests is not None:
            self.details['waiting_requests'] = waiting_requests


class TimeoutError(ConnectionError):
    """Ошибка таймаута операции"""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        
        if timeout_seconds is not None:
            self.details['timeout_seconds'] = timeout_seconds
        if operation:
            self.details['operation'] = operation


class AuthenticationError(ConnectionError):
    """Ошибка аутентификации"""
    
    def __init__(
        self,
        message: str,
        username: Optional[str] = None,
        auth_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.username = username
        self.auth_method = auth_method
        
        if username:
            self.details['username'] = username
        if auth_method:
            self.details['auth_method'] = auth_method


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================

class ConfigurationError(DatabaseConfigError):
    """Базовая ошибка конфигурации"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Any = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if config_key:
            details['config_key'] = config_key
        if config_value is not None:
            details['config_value'] = config_value
        
        super().__init__(message, details, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class MissingConfigError(ConfigurationError):
    """Ошибка отсутствующей конфигурации"""
    
    def __init__(
        self,
        config_key: str,
        required_for: Optional[str] = None,
        **kwargs
    ):
        message = f"Missing required configuration: {config_key}"
        if required_for:
            message += f" (required for {required_for})"
        
        super().__init__(message, config_key=config_key, **kwargs)
        self.required_for = required_for


class InvalidConfigError(ConfigurationError):
    """Ошибка некорректной конфигурации"""
    
    def __init__(
        self,
        config_key: str,
        config_value: Any,
        reason: str,
        **kwargs
    ):
        message = f"Invalid configuration for '{config_key}': {reason}"
        super().__init__(message, config_key=config_key, config_value=config_value, **kwargs)
        self.reason = reason
        self.details['reason'] = reason


class ConfigConflictError(ConfigurationError):
    """Ошибка конфликта конфигураций"""
    
    def __init__(
        self,
        message: str,
        conflicting_keys: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.conflicting_keys = conflicting_keys or []
        if self.conflicting_keys:
            self.details['conflicting_keys'] = self.conflicting_keys


# ============================================================================
# ENVIRONMENT EXCEPTIONS
# ============================================================================

class EnvironmentError(DatabaseConfigError):
    """Базовая ошибка переменных окружения"""
    
    def __init__(
        self,
        message: str,
        env_var: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if env_var:
            details['env_var'] = env_var
        
        super().__init__(message, details, **kwargs)
        self.env_var = env_var


class MissingEnvironmentError(EnvironmentError):
    """Ошибка отсутствующей переменной окружения"""
    
    def __init__(
        self,
        env_var: str,
        required_for: Optional[str] = None,
        **kwargs
    ):
        message = f"Missing required environment variable: {env_var}"
        if required_for:
            message += f" (required for {required_for})"
        
        super().__init__(message, env_var=env_var, **kwargs)
        self.required_for = required_for


class InvalidEnvironmentError(EnvironmentError):
    """Ошибка некорректной переменной окружения"""
    
    def __init__(
        self,
        env_var: str,
        value: str,
        reason: str,
        **kwargs
    ):
        message = f"Invalid environment variable '{env_var}': {reason}"
        super().__init__(message, env_var=env_var, **kwargs)
        self.value = value
        self.reason = reason
        self.details['value'] = value
        self.details['reason'] = reason


# ============================================================================
# COMPONENT EXCEPTIONS
# ============================================================================

class ComponentError(DatabaseConfigError):
    """Базовая ошибка компонента"""
    
    def __init__(
        self,
        message: str,
        component_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if component_name:
            details['component_name'] = component_name
        
        super().__init__(message, details, **kwargs)
        self.component_name = component_name


class ComponentInitError(ComponentError):
    """Ошибка инициализации компонента"""
    
    def __init__(
        self,
        component_name: str,
        reason: str,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        message = f"Failed to initialize component '{component_name}': {reason}"
        super().__init__(message, component_name=component_name, **kwargs)
        self.reason = reason
        self.original_error = original_error
        
        if original_error:
            self.details['original_error'] = str(original_error)


class ComponentStateError(ComponentError):
    """Ошибка состояния компонента"""
    
    def __init__(
        self,
        component_name: str,
        current_state: str,
        expected_state: str,
        **kwargs
    ):
        message = f"Component '{component_name}' is in invalid state: {current_state} (expected {expected_state})"
        super().__init__(message, component_name=component_name, **kwargs)
        self.current_state = current_state
        self.expected_state = expected_state
        self.details['current_state'] = current_state
        self.details['expected_state'] = expected_state


class ComponentNotFoundError(ComponentError):
    """Ошибка отсутствия компонента"""
    
    def __init__(
        self,
        component_name: str,
        available_components: Optional[List[str]] = None,
        **kwargs
    ):
        message = f"Component not found: {component_name}"
        super().__init__(message, component_name=component_name, **kwargs)
        self.available_components = available_components or []
        
        if self.available_components:
            self.details['available_components'] = self.available_components


# ============================================================================
# OPERATION EXCEPTIONS
# ============================================================================

class OperationError(DatabaseConfigError):
    """Базовая ошибка операции БД"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if operation:
            details['operation'] = operation
        
        super().__init__(message, details, **kwargs)
        self.operation = operation


class QueryError(OperationError):
    """Ошибка выполнения запроса"""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation='query', **kwargs)
        self.query = query
        self.parameters = parameters
        self.error_code = error_code
        
        if query:
            self.details['query'] = query[:200]  # Обрезаем длинные запросы
        if parameters:
            self.details['parameters'] = parameters
        if error_code:
            self.details['error_code'] = error_code


class TransactionError(OperationError):
    """Ошибка транзакции"""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        isolation_level: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation='transaction', **kwargs)
        self.transaction_id = transaction_id
        self.isolation_level = isolation_level
        
        if transaction_id:
            self.details['transaction_id'] = transaction_id
        if isolation_level:
            self.details['isolation_level'] = isolation_level


class LockError(OperationError):
    """Ошибка блокировки"""
    
    def __init__(
        self,
        message: str,
        lock_type: Optional[str] = None,
        resource: Optional[str] = None,
        holder: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation='lock', **kwargs)
        self.lock_type = lock_type
        self.resource = resource
        self.holder = holder
        
        if lock_type:
            self.details['lock_type'] = lock_type
        if resource:
            self.details['resource'] = resource
        if holder:
            self.details['holder'] = holder


# ============================================================================
# RESOURCE EXCEPTIONS
# ============================================================================

class ResourceError(DatabaseConfigError):
    """Базовая ошибка ресурсов"""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        
        super().__init__(message, details, **kwargs)
        self.resource_type = resource_type


class PoolExhaustedError(ResourceError):
    """Ошибка исчерпания пула соединений"""
    
    def __init__(
        self,
        message: str,
        pool_size: int,
        active_connections: int,
        waiting_count: int,
        **kwargs
    ):
        super().__init__(message, resource_type='connection_pool', **kwargs)
        self.pool_size = pool_size
        self.active_connections = active_connections
        self.waiting_count = waiting_count
        
        self.details.update({
            'pool_size': pool_size,
            'active_connections': active_connections,
            'waiting_count': waiting_count
        })


class MemoryError(ResourceError):
    """Ошибка нехватки памяти"""
    
    def __init__(
        self,
        message: str,
        required_mb: Optional[float] = None,
        available_mb: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, resource_type='memory', **kwargs)
        self.required_mb = required_mb
        self.available_mb = available_mb
        
        if required_mb is not None:
            self.details['required_mb'] = required_mb
        if available_mb is not None:
            self.details['available_mb'] = available_mb


class DiskSpaceError(ResourceError):
    """Ошибка нехватки дискового пространства"""
    
    def __init__(
        self,
        message: str,
        required_gb: Optional[float] = None,
        available_gb: Optional[float] = None,
        path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, resource_type='disk_space', **kwargs)
        self.required_gb = required_gb
        self.available_gb = available_gb
        self.path = path
        
        if required_gb is not None:
            self.details['required_gb'] = required_gb
        if available_gb is not None:
            self.details['available_gb'] = available_gb
        if path:
            self.details['path'] = path


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_exception_chain(exc: Exception) -> List[Dict[str, Any]]:
    """
    Форматирование цепочки исключений
    
    Args:
        exc: Исключение для форматирования
        
    Returns:
        Список словарей с информацией об исключениях в цепочке
    """
    chain = []
    current = exc
    
    while current is not None:
        if isinstance(current, DatabaseConfigError):
            chain.append(current.to_dict())
        else:
            chain.append({
                'type': type(current).__name__,
                'message': str(current),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        current = getattr(current, '__cause__', None) or getattr(current, '__context__', None)
    
    return chain


def is_transient_error(exc: Exception) -> bool:
    """
    Проверка, является ли ошибка временной (можно повторить операцию)
    
    Args:
        exc: Исключение для проверки
        
    Returns:
        True если ошибка временная
    """
    transient_types = (
        TimeoutError,
        PoolConnectionError,
        PoolExhaustedError,
        LockError
    )
    
    return isinstance(exc, transient_types)


def is_critical_error(exc: Exception) -> bool:
    """
    Проверка, является ли ошибка критической (требует немедленного вмешательства)
    
    Args:
        exc: Исключение для проверки
        
    Returns:
        True если ошибка критическая
    """
    critical_types = (
        DatabaseConnectionError,
        AuthenticationError,
        MemoryError,
        DiskSpaceError,
        ComponentInitError
    )
    
    return isinstance(exc, critical_types)


def get_exception_severity(exc: Exception) -> str:
    """
    Определение серьёзности исключения
    
    Args:
        exc: Исключение для анализа
        
    Returns:
        Уровень серьёзности: 'critical', 'high', 'medium', 'low'
    """
    if is_critical_error(exc):
        return 'critical'
    elif isinstance(exc, (OperationError, ConfigurationError, ComponentError)):
        return 'high'
    elif isinstance(exc, (ValidationError, EnvironmentError)):
        return 'medium'
    else:
        return 'low'


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Base
    'DatabaseConfigError',
    
    # Validation
    'ValidationError',
    'DatabaseValidationError',
    'FieldValidationError',
    'TypeValidationError',
    'RangeValidationError',
    
    # Connection
    'ConnectionError',
    'DatabaseConnectionError',
    'PoolConnectionError',
    'TimeoutError',
    'AuthenticationError',
    
    # Configuration
    'ConfigurationError',
    'MissingConfigError',
    'InvalidConfigError',
    'ConfigConflictError',
    
    # Environment
    'EnvironmentError',
    'MissingEnvironmentError',
    'InvalidEnvironmentError',
    
    # Component
    'ComponentError',
    'ComponentInitError',
    'ComponentStateError',
    'ComponentNotFoundError',
    
    # Operation
    'OperationError',
    'QueryError',
    'TransactionError',
    'LockError',
    
    # Resource
    'ResourceError',
    'PoolExhaustedError',
    'MemoryError',
    'DiskSpaceError',
    
    # Utilities
    'format_exception_chain',
    'is_transient_error',
    'is_critical_error',
    'get_exception_severity',
]