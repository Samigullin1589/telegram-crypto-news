"""
Database Configuration Validators
Полная система валидации конфигураций БД
"""

import re
import logging
from typing import Any, Callable, TypeVar, Optional, List, Dict, Tuple
from functools import wraps
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from ipaddress import ip_address, IPv4Address, IPv6Address

from .exceptions import ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# VALIDATION RESULT
# ============================================================================

@dataclass
class ValidationIssue:
    """
    Отдельная проблема валидации
    
    Attributes:
        field: Имя поля с проблемой
        value: Проблемное значение
        severity: Серьёзность (error/warning/info)
        message: Описание проблемы
        suggestion: Рекомендация по исправлению
    """
    field: str
    value: Any
    severity: str  # 'error', 'warning', 'info'
    message: str
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Строковое представление"""
        result = f"[{self.severity.upper()}] {self.field}: {self.message}"
        if self.suggestion:
            result += f" (Suggestion: {self.suggestion})"
        return result


@dataclass
class ValidationResult:
    """
    Результат валидации конфигурации
    
    Attributes:
        is_valid: Общий результат валидации
        errors: Список ошибок
        warnings: Список предупреждений
        info: Список информационных сообщений
        validated_fields: Список успешно провалидированных полей
    """
    is_valid: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    validated_fields: List[str] = field(default_factory=list)
    
    def add_error(
        self,
        field: str,
        value: Any,
        message: str,
        suggestion: Optional[str] = None
    ) -> None:
        """Добавление ошибки"""
        self.errors.append(
            ValidationIssue(field, value, 'error', message, suggestion)
        )
        self.is_valid = False
    
    def add_warning(
        self,
        field: str,
        value: Any,
        message: str,
        suggestion: Optional[str] = None
    ) -> None:
        """Добавление предупреждения"""
        self.warnings.append(
            ValidationIssue(field, value, 'warning', message, suggestion)
        )
    
    def add_info(
        self,
        field: str,
        value: Any,
        message: str
    ) -> None:
        """Добавление информации"""
        self.info.append(
            ValidationIssue(field, value, 'info', message)
        )
    
    def mark_validated(self, field: str) -> None:
        """Отметка поля как провалидированного"""
        if field not in self.validated_fields:
            self.validated_fields.append(field)
    
    def merge(self, other: "ValidationResult") -> None:
        """Слияние с другим результатом"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
        self.validated_fields.extend(other.validated_fields)
        if not other.is_valid:
            self.is_valid = False
    
    def get_all_issues(self) -> List[ValidationIssue]:
        """Получение всех проблем"""
        return self.errors + self.warnings + self.info
    
    def has_errors(self) -> bool:
        """Проверка наличия ошибок"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Проверка наличия предупреждений"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Получение краткой сводки"""
        return {
            'is_valid': self.is_valid,
            'total_issues': len(self.get_all_issues()),
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
            'info_count': len(self.info),
            'validated_fields_count': len(self.validated_fields)
        }
    
    def __str__(self) -> str:
        """Строковое представление"""
        lines = [f"Validation Result: {'VALID' if self.is_valid else 'INVALID'}"]
        
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        if self.info:
            lines.append(f"\nInfo ({len(self.info)}):")
            for info_item in self.info:
                lines.append(f"  - {info_item}")
        
        return "\n".join(lines)


# ============================================================================
# BASIC VALIDATORS
# ============================================================================

