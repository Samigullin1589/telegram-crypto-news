"""
Database Sub-Configurations
Вложенные конфигурации для различных аспектов работы БД
"""

import os
import random
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from .base_classes import BaseConfig, ValidationMixin
from .enums import PoolStrategy, SSLMode
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# POOL CONFIGURATION
# ============================================================================

@dataclass
class PoolConfig(BaseConfig, ValidationMixin):
    """
    Конфигурация пула соединений к БД
    
    Управляет параметрами пула соединений для эффективного
    использования ресурсов и оптимизации производительности.
    
    Attributes:
        min_size: Минимальное количество соединений в пуле
        max_size: Максимальное количество соединений в пуле
        max_queries: Максимум запросов перед переподключением
        max_inactive_connection_lifetime: Время жизни неактивного соединения (сек)
        timeout: Таймаут получения соединения из пула (сек)
        command_timeout: Таймаут выполнения команды (сек)
        strategy: Стратегия управления пулом (LIFO/FIFO)
    """
    
    min_size: int = 5
    max_size: int = 20
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0
    timeout: float = 30.0
    command_timeout: float = 60.0
    strategy: PoolStrategy = PoolStrategy.LIFO
    
    # Дополнительные параметры
    setup_timeout: float = 10.0
    max_overflow: int = 10
    pool_recycle: int = 3600
    
    def validate(self) -> bool:
        """
        Валидация параметров пула соединений
        
        Returns:
            True если все параметры корректны
            
        Raises:
            ValidationError: При некорректных параметрах
        """
        # Валидация размеров пула
        self.validate_positive_number(self.min_size, "min_size", min_value=1)
        self.validate_positive_number(self.max_size, "max_size", min_value=1)
        
        if self.max_size < self.min_size:
            raise ValidationError(
                f"max_size ({self.max_size}) must be >= min_size ({self.min_size})"
            )
        
        # Валидация количества запросов
        self.validate_positive_number(
            self.max_queries, 
            "max_queries", 
            min_value=1
        )
        
        # Валидация таймаутов
        self.validate_positive_number(
            self.max_inactive_connection_lifetime,
            "max_inactive_connection_lifetime",
            min_value=1.0
        )
        
        self.validate_positive_number(
            self.timeout,
            "timeout",
            min_value=0.1
        )
        
        self.validate_positive_number(
            self.command_timeout,
            "command_timeout",
            min_value=0.1
        )
        
        self.validate_positive_number(
            self.setup_timeout,
            "setup_timeout",
            min_value=0.1
        )
        
        # Валидация overflow
        self.validate_positive_number(
            self.max_overflow,
            "max_overflow",
            min_value=0,
            allow_zero=True
        )
        
        # Валидация recycle
        self.validate_positive_number(
            self.pool_recycle,
            "pool_recycle",
            min_value=60
        )
        
        return True
    
    def get_effective_max_connections(self) -> int:
        """
        Получение эффективного максимума соединений
        
        Returns:
            Максимальное количество соединений включая overflow
        """
        return self.max_size + self.max_overflow
    
    def get_pool_utilization_thresholds(self) -> Dict[str, float]:
        """
        Получение порогов использования пула для мониторинга
        
        Returns:
            Словарь с порогами (warning, critical)
        """
        return {
            'warning': 0.7,  # 70% заполнения
            'critical': 0.9,  # 90% заполнения
            'max_connections': self.get_effective_max_connections()
        }
    
    def should_recycle_connection(
        self,
        connection_age: float,
        queries_executed: int
    ) -> bool:
        """
        Проверка необходимости переподключения
        
        Args:
            connection_age: Возраст соединения в секундах
            queries_executed: Количество выполненных запросов
            
        Returns:
            True если соединение нужно переподключить
        """
        # Переподключение по возрасту
        if connection_age >= self.pool_recycle:
            return True
        
        # Переподключение по количеству запросов
        if queries_executed >= self.max_queries:
            return True
        
        return False
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_POOL_") -> "PoolConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс переменных окружения
            
        Returns:
            Экземпляр PoolConfig
        """
        return cls(
            min_size=int(os.getenv(f'{prefix}MIN_SIZE', '5')),
            max_size=int(os.getenv(f'{prefix}MAX_SIZE', '20')),
            max_queries=int(os.getenv(f'{prefix}MAX_QUERIES', '50000')),
            max_inactive_connection_lifetime=float(
                os.getenv(f'{prefix}MAX_INACTIVE_LIFETIME', '300.0')
            ),
            timeout=float(os.getenv(f'{prefix}TIMEOUT', '30.0')),
            command_timeout=float(os.getenv(f'{prefix}COMMAND_TIMEOUT', '60.0')),
            strategy=PoolStrategy(os.getenv(f'{prefix}STRATEGY', 'lifo')),
            setup_timeout=float(os.getenv(f'{prefix}SETUP_TIMEOUT', '10.0')),
            max_overflow=int(os.getenv(f'{prefix}MAX_OVERFLOW', '10')),
            pool_recycle=int(os.getenv(f'{prefix}RECYCLE', '3600'))
        )


# ============================================================================
# SSL CONFIGURATION
# ============================================================================

@dataclass
class SSLConfig(BaseConfig, ValidationMixin):
    """
    Конфигурация SSL подключения к БД
    
    Управляет параметрами защищённого соединения с базой данных,
    включая сертификаты и режимы проверки.
    
    Attributes:
        enabled: Включить SSL
        mode: Режим SSL (disable/allow/prefer/require/verify-ca/verify-full)
        ca_file: Путь к файлу CA сертификата
        cert_file: Путь к файлу клиентского сертификата
        key_file: Путь к файлу приватного ключа
        verify_hostname: Проверять hostname сервера
    """
    
    enabled: bool = False
    mode: SSLMode = SSLMode.PREFER
    ca_file: Optional[Path] = None
    cert_file: Optional[Path] = None
    key_file: Optional[Path] = None
    verify_hostname: bool = True
    
    # Дополнительные параметры
    ssl_min_protocol_version: str = "TLSv1.2"
    ssl_ciphers: Optional[str] = None
    ssl_check_hostname: bool = True
    
    def validate(self) -> bool:
        """
        Валидация SSL конфигурации
        
        Returns:
            True если конфигурация корректна
            
        Raises:
            ValidationError: При некорректной конфигурации
        """
        if not self.enabled:
            logger.debug("SSL is disabled, skipping validation")
            return True
        
        # Проверка режима SSL
        if self.mode == SSLMode.DISABLE:
            logger.warning("SSL enabled but mode is DISABLE - this is contradictory")
        
        # Для режимов с проверкой CA нужен CA файл
        if self.mode.requires_ca_file():
            if not self.ca_file:
                raise ValidationError(
                    f"SSL mode {self.mode.value} requires ca_file to be specified"
                )
            
            self.validate_file_path(
                self.ca_file,
                "ca_file",
                must_exist=True,
                required=True
            )
        
        # Проверка пары сертификат-ключ
        if self.cert_file and not self.key_file:
            raise ValidationError(
                "SSL key_file is required when cert_file is specified"
            )
        
        if self.key_file and not self.cert_file:
            raise ValidationError(
                "SSL cert_file is required when key_file is specified"
            )
        
        # Проверка существования файлов сертификатов
        if self.cert_file:
            self.validate_file_path(
                self.cert_file,
                "cert_file",
                must_exist=True
            )
        
        if self.key_file:
            self.validate_file_path(
                self.key_file,
                "key_file",
                must_exist=True
            )
        
        # Проверка версии протокола
        valid_protocols = ['TLSv1', 'TLSv1.1', 'TLSv1.2', 'TLSv1.3']
        if self.ssl_min_protocol_version not in valid_protocols:
            logger.warning(
                f"Unusual SSL protocol version: {self.ssl_min_protocol_version}"
            )
        
        return True
    
    def get_security_level(self) -> int:
        """
        Получение уровня безопасности конфигурации (0-5)
        
        Returns:
            Числовой уровень безопасности
        """
        if not self.enabled:
            return 0
        
        return self.mode.get_security_level()
    
    def is_secure(self) -> bool:
        """
        Проверка безопасности конфигурации
        
        Returns:
            True если конфигурация считается безопасной
        """
        return self.enabled and self.get_security_level() >= 3
    
    def get_ssl_context_params(self) -> Dict[str, Any]:
        """
        Получение параметров для создания SSL контекста
        
        Returns:
            Словарь параметров SSL контекста
        """
        if not self.enabled:
            return {}
        
        params = {
            'ssl_mode': self.mode.value,
            'verify_hostname': self.verify_hostname,
            'check_hostname': self.ssl_check_hostname,
            'min_protocol_version': self.ssl_min_protocol_version
        }
        
        if self.ca_file:
            params['cafile'] = str(self.ca_file)
        
        if self.cert_file:
            params['certfile'] = str(self.cert_file)
        
        if self.key_file:
            params['keyfile'] = str(self.key_file)
        
        if self.ssl_ciphers:
            params['ciphers'] = self.ssl_ciphers
        
        return params
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_SSL_") -> "SSLConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс переменных окружения
            
        Returns:
            Экземпляр SSLConfig
        """
        ca_file_str = os.getenv(f'{prefix}CA_FILE')
        cert_file_str = os.getenv(f'{prefix}CERT_FILE')
        key_file_str = os.getenv(f'{prefix}KEY_FILE')
        
        return cls(
            enabled=os.getenv(f'{prefix}ENABLED', 'false').lower() == 'true',
            mode=SSLMode(os.getenv(f'{prefix}MODE', 'prefer')),
            ca_file=Path(ca_file_str) if ca_file_str else None,
            cert_file=Path(cert_file_str) if cert_file_str else None,
            key_file=Path(key_file_str) if key_file_str else None,
            verify_hostname=os.getenv(f'{prefix}VERIFY_HOSTNAME', 'true').lower() == 'true',
            ssl_min_protocol_version=os.getenv(f'{prefix}MIN_PROTOCOL_VERSION', 'TLSv1.2'),
            ssl_ciphers=os.getenv(f'{prefix}CIPHERS'),
            ssl_check_hostname=os.getenv(f'{prefix}CHECK_HOSTNAME', 'true').lower() == 'true'
        )


