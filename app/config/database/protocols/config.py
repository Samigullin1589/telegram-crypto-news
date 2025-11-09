# app/config/database/protocols/config.py
"""
Configuration Protocols
Протоколы для конфигурационных объектов
"""

from typing import Protocol, Dict, Any, Optional, runtime_checkable
from pathlib import Path

from .base import Configurable


@runtime_checkable
class DatabaseConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации базы данных"""
    
    # Основные параметры подключения
    engine: str
    host: str
    port: int
    database: str
    user: Optional[str]
    password: Optional[str]
    
    def get_connection_string(self) -> str:
        """
        Получение строки подключения
        
        Returns:
            DSN строка для подключения к БД
        """
        ...
    
    def get_safe_connection_string(self) -> str:
        """
        Получение безопасной строки подключения (без пароля)
        
        Returns:
            DSN строка без чувствительных данных
        """
        ...
    
    def test_connection(self, timeout: float = 5.0) -> bool:
        """
        Тестирование подключения к БД
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            True если подключение успешно
        """
        ...
    
    async def test_connection_async(self, timeout: float = 5.0) -> bool:
        """
        Асинхронное тестирование подключения
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            True если подключение успешно
        """
        ...
    
    def get_engine_specific_options(self) -> Dict[str, Any]:
        """
        Получение специфичных для движка опций
        
        Returns:
            Словарь с опциями для конкретного engine
        """
        ...
    
    def supports_feature(self, feature: str) -> bool:
        """
        Проверка поддержки функции движком БД
        
        Args:
            feature: Название функции (transactions, async, streaming, etc)
            
        Returns:
            True если функция поддерживается
        """
        ...


@runtime_checkable
class PoolConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации пула соединений"""
    
    min_size: int
    max_size: int
    max_idle_time: float
    max_lifetime: float
    strategy: str
    
    def get_pool_params(self) -> Dict[str, Any]:
        """
        Получение параметров для создания пула
        
        Returns:
            Словарь с параметрами пула
        """
        ...
    
    def calculate_optimal_size(self, 
                              expected_load: int,
                              avg_query_time: float) -> int:
        """
        Расчет оптимального размера пула
        
        Args:
            expected_load: Ожидаемая нагрузка (запросов/сек)
            avg_query_time: Среднее время запроса (сек)
            
        Returns:
            Рекомендуемый размер пула
        """
        ...
    
    def validate_pool_size(self) -> bool:
        """
        Валидация размеров пула
        
        Returns:
            True если размеры корректны
        """
        ...


@runtime_checkable
class SSLConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации SSL/TLS"""
    
    enabled: bool
    mode: str
    ca_cert: Optional[Path]
    client_cert: Optional[Path]
    client_key: Optional[Path]
    verify_hostname: bool
    
    def get_ssl_context(self) -> Any:
        """
        Создание SSL контекста
        
        Returns:
            ssl.SSLContext или аналог
        """
        ...
    
    def validate_certificates(self) -> bool:
        """
        Валидация сертификатов
        
        Returns:
            True если все сертификаты валидны
        """
        ...
    
    def get_ssl_params(self) -> Dict[str, Any]:
        """
        Получение параметров SSL для драйвера
        
        Returns:
            Словарь с SSL параметрами
        """
        ...


@runtime_checkable
class TimeoutConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации таймаутов"""
    
    connect: float
    read: float
    write: float
    idle: float
    
    def get_total_timeout(self) -> float:
        """
        Получение суммарного таймаута
        
        Returns:
            Максимальное время выполнения операции
        """
        ...
    
    def adjust_for_operation(self, operation_type: str) -> float:
        """
        Получение таймаута для конкретной операции
        
        Args:
            operation_type: Тип операции (select, insert, update, etc)
            
        Returns:
            Таймаут в секундах
        """
        ...
    
    def is_expired(self, start_time: float, current_time: float) -> bool:
        """
        Проверка истечения таймаута
        
        Args:
            start_time: Время начала операции
            current_time: Текущее время
            
        Returns:
            True если таймаут истек
        """
        ...


@runtime_checkable
class RetryConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации повторных попыток"""
    
    max_attempts: int
    initial_delay: float
    max_delay: float
    backoff_factor: float
    retry_on_errors: list[str]
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Расчет задержки перед следующей попыткой
        
        Args:
            attempt: Номер попытки (начиная с 1)
            
        Returns:
            Задержка в секундах
        """
        ...
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Проверка необходимости повтора
        
        Args:
            error: Возникшее исключение
            attempt: Номер текущей попытки
            
        Returns:
            True если нужно повторить попытку
        """
        ...
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Получение статистики повторов
        
        Returns:
            Словарь со статистикой
        """
        ...


@runtime_checkable
class MonitoringConfigProtocol(Configurable, Protocol):
    """Протокол для конфигурации мониторинга"""
    
    enabled: bool
    metrics_interval: float
    health_check_interval: float
    slow_query_threshold: float
    enable_query_logging: bool
    
    def should_log_query(self, duration: float, query: str) -> bool:
        """
        Проверка необходимости логирования запроса
        
        Args:
            duration: Время выполнения запроса
            query: Текст запроса
            
        Returns:
            True если запрос нужно залогировать
        """
        ...
    
    def get_monitoring_targets(self) -> list[str]:
        """
        Получение списка целей мониторинга
        
        Returns:
            Список целей (connections, queries, pool, etc)
        """
        ...
    
    def configure_exporter(self) -> Dict[str, Any]:
        """
        Конфигурация экспортера метрик
        
        Returns:
            Словарь с настройками экспортера
        """
        ...