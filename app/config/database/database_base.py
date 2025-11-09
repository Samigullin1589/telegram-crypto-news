"""
Database Configuration Base
Главная конфигурация базы данных, объединяющая все компоненты
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .base_classes import BaseConfig, ValidationMixin
from .sub_configs import (
    PoolConfig,
    SSLConfig,
    TimeoutConfig,
    RetryConfig,
    MonitoringConfig
)
from .enums import DatabaseEngine
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE CONFIG BASE
# ============================================================================

@dataclass
class DatabaseConfigBase(BaseConfig, ValidationMixin):
    """
    Главная конфигурация базы данных
    
    Объединяет все параметры подключения и настройки для работы с БД.
    Является центральной точкой конфигурации всей системы БД.
    
    Attributes:
        engine: Движок БД (postgresql/sqlite/mysql)
        host: Хост БД
        port: Порт БД
        database: Имя базы данных
        user: Имя пользователя
        password: Пароль
        schema: Схема БД (для PostgreSQL)
        application_name: Имя приложения для идентификации соединений
        server_settings: Дополнительные настройки сервера БД
        pool: Конфигурация пула соединений
        ssl: Конфигурация SSL
        timeouts: Конфигурация таймаутов
        retry: Конфигурация повторных попыток
        monitoring: Конфигурация мониторинга
        echo_queries: Выводить SQL запросы в лог
        log_slow_queries: Логировать медленные запросы
        auto_commit: Автоматический commit после каждого запроса
        enable_query_cache: Включить кэширование запросов
        enable_prepared_statements: Использовать prepared statements
    """
    
    # ===== Основные параметры подключения =====
    engine: DatabaseEngine = DatabaseEngine.POSTGRESQL
    host: str = "localhost"
    port: int = 5432
    database: str = "mydb"
    user: str = "postgres"
    password: str = ""
    
    # ===== Дополнительные параметры =====
    schema: str = "public"
    application_name: str = "crypto_monitor"
    server_settings: Dict[str, Any] = field(default_factory=dict)
    
    # ===== Вложенные конфигурации =====
    pool: PoolConfig = field(default_factory=PoolConfig)
    ssl: SSLConfig = field(default_factory=SSLConfig)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # ===== Флаги поведения =====
    echo_queries: bool = False
    log_slow_queries: bool = True
    auto_commit: bool = False
    enable_query_cache: bool = True
    enable_prepared_statements: bool = True
    
    # ===== Дополнительные опции =====
    encoding: str = "utf-8"
    timezone: str = "UTC"
    max_overflow: int = 10
    
    def validate(self) -> bool:
        """
        Полная валидация всей конфигурации БД
        
        Returns:
            True если валидация успешна
            
        Raises:
            ValidationError: При любых ошибках валидации
        """
        logger.debug(f"Validating DatabaseConfigBase for {self.engine.value}")
        
        # ===== Валидация основных параметров =====
        self._validate_connection_params()
        
        # ===== Валидация вложенных конфигураций =====
        self._validate_nested_configs()
        
        # ===== Специфичная для движка валидация =====
        self._validate_engine_specific()
        
        logger.info(
            f"Database configuration validated successfully: "
            f"{self.engine.value}://{self.host}:{self.port}/{self.database}"
        )
        
        return True
    
    def _validate_connection_params(self) -> None:
        """Валидация параметров подключения"""
        # Валидация хоста
        self.validate_non_empty_string(self.host, "host")
        
        # Валидация порта (для не-SQLite)
        if self.engine != DatabaseEngine.SQLITE:
            self.validate_port(self.port, "port")
        
        # Валидация имени БД
        self.validate_non_empty_string(self.database, "database")
        
        # Валидация пользователя (для не-SQLite)
        if self.engine != DatabaseEngine.SQLITE:
            self.validate_non_empty_string(self.user, "user")
        
        # Валидация схемы (для PostgreSQL)
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.validate_non_empty_string(self.schema, "schema")
        
        # Валидация application_name
        self.validate_non_empty_string(self.application_name, "application_name")
    
    def _validate_nested_configs(self) -> None:
        """Валидация вложенных конфигураций"""
        config_validations = {
            'pool': self.pool,
            'ssl': self.ssl,
            'timeouts': self.timeouts,
            'retry': self.retry,
            'monitoring': self.monitoring
        }
        
        for config_name, config_obj in config_validations.items():
            try:
                config_obj.validate()
            except ValidationError as e:
                raise ValidationError(f"{config_name} configuration invalid: {e}")
    
    def _validate_engine_specific(self) -> None:
        """Валидация специфичных для движка параметров"""
        if self.engine == DatabaseEngine.SQLITE:
            # SQLite не поддерживает некоторые опции
            if self.ssl.enabled:
                logger.warning("SQLite does not support SSL, ignoring SSL config")
            
            if self.pool.min_size > 1 or self.pool.max_size > 1:
                logger.warning("SQLite has limited connection pool support")
        
        elif self.engine == DatabaseEngine.POSTGRESQL:
            # PostgreSQL специфичные проверки
            if self.port != 5432:
                logger.debug(f"Using non-default PostgreSQL port: {self.port}")
        
        elif self.engine == DatabaseEngine.MYSQL:
            # MySQL специфичные проверки
            if self.port != 3306:
                logger.debug(f"Using non-default MySQL port: {self.port}")
    
    def get_connection_string(
        self,
        mask_password: bool = True,
        include_params: bool = False
    ) -> str:
        """
        Получение синхронной строки подключения
        
        Args:
            mask_password: Маскировать пароль для логирования
            include_params: Включить дополнительные параметры
            
        Returns:
            Строка подключения в формате DSN
        """
        password = "***" if (mask_password and self.password) else self.password
        
        # Базовая строка подключения
        if self.engine == DatabaseEngine.SQLITE:
            conn_str = f"sqlite:///{self.database}"
        else:
            conn_str = (
                f"{self.engine.value}://{self.user}:{password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
        
        # Добавляем параметры если требуется
        if include_params and self.engine != DatabaseEngine.SQLITE:
            params = []
            
            if self.schema and self.engine == DatabaseEngine.POSTGRESQL:
                params.append(f"options=-csearch_path={self.schema}")
            
            if self.application_name:
                params.append(f"application_name={self.application_name}")
            
            if params:
                conn_str += "?" + "&".join(params)
        
        return conn_str
    
    def get_async_connection_string(
        self,
        mask_password: bool = True,
        include_params: bool = False
    ) -> str:
        """
        Получение асинхронной строки подключения
        
        Args:
            mask_password: Маскировать пароль
            include_params: Включить дополнительные параметры
            
        Returns:
            Async строка подключения
        """
        conn_str = self.get_connection_string(mask_password, include_params)
        
        # Заменяем драйвер на асинхронный
        driver_replacements = {
            DatabaseEngine.POSTGRESQL: ("postgresql://", "postgresql+asyncpg://"),
            DatabaseEngine.SQLITE: ("sqlite:///", "sqlite+aiosqlite:///"),
            DatabaseEngine.MYSQL: ("mysql://", "mysql+aiomysql://")
        }
        
        old_driver, new_driver = driver_replacements.get(
            self.engine,
            ("", "")
        )
        
        if old_driver and new_driver:
            conn_str = conn_str.replace(old_driver, new_driver, 1)
        
        return conn_str
    
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Получение параметров подключения для драйвера
        
        Returns:
            Словарь с параметрами подключения
        """
        params = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }
        
        # Добавляем специфичные параметры для PostgreSQL
        if self.engine == DatabaseEngine.POSTGRESQL:
            params.update({
                'server_settings': self._get_server_settings(),
                'timeout': self.timeouts.connect_timeout,
                'command_timeout': self.timeouts.query_timeout
            })
        
        # Для SQLite только путь к файлу
        elif self.engine == DatabaseEngine.SQLITE:
            params = {'database': self.database}
        
        return params
    
    def get_pool_params(self) -> Dict[str, Any]:
        """
        Получение параметров для инициализации пула соединений
        
        Returns:
            Словарь с параметрами пула
        """
        return {
            'min_size': self.pool.min_size,
            'max_size': self.pool.max_size,
            'max_queries': self.pool.max_queries,
            'max_inactive_connection_lifetime': self.pool.max_inactive_connection_lifetime,
            'timeout': self.pool.timeout,
            'command_timeout': self.pool.command_timeout,
            'setup_timeout': self.pool.setup_timeout
        }
    
    def get_ssl_params(self) -> Optional[Dict[str, Any]]:
        """
        Получение SSL параметров для подключения
        
        Returns:
            Словарь с SSL параметрами или None если SSL отключен
        """
        if not self.ssl.enabled or self.engine == DatabaseEngine.SQLITE:
            return None
        
        return self.ssl.get_ssl_context_params()
    
    def _get_server_settings(self) -> Dict[str, Any]:
        """
        Получение настроек сервера БД
        
        Returns:
            Словарь с server settings
        """
        settings = self.server_settings.copy()
        
        # Добавляем таймауты для PostgreSQL
        if self.engine == DatabaseEngine.POSTGRESQL:
            settings.update(self.timeouts.get_postgresql_settings())
            
            # Добавляем timezone
            settings['timezone'] = self.timezone
            
            # Добавляем application_name
            settings['application_name'] = self.application_name
        
        return settings
    
    def get_engine_specific_params(self) -> Dict[str, Any]:
        """
        Получение специфичных параметров для движка
        
        Returns:
            Словарь с параметрами специфичными для движка БД
        """
        if self.engine == DatabaseEngine.POSTGRESQL:
            return {
                'schema': self.schema,
                'server_settings': self._get_server_settings(),
                'prepared_statement_cache_size': 100 if self.enable_prepared_statements else 0
            }
        
        elif self.engine == DatabaseEngine.SQLITE:
            return {
                'timeout': self.timeouts.connect_timeout,
                'check_same_thread': False
            }
        
        elif self.engine == DatabaseEngine.MYSQL:
            return {
                'charset': self.encoding.replace('-', ''),
                'autocommit': self.auto_commit
            }
        
        return {}
    
    def get_full_connection_config(self) -> Dict[str, Any]:
        """
        Получение полной конфигурации подключения
        
        Returns:
            Словарь со всеми параметрами подключения
        """
        config = {
            'dsn': self.get_async_connection_string(mask_password=False),
            'connection_params': self.get_connection_params(),
            'pool_params': self.get_pool_params(),
            'ssl_params': self.get_ssl_params(),
            'engine_params': self.get_engine_specific_params(),
            'retry_config': self.retry.to_dict(),
            'monitoring_config': self.monitoring.to_dict()
        }
        
        return config
    
    def test_connection_string(self) -> str:
        """
        Получение строки подключения для тестирования (с маскированным паролем)
        
        Returns:
            Безопасная строка подключения для логов
        """
        return self.get_connection_string(mask_password=True, include_params=True)
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        Получение диагностической информации о конфигурации
        
        Returns:
            Словарь с диагностической информацией
        """
        return {
            'engine': self.engine.value,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'schema': self.schema if self.engine == DatabaseEngine.POSTGRESQL else None,
            'pool_size': f"{self.pool.min_size}-{self.pool.max_size}",
            'ssl_enabled': self.ssl.enabled,
            'ssl_security_level': self.ssl.get_security_level() if self.ssl.enabled else 0,
            'monitoring_enabled': self.monitoring.enabled,
            'retry_enabled': self.retry.enabled,
            'connection_string': self.test_connection_string()
        }
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE_") -> "DatabaseConfigBase":
        """
        Создание конфигурации из переменных окружения
        
        Args:
            prefix: Префикс для переменных окружения
            
        Returns:
            Экземпляр DatabaseConfigBase
        """
        logger.info(f"Loading database configuration from environment with prefix: {prefix}")
        
        # Определяем движок
        engine_str = os.getenv(f'{prefix}ENGINE', 'postgresql').lower()
        try:
            engine = DatabaseEngine(engine_str)
        except ValueError:
            logger.warning(f"Invalid engine '{engine_str}', defaulting to postgresql")
            engine = DatabaseEngine.POSTGRESQL
        
        # Определяем порт по умолчанию в зависимости от движка
        default_port = engine.get_default_port()
        
        # Основные параметры
        config_dict = {
            'engine': engine,
            'host': os.getenv(f'{prefix}HOST', 'localhost'),
            'port': int(os.getenv(f'{prefix}PORT', str(default_port))),
            'database': os.getenv(f'{prefix}NAME', 'mydb'),
            'user': os.getenv(f'{prefix}USER', 'postgres'),
            'password': os.getenv(f'{prefix}PASSWORD', ''),
            'schema': os.getenv(f'{prefix}SCHEMA', 'public'),
            'application_name': os.getenv(f'{prefix}APP_NAME', 'crypto_monitor'),
            
            # Флаги
            'echo_queries': os.getenv(f'{prefix}ECHO_QUERIES', 'false').lower() == 'true',
            'log_slow_queries': os.getenv(f'{prefix}LOG_SLOW_QUERIES', 'true').lower() == 'true',
            'auto_commit': os.getenv(f'{prefix}AUTO_COMMIT', 'false').lower() == 'true',
            'enable_query_cache': os.getenv(f'{prefix}ENABLE_QUERY_CACHE', 'true').lower() == 'true',
            'enable_prepared_statements': os.getenv(f'{prefix}ENABLE_PREPARED_STATEMENTS', 'true').lower() == 'true',
            
            # Дополнительные опции
            'encoding': os.getenv(f'{prefix}ENCODING', 'utf-8'),
            'timezone': os.getenv(f'{prefix}TIMEZONE', 'UTC'),
            'max_overflow': int(os.getenv(f'{prefix}MAX_OVERFLOW', '10'))
        }
        
        # Загружаем вложенные конфигурации
        config_dict['pool'] = PoolConfig.from_env(f'{prefix}POOL_')
        config_dict['ssl'] = SSLConfig.from_env(f'{prefix}SSL_')
        config_dict['timeouts'] = TimeoutConfig.from_env(f'{prefix}TIMEOUT_')
        config_dict['retry'] = RetryConfig.from_env(f'{prefix}RETRY_')
        config_dict['monitoring'] = MonitoringConfig.from_env(f'{prefix}MONITORING_')
        
        logger.info(f"Database configuration loaded: {engine.value}://{config_dict['host']}:{config_dict['port']}/{config_dict['database']}")
        
        return cls(**config_dict)
    
    @classmethod
    def from_url(cls, url: str, **kwargs) -> "DatabaseConfigBase":
        """
        Создание конфигурации из URL строки подключения
        
        Args:
            url: Строка подключения (e.g., postgresql://user:pass@host:port/db)
            **kwargs: Дополнительные параметры для переопределения
            
        Returns:
            Экземпляр DatabaseConfigBase
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        
        # Определяем движок
        engine_str = parsed.scheme.split('+')[0]  # Убираем async драйвер если есть
        try:
            engine = DatabaseEngine(engine_str)
        except ValueError:
            raise ValidationError(f"Unsupported database engine: {engine_str}")
        
        # Извлекаем параметры
        config_dict = {
            'engine': engine,
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or engine.get_default_port(),
            'database': parsed.path.lstrip('/') if parsed.path else 'mydb',
            'user': parsed.username or 'postgres',
            'password': parsed.password or ''
        }
        
        # Добавляем query параметры
        if parsed.query:
            query_params = parse_qs(parsed.query)
            if 'schema' in query_params:
                config_dict['schema'] = query_params['schema'][0]
        
        # Переопределяем параметрами из kwargs
        config_dict.update(kwargs)
        
        return cls(**config_dict)


__all__ = [
    'DatabaseConfigBase'
]