# ============================================================================
# TIMEOUT CONFIGURATION
# ============================================================================

@dataclass
class TimeoutConfig(BaseConfig, ValidationMixin):
    """
    Конфигурация таймаутов для операций БД
    
    Управляет различными таймаутами для предотвращения зависаний
    и контроля времени выполнения операций.
    
    Attributes:
        connect_timeout: Таймаут подключения к БД (сек)
        query_timeout: Таймаут выполнения запроса (сек)
        transaction_timeout: Таймаут транзакции (сек)
        lock_timeout: Таймаут ожидания блокировки (сек)
        statement_timeout: Таймаут выполнения statement (сек)
        idle_in_transaction_timeout: Таймаут простоя в транзакции (сек)
    """
    
    connect_timeout: float = 30.0
    query_timeout: float = 60.0
    transaction_timeout: float = 300.0
    lock_timeout: float = 30.0
    statement_timeout: float = 60.0
    idle_in_transaction_timeout: float = 600.0
    
    # Дополнительные таймауты
    healthcheck_timeout: float = 5.0
    backup_timeout: float = 3600.0
    
    def validate(self) -> bool:
        """
        Валидация таймаутов
        
        Returns:
            True если все таймауты корректны
            
        Raises:
            ValidationError: При некорректных значениях
        """
        timeouts = {
            'connect_timeout': self.connect_timeout,
            'query_timeout': self.query_timeout,
            'transaction_timeout': self.transaction_timeout,
            'lock_timeout': self.lock_timeout,
            'statement_timeout': self.statement_timeout,
            'idle_in_transaction_timeout': self.idle_in_transaction_timeout,
            'healthcheck_timeout': self.healthcheck_timeout,
            'backup_timeout': self.backup_timeout
        }
        
        for timeout_name, timeout_value in timeouts.items():
            self.validate_positive_number(
                timeout_value,
                timeout_name,
                min_value=0.1
            )
        
        # Логические проверки
        if self.query_timeout > self.transaction_timeout:
            logger.warning(
                f"query_timeout ({self.query_timeout}) is greater than "
                f"transaction_timeout ({self.transaction_timeout})"
            )
        
        if self.statement_timeout > self.transaction_timeout:
            logger.warning(
                f"statement_timeout ({self.statement_timeout}) is greater than "
                f"transaction_timeout ({self.transaction_timeout})"
            )
        
        return True
    
    def get_timeout_for_operation(self, operation_type: str) -> float:
        """
        Получение таймаута для типа операции
        
        Args:
            operation_type: Тип операции (connect/query/transaction/etc)
            
        Returns:
            Значение таймаута в секундах
        """
        timeout_map = {
            'connect': self.connect_timeout,
            'query': self.query_timeout,
            'transaction': self.transaction_timeout,
            'lock': self.lock_timeout,
            'statement': self.statement_timeout,
            'idle': self.idle_in_transaction_timeout,
            'healthcheck': self.healthcheck_timeout,
            'backup': self.backup_timeout
        }
        
        return timeout_map.get(operation_type, self.query_timeout)
    
    def get_postgresql_settings(self) -> Dict[str, str]:
        """
        Получение настроек таймаутов для PostgreSQL
        
        Returns:
            Словарь с настройками для SET команд
        """
        return {
            'statement_timeout': f'{int(self.statement_timeout * 1000)}ms',
            'lock_timeout': f'{int(self.lock_timeout * 1000)}ms',
            'idle_in_transaction_session_timeout': f'{int(self.idle_in_transaction_timeout * 1000)}ms'
        }
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_TIMEOUT_") -> "TimeoutConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс переменных окружения
            
        Returns:
            Экземпляр TimeoutConfig
        """
        return cls(
            connect_timeout=float(os.getenv(f'{prefix}CONNECT', '30.0')),
            query_timeout=float(os.getenv(f'{prefix}QUERY', '60.0')),
            transaction_timeout=float(os.getenv(f'{prefix}TRANSACTION', '300.0')),
            lock_timeout=float(os.getenv(f'{prefix}LOCK', '30.0')),
            statement_timeout=float(os.getenv(f'{prefix}STATEMENT', '60.0')),
            idle_in_transaction_timeout=float(os.getenv(f'{prefix}IDLE_IN_TRANSACTION', '600.0')),
            healthcheck_timeout=float(os.getenv(f'{prefix}HEALTHCHECK', '5.0')),
            backup_timeout=float(os.getenv(f'{prefix}BACKUP', '3600.0'))
        )


# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

@dataclass
class RetryConfig(BaseConfig, ValidationMixin):
    """
    Конфигурация политики повторных попыток при ошибках
    
    Управляет стратегией повторных попыток выполнения операций
    при временных сбоях.
    
    Attributes:
        enabled: Включить повторные попытки
        max_attempts: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками (сек)
        max_delay: Максимальная задержка между попытками (сек)
        exponential_base: База для экспоненциального роста задержки
        jitter: Добавлять случайность к задержкам
    """
    
    enabled: bool = True
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Дополнительные параметры
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    backoff_multiplier: float = 1.0
    
    def validate(self) -> bool:
        """
        Валидация retry конфигурации
        
        Returns:
            True если конфигурация корректна
            
        Raises:
            ValidationError: При некорректных значениях
        """
        if not self.enabled:
            logger.debug("Retry is disabled, skipping validation")
            return True
        
        # Валидация количества попыток
        self.validate_positive_number(
            self.max_attempts,
            "max_attempts",
            min_value=1
        )
        
        # Валидация задержек
        self.validate_positive_number(
            self.initial_delay,
            "initial_delay",
            min_value=0.1
        )
        
        self.validate_positive_number(
            self.max_delay,
            "max_delay",
            min_value=0.1
        )
        
        if self.max_delay < self.initial_delay:
            raise ValidationError(
                f"max_delay ({self.max_delay}) must be >= "
                f"initial_delay ({self.initial_delay})"
            )
        
        # Валидация экспоненциальной базы
        if self.exponential_base < 1.0:
            raise ValidationError(
                f"exponential_base must be >= 1.0, got {self.exponential_base}"
            )
        
        # Валидация multiplier
        self.validate_positive_number(
            self.backoff_multiplier,
            "backoff_multiplier",
            min_value=0.1
        )
        
        return True
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Вычисление задержки для конкретной попытки
        
        Args:
            attempt: Номер попытки (начиная с 0)
            
        Returns:
            Задержка в секундах
        """
        if not self.enabled or attempt < 0:
            return 0.0
        
        # Экспоненциальная задержка с ограничением
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Применяем multiplier
        delay *= self.backoff_multiplier
        
        # Добавляем jitter для избежания thundering herd problem
        if self.jitter:
            jitter_factor = 0.5 + random.random() * 0.5  # От 0.5 до 1.0
            delay *= jitter_factor
        
        return delay
    
    def get_retry_schedule(self) -> list[float]:
        """
        Получение полного расписания задержек для всех попыток
        
        Returns:
            Список задержек для каждой попытки
        """
        return [
            self.calculate_delay(attempt)
            for attempt in range(self.max_attempts)
        ]
    
    def get_total_max_time(self) -> float:
        """
        Получение максимального времени всех попыток
        
        Returns:
            Сумма всех задержек в секундах
        """
        return sum(self.get_retry_schedule())
    
    def should_retry_error(self, error_type: str) -> bool:
        """
        Проверка необходимости повтора для типа ошибки
        
        Args:
            error_type: Тип ошибки (timeout/connection/etc)
            
        Returns:
            True если нужно повторить попытку
        """
        if not self.enabled:
            return False
        
        retry_map = {
            'timeout': self.retry_on_timeout,
            'connection': self.retry_on_connection_error,
            'connection_error': self.retry_on_connection_error
        }
        
        return retry_map.get(error_type, False)
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_RETRY_") -> "RetryConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс переменных окружения
            
        Returns:
            Экземпляр RetryConfig
        """
        return cls(
            enabled=os.getenv(f'{prefix}ENABLED', 'true').lower() == 'true',
            max_attempts=int(os.getenv(f'{prefix}MAX_ATTEMPTS', '3')),
            initial_delay=float(os.getenv(f'{prefix}INITIAL_DELAY', '1.0')),
            max_delay=float(os.getenv(f'{prefix}MAX_DELAY', '30.0')),
            exponential_base=float(os.getenv(f'{prefix}EXPONENTIAL_BASE', '2.0')),
            jitter=os.getenv(f'{prefix}JITTER', 'true').lower() == 'true',
            retry_on_timeout=os.getenv(f'{prefix}ON_TIMEOUT', 'true').lower() == 'true',
            retry_on_connection_error=os.getenv(f'{prefix}ON_CONNECTION_ERROR', 'true').lower() == 'true',
            backoff_multiplier=float(os.getenv(f'{prefix}BACKOFF_MULTIPLIER', '1.0'))
        )


# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================

@dataclass
class MonitoringConfig(BaseConfig, ValidationMixin):
    """
    Конфигурация системы мониторинга БД
    
    Управляет сбором метрик, статистики и оповещениями о состоянии БД.
    
    Attributes:
        enabled: Включить мониторинг
        interval_seconds: Интервал сбора метрик (сек)
        collect_query_stats: Собирать статистику запросов
        collect_table_stats: Собирать статистику таблиц
        collect_index_stats: Собирать статистику индексов
        collect_connection_stats: Собирать статистику соединений
        slow_query_threshold_ms: Порог медленного запроса (мс)
        alert_on_connection_errors: Оповещать об ошибках подключения
        alert_on_slow_queries: Оповещать о медленных запросах
        alert_on_high_cpu: Оповещать о высокой нагрузке CPU
        alert_on_high_memory: Оповещать о высоком использовании памяти
    """
    
    enabled: bool = True
    interval_seconds: int = 60
    collect_query_stats: bool = True
    collect_table_stats: bool = True
    collect_index_stats: bool = True
    collect_connection_stats: bool = True
    slow_query_threshold_ms: float = 1000.0
    alert_on_connection_errors: bool = True
    alert_on_slow_queries: bool = True
    alert_on_high_cpu: bool = True
    alert_on_high_memory: bool = True
    
    # Дополнительные параметры
    metrics_retention_hours: int = 24
    statistics_sample_rate: float = 1.0
    enable_query_logging: bool = False
    max_stored_queries: int = 1000
    
    # Пороги для алертов
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    connection_pool_threshold_percent: float = 90.0
    
    def validate(self) -> bool:
        """
        Валидация мониторинга
        
        Returns:
            True если конфигурация корректна
            
        Raises:
            ValidationError: При некорректных значениях
        """
        if not self.enabled:
            logger.debug("Monitoring is disabled, skipping validation")
            return True
        
        # Валидация интервала
        if self.interval_seconds < 10:
            raise ValidationError(
                f"monitoring interval_seconds must be >= 10, got {self.interval_seconds}"
            )
        
        # Валидация порога медленных запросов
        self.validate_positive_number(
            self.slow_query_threshold_ms,
            "slow_query_threshold_ms",
            min_value=1.0
        )
        
        # Валидация retention
        self.validate_positive_number(
            self.metrics_retention_hours,
            "metrics_retention_hours",
            min_value=1
        )
        
        # Валидация sample rate
        if not 0.0 < self.statistics_sample_rate <= 1.0:
            raise ValidationError(
                f"statistics_sample_rate must be between 0.0 and 1.0, "
                f"got {self.statistics_sample_rate}"
            )
        
        # Валидация max_stored_queries
        self.validate_positive_number(
            self.max_stored_queries,
            "max_stored_queries",
            min_value=10
        )
        
        # Валидация порогов
        thresholds = {
            'cpu_threshold_percent': self.cpu_threshold_percent,
            'memory_threshold_percent': self.memory_threshold_percent,
            'connection_pool_threshold_percent': self.connection_pool_threshold_percent
        }
        
        for threshold_name, threshold_value in thresholds.items():
            if not 0.0 < threshold_value <= 100.0:
                raise ValidationError(
                    f"{threshold_name} must be between 0.0 and 100.0, "
                    f"got {threshold_value}"
                )
        
        return True
    
    def get_collection_flags(self) -> Dict[str, bool]:
        """
        Получение флагов сбора статистики
        
        Returns:
            Словарь с флагами всех типов сбора
        """
        return {
            'queries': self.collect_query_stats,
            'tables': self.collect_table_stats,
            'indexes': self.collect_index_stats,
            'connections': self.collect_connection_stats
        }
    
    def get_alert_flags(self) -> Dict[str, bool]:
        """
        Получение флагов оповещений
        
        Returns:
            Словарь с флагами всех типов оповещений
        """
        return {
            'connection_errors': self.alert_on_connection_errors,
            'slow_queries': self.alert_on_slow_queries,
            'high_cpu': self.alert_on_high_cpu,
            'high_memory': self.alert_on_high_memory
        }
    
    def is_query_slow(self, execution_time_ms: float) -> bool:
        """
        Проверка является ли запрос медленным
        
        Args:
            execution_time_ms: Время выполнения в миллисекундах
            
        Returns:
            True если запрос считается медленным
        """
        return execution_time_ms >= self.slow_query_threshold_ms
    
    def should_alert_on_metric(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: Optional[float] = None
    ) -> bool:
        """
        Проверка необходимости оповещения по метрике
        
        Args:
            metric_name: Имя метрики
            current_value: Текущее значение
            threshold_value: Пороговое значение (опционально)
            
        Returns:
            True если нужно создать оповещение
        """
        if not self.enabled:
            return False
        
        # Получаем порог по умолчанию если не передан
        if threshold_value is None:
            threshold_map = {
                'cpu_usage': self.cpu_threshold_percent,
                'memory_usage': self.memory_threshold_percent,
                'pool_usage': self.connection_pool_threshold_percent
            }
            threshold_value = threshold_map.get(metric_name, 100.0)
        
        return current_value >= threshold_value
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_MONITORING_") -> "MonitoringConfig":
        """
        Создание конфигурации из environment variables
        
        Args:
            prefix: Префикс переменных окружения
            
        Returns:
            Экземпляр MonitoringConfig
        """
        return cls(
            enabled=os.getenv(f'{prefix}ENABLED', 'true').lower() == 'true',
            interval_seconds=int(os.getenv(f'{prefix}INTERVAL', '60')),
            collect_query_stats=os.getenv(f'{prefix}COLLECT_QUERY_STATS', 'true').lower() == 'true',
            collect_table_stats=os.getenv(f'{prefix}COLLECT_TABLE_STATS', 'true').lower() == 'true',
            collect_index_stats=os.getenv(f'{prefix}COLLECT_INDEX_STATS', 'true').lower() == 'true',
            collect_connection_stats=os.getenv(f'{prefix}COLLECT_CONNECTION_STATS', 'true').lower() == 'true',
            slow_query_threshold_ms=float(os.getenv(f'{prefix}SLOW_QUERY_THRESHOLD_MS', '1000.0')),
            alert_on_connection_errors=os.getenv(f'{prefix}ALERT_ON_CONNECTION_ERRORS', 'true').lower() == 'true',
            alert_on_slow_queries=os.getenv(f'{prefix}ALERT_ON_SLOW_QUERIES', 'true').lower() == 'true',
            alert_on_high_cpu=os.getenv(f'{prefix}ALERT_ON_HIGH_CPU', 'true').lower() == 'true',
            alert_on_high_memory=os.getenv(f'{prefix}ALERT_ON_HIGH_MEMORY', 'true').lower() == 'true',
            metrics_retention_hours=int(os.getenv(f'{prefix}METRICS_RETENTION_HOURS', '24')),
            statistics_sample_rate=float(os.getenv(f'{prefix}STATISTICS_SAMPLE_RATE', '1.0')),
            enable_query_logging=os.getenv(f'{prefix}ENABLE_QUERY_LOGGING', 'false').lower() == 'true',
            max_stored_queries=int(os.getenv(f'{prefix}MAX_STORED_QUERIES', '1000')),
            cpu_threshold_percent=float(os.getenv(f'{prefix}CPU_THRESHOLD_PERCENT', '80.0')),
            memory_threshold_percent=float(os.getenv(f'{prefix}MEMORY_THRESHOLD_PERCENT', '85.0')),
            connection_pool_threshold_percent=float(os.getenv(f'{prefix}POOL_THRESHOLD_PERCENT', '90.0'))
        )


__all__ = [
    'PoolConfig',
    'SSLConfig',
    'TimeoutConfig',
    'RetryConfig',
    'MonitoringConfig'
]