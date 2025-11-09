"""
Database Configuration Loaders
Загрузчики конфигурации БД из различных источников
"""

import os
import logging
from typing import Optional, Dict, Any, TypeVar, Callable, Type
from pathlib import Path
from enum import Enum

from .base import DatabaseConfigBase
from .sub_configs import (
    PoolConfig,
    SSLConfig,
    TimeoutConfig,
    RetryConfig,
    MonitoringConfig
)
from .enums import DatabaseEngine, PoolStrategy, SSLMode
from .exceptions import (
    DatabaseConfigError,
    ValidationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# ENVIRONMENT VARIABLE PARSER
# ============================================================================

class EnvironmentVariableParser:
    """
    Парсер переменных окружения с типизацией
    
    Обеспечивает безопасное преобразование строковых значений
    из environment variables в типизированные значения Python.
    """
    
    @staticmethod
    def parse_bool(value: str, default: bool = False) -> bool:
        """
        Парсинг boolean значения
        
        Args:
            value: Строковое значение
            default: Значение по умолчанию
            
        Returns:
            Boolean значение
        """
        if not value:
            return default
        
        true_values = {'true', '1', 'yes', 'on', 'enabled', 'enable'}
        false_values = {'false', '0', 'no', 'off', 'disabled', 'disable'}
        
        value_lower = value.lower().strip()
        
        if value_lower in true_values:
            return True
        elif value_lower in false_values:
            return False
        else:
            logger.warning(
                f"Invalid boolean value: '{value}', using default: {default}"
            )
            return default
    
    @staticmethod
    def parse_int(
        value: str,
        default: int,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """
        Парсинг integer значения с валидацией диапазона
        
        Args:
            value: Строковое значение
            default: Значение по умолчанию
            min_value: Минимальное допустимое значение
            max_value: Максимальное допустимое значение
            
        Returns:
            Integer значение
        """
        if not value:
            return default
        
        try:
            parsed = int(value.strip())
            
            # Валидация минимума
            if min_value is not None and parsed < min_value:
                logger.warning(
                    f"Value {parsed} is less than minimum {min_value}, "
                    f"clamping to minimum"
                )
                return min_value
            
            # Валидация максимума
            if max_value is not None and parsed > max_value:
                logger.warning(
                    f"Value {parsed} is greater than maximum {max_value}, "
                    f"clamping to maximum"
                )
                return max_value
            
            return parsed
            
        except (ValueError, AttributeError) as e:
            logger.error(
                f"Failed to parse integer from '{value}': {e}, "
                f"using default: {default}"
            )
            return default
    
    @staticmethod
    def parse_float(
        value: str,
        default: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """
        Парсинг float значения с валидацией диапазона
        
        Args:
            value: Строковое значение
            default: Значение по умолчанию
            min_value: Минимальное допустимое значение
            max_value: Максимальное допустимое значение
            
        Returns:
            Float значение
        """
        if not value:
            return default
        
        try:
            parsed = float(value.strip())
            
            # Валидация минимума
            if min_value is not None and parsed < min_value:
                logger.warning(
                    f"Value {parsed} is less than minimum {min_value}, "
                    f"clamping to minimum"
                )
                return min_value
            
            # Валидация максимума
            if max_value is not None and parsed > max_value:
                logger.warning(
                    f"Value {parsed} is greater than maximum {max_value}, "
                    f"clamping to maximum"
                )
                return max_value
            
            return parsed
            
        except (ValueError, AttributeError) as e:
            logger.error(
                f"Failed to parse float from '{value}': {e}, "
                f"using default: {default}"
            )
            return default
    
    @staticmethod
    def parse_enum(
        value: str,
        enum_class: Type[Enum],
        default: Enum
    ) -> Enum:
        """
        Парсинг enum значения
        
        Args:
            value: Строковое значение
            enum_class: Класс Enum
            default: Значение по умолчанию
            
        Returns:
            Enum значение
        """
        if not value:
            return default
        
        try:
            # Пробуем различные варианты
            value_variants = [
                value.strip(),
                value.strip().upper(),
                value.strip().lower()
            ]
            
            for variant in value_variants:
                try:
                    return enum_class(variant)
                except ValueError:
                    continue
            
            # Если ни один вариант не подошёл
            valid_values = [e.value for e in enum_class]
            logger.warning(
                f"Invalid enum value '{value}' for {enum_class.__name__}, "
                f"valid values: {valid_values}, using default: {default.value}"
            )
            return default
            
        except Exception as e:
            logger.error(
                f"Failed to parse enum from '{value}': {e}, "
                f"using default: {default.value}"
            )
            return default
    
    @staticmethod
    def parse_path(value: str, must_exist: bool = False) -> Optional[Path]:
        """
        Парсинг пути к файлу
        
        Args:
            value: Строковое значение с путём
            must_exist: Файл должен существовать
            
        Returns:
            Path объект или None
        """
        if not value or not value.strip():
            return None
        
        try:
            path = Path(value.strip()).expanduser().resolve()
            
            if must_exist and not path.exists():
                logger.warning(f"Path does not exist: {path}")
                return None
            
            return path
            
        except Exception as e:
            logger.error(f"Failed to parse path from '{value}': {e}")
            return None
    
    @staticmethod
    def parse_list(
        value: str,
        separator: str = ',',
        item_parser: Optional[Callable[[str], Any]] = None
    ) -> list:
        """
        Парсинг списка значений
        
        Args:
            value: Строковое значение со списком
            separator: Разделитель элементов
            item_parser: Функция для парсинга каждого элемента
            
        Returns:
            Список значений
        """
        if not value or not value.strip():
            return []
        
        try:
            items = [item.strip() for item in value.split(separator) if item.strip()]
            
            if item_parser:
                parsed_items = []
                for item in items:
                    try:
                        parsed_items.append(item_parser(item))
                    except Exception as e:
                        logger.warning(f"Failed to parse list item '{item}': {e}")
                return parsed_items
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to parse list from '{value}': {e}")
            return []


# ============================================================================
# ENVIRONMENT LOADER
# ============================================================================

class EnvironmentLoader:
    """
    Загрузчик конфигурации из переменных окружения
    
    Предоставляет удобный API для чтения и парсинга
    environment variables с поддержкой префиксов.
    """
    
    def __init__(self, prefix: str = ''):
        """
        Инициализация загрузчика
        
        Args:
            prefix: Префикс для всех переменных окружения
        """
        self.prefix = prefix
        self.parser = EnvironmentVariableParser()
    
    def _make_key(self, key: str) -> str:
        """
        Создание полного ключа с префиксом
        
        Args:
            key: Базовый ключ
            
        Returns:
            Ключ с префиксом
        """
        return f"{self.prefix}{key}" if self.prefix else key
    
    def get_str(
        self,
        key: str,
        default: str = '',
        required: bool = False
    ) -> str:
        """
        Получение строкового значения
        
        Args:
            key: Ключ переменной
            default: Значение по умолчанию
            required: Обязательная переменная
            
        Returns:
            Строковое значение
            
        Raises:
            DatabaseConfigError: Если обязательная переменная не установлена
        """
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        
        if value is None:
            if required:
                raise DatabaseConfigError(
                    f"Required environment variable not set: {full_key}"
                )
            return default
        
        return value.strip()
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Получение boolean значения"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_bool(value, default) if value else default
    
    def get_int(
        self,
        key: str,
        default: int,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> int:
        """Получение integer значения"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_int(value, default, min_value, max_value) if value else default
    
    def get_float(
        self,
        key: str,
        default: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> float:
        """Получение float значения"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_float(value, default, min_value, max_value) if value else default
    
    def get_enum(
        self,
        key: str,
        enum_class: Type[Enum],
        default: Enum
    ) -> Enum:
        """Получение enum значения"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_enum(value, enum_class, default) if value else default
    
    def get_path(
        self,
        key: str,
        must_exist: bool = False
    ) -> Optional[Path]:
        """Получение пути к файлу"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_path(value, must_exist) if value else None
    
    def get_list(
        self,
        key: str,
        separator: str = ',',
        item_parser: Optional[Callable[[str], Any]] = None
    ) -> list:
        """Получение списка значений"""
        full_key = self._make_key(key)
        value = os.getenv(full_key)
        return self.parser.parse_list(value, separator, item_parser) if value else []
    
    def has_key(self, key: str) -> bool:
        """
        Проверка наличия переменной
        
        Args:
            key: Ключ переменной
            
        Returns:
            True если переменная установлена
        """
        full_key = self._make_key(key)
        return os.getenv(full_key) is not None


# ============================================================================
# DATABASE CONFIG LOADER
# ============================================================================

class DatabaseConfigLoader:
    """
    Загрузчик конфигурации базы данных
    
    Обеспечивает загрузку полной конфигурации БД из различных источников:
    - Переменные окружения
    - Словарь
    - URL строка подключения
    """
    
    def __init__(self, prefix: str = "DATABASE_"):
        """
        Инициализация загрузчика
        
        Args:
            prefix: Префикс для переменных окружения
        """
        self.prefix = prefix
        self.env_loader = EnvironmentLoader(prefix)
        logger.debug(f"DatabaseConfigLoader initialized with prefix: {prefix}")
    
    def load_from_env(self) -> DatabaseConfigBase:
        """
        Загрузка конфигурации из переменных окружения
        
        Returns:
            Полная конфигурация БД
        """
        logger.info(f"Loading database configuration from environment (prefix: {self.prefix})")
        
        try:
            # Загружаем основные параметры
            main_params = self._load_main_params()
            
            # Загружаем вложенные конфигурации
            pool_config = self._load_pool_config()
            ssl_config = self._load_ssl_config()
            timeout_config = self._load_timeout_config()
            retry_config = self._load_retry_config()
            monitoring_config = self._load_monitoring_config()
            
            # Собираем всё вместе
            config_dict = {
                **main_params,
                'pool': pool_config,
                'ssl': ssl_config,
                'timeouts': timeout_config,
                'retry': retry_config,
                'monitoring': monitoring_config
            }
            
            config = DatabaseConfigBase(**config_dict)
            logger.info(
                f"Database configuration loaded successfully: "
                f"{config.engine.value}://{config.host}:{config.port}/{config.database}"
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}", exc_info=True)
            raise DatabaseConfigError(f"Configuration loading failed: {e}")
    
    def _load_main_params(self) -> Dict[str, Any]:
        """Загрузка основных параметров подключения"""
        # Определяем движок
        engine_str = self.env_loader.get_str('ENGINE', 'postgresql')
        try:
            engine = DatabaseEngine(engine_str.lower())
        except ValueError:
            logger.warning(f"Invalid engine '{engine_str}', using postgresql")
            engine = DatabaseEngine.POSTGRESQL
        
        # Определяем порт по умолчанию
        default_port = engine.get_default_port()
        
        return {
            'engine': engine,
            'host': self.env_loader.get_str('HOST', 'localhost'),
            'port': self.env_loader.get_int('PORT', default_port, min_value=1, max_value=65535),
            'database': self.env_loader.get_str('NAME', 'mydb'),
            'user': self.env_loader.get_str('USER', 'postgres'),
            'password': self.env_loader.get_str('PASSWORD', ''),
            'schema': self.env_loader.get_str('SCHEMA', 'public'),
            'application_name': self.env_loader.get_str('APP_NAME', 'crypto_monitor'),
            'echo_queries': self.env_loader.get_bool('ECHO_QUERIES', False),
            'log_slow_queries': self.env_loader.get_bool('LOG_SLOW_QUERIES', True),
            'auto_commit': self.env_loader.get_bool('AUTO_COMMIT', False),
            'enable_query_cache': self.env_loader.get_bool('ENABLE_QUERY_CACHE', True),
            'enable_prepared_statements': self.env_loader.get_bool('ENABLE_PREPARED_STATEMENTS', True),
            'encoding': self.env_loader.get_str('ENCODING', 'utf-8'),
            'timezone': self.env_loader.get_str('TIMEZONE', 'UTC'),
            'max_overflow': self.env_loader.get_int('MAX_OVERFLOW', 10, min_value=0)
        }
    
    def _load_pool_config(self) -> PoolConfig:
        """Загрузка конфигурации пула соединений"""
        pool_loader = EnvironmentLoader(f"{self.prefix}POOL_")
        
        return PoolConfig(
            min_size=pool_loader.get_int('MIN_SIZE', 5, min_value=1),
            max_size=pool_loader.get_int('MAX_SIZE', 20, min_value=1),
            max_queries=pool_loader.get_int('MAX_QUERIES', 50000, min_value=1),
            max_inactive_connection_lifetime=pool_loader.get_float(
                'MAX_INACTIVE_LIFETIME', 300.0, min_value=1.0
            ),
            timeout=pool_loader.get_float('TIMEOUT', 30.0, min_value=0.1),
            command_timeout=pool_loader.get_float('COMMAND_TIMEOUT', 60.0, min_value=0.1),
            strategy=pool_loader.get_enum('STRATEGY', PoolStrategy, PoolStrategy.LIFO),
            setup_timeout=pool_loader.get_float('SETUP_TIMEOUT', 10.0, min_value=0.1),
            max_overflow=pool_loader.get_int('MAX_OVERFLOW', 10, min_value=0),
            pool_recycle=pool_loader.get_int('RECYCLE', 3600, min_value=60)
        )
    
    def _load_ssl_config(self) -> SSLConfig:
        """Загрузка SSL конфигурации"""
        ssl_loader = EnvironmentLoader(f"{self.prefix}SSL_")
        
        return SSLConfig(
            enabled=ssl_loader.get_bool('ENABLED', False),
            mode=ssl_loader.get_enum('MODE', SSLMode, SSLMode.PREFER),
            ca_file=ssl_loader.get_path('CA_FILE', must_exist=False),
            cert_file=ssl_loader.get_path('CERT_FILE', must_exist=False),
            key_file=ssl_loader.get_path('KEY_FILE', must_exist=False),
            verify_hostname=ssl_loader.get_bool('VERIFY_HOSTNAME', True),
            ssl_min_protocol_version=ssl_loader.get_str('MIN_PROTOCOL_VERSION', 'TLSv1.2'),
            ssl_ciphers=ssl_loader.get_str('CIPHERS', ''),
            ssl_check_hostname=ssl_loader.get_bool('CHECK_HOSTNAME', True)
        )
    
    def _load_timeout_config(self) -> TimeoutConfig:
        """Загрузка конфигурации таймаутов"""
        timeout_loader = EnvironmentLoader(f"{self.prefix}TIMEOUT_")
        
        return TimeoutConfig(
            connect_timeout=timeout_loader.get_float('CONNECT', 30.0, min_value=0.1),
            query_timeout=timeout_loader.get_float('QUERY', 60.0, min_value=0.1),
            transaction_timeout=timeout_loader.get_float('TRANSACTION', 300.0, min_value=0.1),
            lock_timeout=timeout_loader.get_float('LOCK', 30.0, min_value=0.1),
            statement_timeout=timeout_loader.get_float('STATEMENT', 60.0, min_value=0.1),
            idle_in_transaction_timeout=timeout_loader.get_float(
                'IDLE_IN_TRANSACTION', 600.0, min_value=0.1
            ),
            healthcheck_timeout=timeout_loader.get_float('HEALTHCHECK', 5.0, min_value=0.1),
            backup_timeout=timeout_loader.get_float('BACKUP', 3600.0, min_value=1.0)
        )
    
    def _load_retry_config(self) -> RetryConfig:
        """Загрузка конфигурации повторных попыток"""
        retry_loader = EnvironmentLoader(f"{self.prefix}RETRY_")
        
        return RetryConfig(
            enabled=retry_loader.get_bool('ENABLED', True),
            max_attempts=retry_loader.get_int('MAX_ATTEMPTS', 3, min_value=1),
            initial_delay=retry_loader.get_float('INITIAL_DELAY', 1.0, min_value=0.1),
            max_delay=retry_loader.get_float('MAX_DELAY', 30.0, min_value=0.1),
            exponential_base=retry_loader.get_float('EXPONENTIAL_BASE', 2.0, min_value=1.0),
            jitter=retry_loader.get_bool('JITTER', True),
            retry_on_timeout=retry_loader.get_bool('ON_TIMEOUT', True),
            retry_on_connection_error=retry_loader.get_bool('ON_CONNECTION_ERROR', True),
            backoff_multiplier=retry_loader.get_float('BACKOFF_MULTIPLIER', 1.0, min_value=0.1)
        )
    
    def _load_monitoring_config(self) -> MonitoringConfig:
        """Загрузка конфигурации мониторинга"""
        mon_loader = EnvironmentLoader(f"{self.prefix}MONITORING_")
        
        return MonitoringConfig(
            enabled=mon_loader.get_bool('ENABLED', True),
            interval_seconds=mon_loader.get_int('INTERVAL', 60, min_value=10),
            collect_query_stats=mon_loader.get_bool('COLLECT_QUERY_STATS', True),
            collect_table_stats=mon_loader.get_bool('COLLECT_TABLE_STATS', True),
            collect_index_stats=mon_loader.get_bool('COLLECT_INDEX_STATS', True),
            collect_connection_stats=mon_loader.get_bool('COLLECT_CONNECTION_STATS', True),
            slow_query_threshold_ms=mon_loader.get_float(
                'SLOW_QUERY_THRESHOLD_MS', 1000.0, min_value=1.0
            ),
            alert_on_connection_errors=mon_loader.get_bool('ALERT_ON_CONNECTION_ERRORS', True),
            alert_on_slow_queries=mon_loader.get_bool('ALERT_ON_SLOW_QUERIES', True),
            alert_on_high_cpu=mon_loader.get_bool('ALERT_ON_HIGH_CPU', True),
            alert_on_high_memory=mon_loader.get_bool('ALERT_ON_HIGH_MEMORY', True),
            metrics_retention_hours=mon_loader.get_int('METRICS_RETENTION_HOURS', 24, min_value=1),
            statistics_sample_rate=mon_loader.get_float(
                'STATISTICS_SAMPLE_RATE', 1.0, min_value=0.0, max_value=1.0
            ),
            enable_query_logging=mon_loader.get_bool('ENABLE_QUERY_LOGGING', False),
            max_stored_queries=mon_loader.get_int('MAX_STORED_QUERIES', 1000, min_value=10),
            cpu_threshold_percent=mon_loader.get_float(
                'CPU_THRESHOLD_PERCENT', 80.0, min_value=0.0, max_value=100.0
            ),
            memory_threshold_percent=mon_loader.get_float(
                'MEMORY_THRESHOLD_PERCENT', 85.0, min_value=0.0, max_value=100.0
            ),
            connection_pool_threshold_percent=mon_loader.get_float(
                'POOL_THRESHOLD_PERCENT', 90.0, min_value=0.0, max_value=100.0
            )
        )
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> DatabaseConfigBase:
        """
        Загрузка конфигурации из словаря
        
        Args:
            config_dict: Словарь с параметрами конфигурации
            
        Returns:
            Конфигурация БД
        """
        logger.info("Loading database configuration from dictionary")
        
        try:
            config = DatabaseConfigBase(**config_dict)
            logger.info("Database configuration loaded from dictionary successfully")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration from dict: {e}", exc_info=True)
            raise DatabaseConfigError(f"Configuration loading from dict failed: {e}")
    
    def load_from_url(self, url: str, **overrides) -> DatabaseConfigBase:
        """
        Загрузка конфигурации из URL строки подключения
        
        Args:
            url: URL строка подключения
            **overrides: Параметры для переопределения
            
        Returns:
            Конфигурация БД
        """
        logger.info(f"Loading database configuration from URL")
        
        try:
            config = DatabaseConfigBase.from_url(url, **overrides)
            logger.info("Database configuration loaded from URL successfully")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration from URL: {e}", exc_info=True)
            raise DatabaseConfigError(f"Configuration loading from URL failed: {e}")


__all__ = [
    'EnvironmentVariableParser',
    'EnvironmentLoader',
    'DatabaseConfigLoader'
]