class BasicValidators:
    """Базовые валидаторы для примитивных типов"""
    
    @staticmethod
    def validate_positive(
        value: Any,
        field_name: str,
        allow_zero: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> ValidationResult:
        """Валидация положительного числа"""
        result = ValidationResult()
        
        try:
            numeric_value = float(value)
            
            minimum = min_value if min_value is not None else (0 if allow_zero else 0.0001)
            
            if numeric_value < minimum:
                result.add_error(
                    field_name,
                    value,
                    f"must be >= {minimum}",
                    f"Use a value >= {minimum}"
                )
            elif max_value is not None and numeric_value > max_value:
                result.add_error(
                    field_name,
                    value,
                    f"must be <= {max_value}",
                    f"Use a value <= {max_value}"
                )
            else:
                result.mark_validated(field_name)
        
        except (ValueError, TypeError) as e:
            result.add_error(
                field_name,
                value,
                f"must be a numeric value: {e}",
                "Provide a valid number"
            )
        
        return result
    
    @staticmethod
    def validate_range(
        value: Any,
        field_name: str,
        min_val: float,
        max_val: float,
        inclusive: bool = True
    ) -> ValidationResult:
        """Валидация диапазона"""
        result = ValidationResult()
        
        try:
            numeric_value = float(value)
            
            if inclusive:
                in_range = min_val <= numeric_value <= max_val
                bracket = "[]"
            else:
                in_range = min_val < numeric_value < max_val
                bracket = "()"
            
            if not in_range:
                result.add_error(
                    field_name,
                    value,
                    f"must be in range {bracket[0]}{min_val}, {max_val}{bracket[1]}",
                    f"Use a value between {min_val} and {max_val}"
                )
            else:
                result.mark_validated(field_name)
        
        except (ValueError, TypeError) as e:
            result.add_error(
                field_name,
                value,
                f"must be a numeric value: {e}"
            )
        
        return result
    
    @staticmethod
    def validate_non_empty_string(
        value: Any,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> ValidationResult:
        """Валидация непустой строки"""
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error(
                field_name,
                value,
                f"must be a string, got {type(value).__name__}"
            )
            return result
        
        if not value or not value.strip():
            result.add_error(
                field_name,
                value,
                "cannot be empty",
                "Provide a non-empty string"
            )
            return result
        
        if min_length is not None and len(value) < min_length:
            result.add_error(
                field_name,
                value,
                f"must be at least {min_length} characters long",
                f"Use at least {min_length} characters"
            )
        
        if max_length is not None and len(value) > max_length:
            result.add_error(
                field_name,
                value,
                f"must be at most {max_length} characters long",
                f"Use at most {max_length} characters"
            )
        
        if result.is_valid:
            result.mark_validated(field_name)
        
        return result
    
    @staticmethod
    def validate_enum(
        value: Any,
        field_name: str,
        enum_class: Type[Enum]
    ) -> ValidationResult:
        """Валидация enum значения"""
        result = ValidationResult()
        
        if isinstance(value, enum_class):
            result.mark_validated(field_name)
            return result
        
        if isinstance(value, str):
            try:
                # Пробуем различные варианты
                for variant in [value, value.upper(), value.lower()]:
                    try:
                        enum_class(variant)
                        result.mark_validated(field_name)
                        return result
                    except ValueError:
                        continue
            except Exception:
                pass
        
        valid_values = [e.value for e in enum_class]
        result.add_error(
            field_name,
            value,
            f"must be one of {valid_values}",
            f"Use one of: {', '.join(valid_values)}"
        )
        
        return result


# ============================================================================
# NETWORK VALIDATORS
# ============================================================================

class NetworkValidators:
    """Валидаторы для сетевых параметров"""
    
    @staticmethod
    def validate_port(value: Any, field_name: str = "port") -> ValidationResult:
        """Валидация номера порта"""
        result = ValidationResult()
        
        try:
            port = int(value)
            
            if not 1 <= port <= 65535:
                result.add_error(
                    field_name,
                    value,
                    "must be between 1 and 65535",
                    "Use a valid port number (1-65535)"
                )
            else:
                result.mark_validated(field_name)
        
        except (ValueError, TypeError):
            result.add_error(
                field_name,
                value,
                "must be an integer",
                "Provide a numeric port value"
            )
        
        return result
    
    @staticmethod
    def validate_hostname(value: str, field_name: str = "host") -> ValidationResult:
        """Валидация hostname"""
        result = ValidationResult()
        
        if not value or not value.strip():
            result.add_error(field_name, value, "cannot be empty")
            return result
        
        # Проверка на IP адрес
        try:
            ip_address(value)
            result.mark_validated(field_name)
            return result
        except ValueError:
            pass
        
        # Проверка на hostname
        hostname_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        
        if not re.match(hostname_pattern, value):
            result.add_error(
                field_name,
                value,
                "invalid hostname format",
                "Use a valid hostname or IP address"
            )
        else:
            result.mark_validated(field_name)
        
        return result
    
    @staticmethod
    def validate_url(value: str, field_name: str = "url") -> ValidationResult:
        """Валидация URL"""
        result = ValidationResult()
        
        if not value or not value.strip():
            result.add_error(field_name, value, "cannot be empty")
            return result
        
        url_pattern = r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+$'
        
        if not re.match(url_pattern, value):
            result.add_error(
                field_name,
                value,
                "invalid URL format",
                "Use a valid URL with scheme (e.g., http://example.com)"
            )
        else:
            result.mark_validated(field_name)
        
        return result


# ============================================================================
# FILE SYSTEM VALIDATORS
# ============================================================================

class FileSystemValidators:
    """Валидаторы для файловой системы"""
    
    @staticmethod
    def validate_path(
        value: Any,
        field_name: str,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        must_be_readable: bool = False,
        must_be_writable: bool = False
    ) -> ValidationResult:
        """Валидация пути"""
        result = ValidationResult()
        
        if value is None:
            if must_exist:
                result.add_error(field_name, value, "path is required")
            return result
        
        try:
            path = Path(value) if not isinstance(value, Path) else value
            
            if must_exist and not path.exists():
                result.add_error(
                    field_name,
                    value,
                    f"path does not exist: {path}",
                    f"Create the path or use an existing one"
                )
                return result
            
            if must_be_file and path.exists() and not path.is_file():
                result.add_error(
                    field_name,
                    value,
                    "must be a file, not a directory"
                )
            
            if must_be_dir and path.exists() and not path.is_dir():
                result.add_error(
                    field_name,
                    value,
                    "must be a directory, not a file"
                )
            
            if must_be_readable and path.exists():
                if not os.access(path, os.R_OK):
                    result.add_error(
                        field_name,
                        value,
                        "path is not readable",
                        "Check file permissions"
                    )
            
            if must_be_writable and path.exists():
                if not os.access(path, os.W_OK):
                    result.add_error(
                        field_name,
                        value,
                        "path is not writable",
                        "Check file permissions"
                    )
            
            if result.is_valid:
                result.mark_validated(field_name)
        
        except Exception as e:
            result.add_error(
                field_name,
                value,
                f"invalid path: {e}"
            )
        
        return result


# ============================================================================
# DATABASE CONFIG VALIDATOR
# ============================================================================

class DatabaseConfigValidator:
    """
    Главный валидатор конфигурации БД
    
    Выполняет комплексную валидацию всех параметров конфигурации
    и проверяет связи между ними.
    """
    
    def __init__(self, config: Any):
        """
        Инициализация валидатора
        
        Args:
            config: Конфигурация для валидации
        """
        self.config = config
        self.basic_validators = BasicValidators()
        self.network_validators = NetworkValidators()
        self.fs_validators = FileSystemValidators()
    
    def validate_all(self) -> ValidationResult:
        """
        Полная валидация конфигурации
        
        Returns:
            Результат валидации
        """
        logger.info("Starting comprehensive configuration validation")
        
        result = ValidationResult()
        
        # Валидация основных параметров
        result.merge(self._validate_connection_params())
        
        # Валидация пула соединений
        result.merge(self._validate_pool_config())
        
        # Валидация SSL
        result.merge(self._validate_ssl_config())
        
        # Валидация таймаутов
        result.merge(self._validate_timeout_config())
        
        # Валидация retry
        result.merge(self._validate_retry_config())
        
        # Валидация мониторинга
        result.merge(self._validate_monitoring_config())
        
        # Валидация связей между параметрами
        result.merge(self._validate_relationships())
        
        logger.info(
            f"Validation complete: {result.get_summary()}"
        )
        
        return result
    
    def _validate_connection_params(self) -> ValidationResult:
        """Валидация параметров подключения"""
        result = ValidationResult()
        
        # Валидация engine
        result.merge(
            self.basic_validators.validate_enum(
                self.config.engine,
                'engine',
                self.config.engine.__class__
            )
        )
        
        # Валидация host
        result.merge(
            self.network_validators.validate_hostname(
                self.config.host,
                'host'
            )
        )
        
        # Валидация port
        result.merge(
            self.network_validators.validate_port(
                self.config.port,
                'port'
            )
        )
        
        # Валидация database
        result.merge(
            self.basic_validators.validate_non_empty_string(
                self.config.database,
                'database',
                min_length=1,
                max_length=255
            )
        )
        
        # Валидация user
        result.merge(
            self.basic_validators.validate_non_empty_string(
                self.config.user,
                'user',
                min_length=1,
                max_length=255
            )
        )
        
        # Валидация schema (для PostgreSQL)
        if hasattr(self.config, 'schema') and self.config.schema:
            result.merge(
                self.basic_validators.validate_non_empty_string(
                    self.config.schema,
                    'schema',
                    min_length=1,
                    max_length=255
                )
            )
        
        return result
    
    def _validate_pool_config(self) -> ValidationResult:
        """Валидация конфигурации пула"""
        result = ValidationResult()
        
        pool = self.config.pool
        
        # Валидация размеров
        result.merge(
            self.basic_validators.validate_positive(
                pool.min_size,
                'pool.min_size',
                min_value=1
            )
        )
        
        result.merge(
            self.basic_validators.validate_positive(
                pool.max_size,
                'pool.max_size',
                min_value=1
            )
        )
        
        # Проверка min <= max
        if pool.min_size > pool.max_size:
            result.add_error(
                'pool',
                f"min={pool.min_size}, max={pool.max_size}",
                "min_size cannot be greater than max_size",
                f"Set min_size <= {pool.max_size} or increase max_size"
            )
        
        # Валидация таймаутов
        result.merge(
            self.basic_validators.validate_positive(
                pool.timeout,
                'pool.timeout',
                min_value=0.1
            )
        )
        
        result.merge(
            self.basic_validators.validate_positive(
                pool.command_timeout,
                'pool.command_timeout',
                min_value=0.1
            )
        )
        
        return result
    
    def _validate_ssl_config(self) -> ValidationResult:
        """Валидация SSL конфигурации"""
        result = ValidationResult()
        
        ssl = self.config.ssl
        
        if not ssl.enabled:
            return result
        
        # Валидация mode
        result.merge(
            self.basic_validators.validate_enum(
                ssl.mode,
                'ssl.mode',
                ssl.mode.__class__
            )
        )
        
        # Валидация файлов сертификатов
        if ssl.ca_file:
            result.merge(
                self.fs_validators.validate_path(
                    ssl.ca_file,
                    'ssl.ca_file',
                    must_exist=True,
                    must_be_file=True,
                    must_be_readable=True
                )
            )
        
        if ssl.cert_file:
            result.merge(
                self.fs_validators.validate_path(
                    ssl.cert_file,
                    'ssl.cert_file',
                    must_exist=True,
                    must_be_file=True,
                    must_be_readable=True
                )
            )
        
        if ssl.key_file:
            result.merge(
                self.fs_validators.validate_path(
                    ssl.key_file,
                    'ssl.key_file',
                    must_exist=True,
                    must_be_file=True,
                    must_be_readable=True
                )
            )
        
        # Проверка пары cert-key
        if bool(ssl.cert_file) != bool(ssl.key_file):
            result.add_error(
                'ssl',
                'cert/key mismatch',
                "cert_file and key_file must both be set or both be None",
                "Provide both certificate and key files"
            )
        
        return result
    
    def _validate_timeout_config(self) -> ValidationResult:
        """Валидация конфигурации таймаутов"""
        result = ValidationResult()
        
        timeouts = self.config.timeouts
        
        # Валидация всех таймаутов
        timeout_fields = [
            ('connect_timeout', 0.1),
            ('query_timeout', 0.1),
            ('transaction_timeout', 0.1),
            ('lock_timeout', 0.1),
            ('statement_timeout', 0.1),
            ('idle_in_transaction_timeout', 0.1)
        ]
        
        for field, min_val in timeout_fields:
            result.merge(
                self.basic_validators.validate_positive(
                    getattr(timeouts, field),
                    f'timeouts.{field}',
                    min_value=min_val
                )
            )
        
        # Логические проверки
        if timeouts.query_timeout > timeouts.transaction_timeout:
            result.add_warning(
                'timeouts',
                f"query={timeouts.query_timeout}, transaction={timeouts.transaction_timeout}",
                "query_timeout is greater than transaction_timeout",
                "Consider setting query_timeout <= transaction_timeout"
            )
        
        return result
    
    def _validate_retry_config(self) -> ValidationResult:
        """Валидация конфигурации retry"""
        result = ValidationResult()
        
        retry = self.config.retry
        
        if not retry.enabled:
            return result
        
        # Валидация попыток
        result.merge(
            self.basic_validators.validate_positive(
                retry.max_attempts,
                'retry.max_attempts',
                min_value=1,
                max_value=100
            )
        )
        
        # Валидация задержек
        result.merge(
            self.basic_validators.validate_positive(
                retry.initial_delay,
                'retry.initial_delay',
                min_value=0.1
            )
        )
        
        result.merge(
            self.basic_validators.validate_positive(
                retry.max_delay,
                'retry.max_delay',
                min_value=0.1
            )
        )
        
        if retry.initial_delay > retry.max_delay:
            result.add_error(
                'retry',
                f"initial={retry.initial_delay}, max={retry.max_delay}",
                "initial_delay cannot be greater than max_delay",
                f"Set initial_delay <= {retry.max_delay}"
            )
        
        return result
    
    def _validate_monitoring_config(self) -> ValidationResult:
        """Валидация конфигурации мониторинга"""
        result = ValidationResult()
        
        monitoring = self.config.monitoring
        
        if not monitoring.enabled:
            return result
        
        # Валидация интервала
        result.merge(
            self.basic_validators.validate_positive(
                monitoring.interval_seconds,
                'monitoring.interval_seconds',
                min_value=10
            )
        )
        
        # Валидация порогов
        result.merge(
            self.basic_validators.validate_range(
                monitoring.slow_query_threshold_ms,
                'monitoring.slow_query_threshold_ms',
                1.0,
                3600000.0  # 1 hour max
            )
        )
        
        return result
    
    def _validate_relationships(self) -> ValidationResult:
        """Валидация связей между параметрами"""
        result = ValidationResult()
        
        # Проверка SSL для SQLite
        if str(self.config.engine.value) == 'sqlite' and self.config.ssl.enabled:
            result.add_warning(
                'ssl',
                'enabled for SQLite',
                "SQLite does not support SSL connections",
                "Disable SSL for SQLite or use a different engine"
            )
        
        # Проверка пула для SQLite
        if str(self.config.engine.value) == 'sqlite':
            if self.config.pool.max_size > 1:
                result.add_warning(
                    'pool',
                    f"max_size={self.config.pool.max_size} for SQLite",
                    "SQLite has limited connection pool support",
                    "Consider using max_size=1 for SQLite"
                )
        
        return result


__all__ = [
    'ValidationIssue',
    'ValidationResult',
    'BasicValidators',
    'NetworkValidators',
    'FileSystemValidators',
    'DatabaseConfigValidator'
]