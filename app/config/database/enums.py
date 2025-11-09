"""
Database Configuration Enumerations
Перечисления для типов и режимов работы БД
"""

from enum import Enum


class DatabaseEngine(str, Enum):
    """
    Поддерживаемые движки баз данных
    
    Attributes:
        POSTGRESQL: PostgreSQL database
        SQLITE: SQLite database
        MYSQL: MySQL database
    """
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"
    
    def is_async_supported(self) -> bool:
        """Проверка поддержки асинхронного драйвера"""
        return self in (
            DatabaseEngine.POSTGRESQL,
            DatabaseEngine.SQLITE,
            DatabaseEngine.MYSQL
        )
    
    def get_async_driver(self) -> str:
        """Получение имени асинхронного драйвера"""
        driver_map = {
            DatabaseEngine.POSTGRESQL: "asyncpg",
            DatabaseEngine.SQLITE: "aiosqlite",
            DatabaseEngine.MYSQL: "aiomysql"
        }
        return driver_map.get(self, "")
    
    def get_default_port(self) -> int:
        """Получение порта по умолчанию для движка"""
        port_map = {
            DatabaseEngine.POSTGRESQL: 5432,
            DatabaseEngine.SQLITE: 0,  # SQLite не использует порты
            DatabaseEngine.MYSQL: 3306
        }
        return port_map.get(self, 5432)


class PoolStrategy(str, Enum):
    """
    Стратегии управления пулом соединений
    
    Attributes:
        LIFO: Last In First Out - последнее соединение используется первым
        FIFO: First In First Out - первое соединение используется первым
    """
    LIFO = "lifo"
    FIFO = "fifo"
    
    def get_description(self) -> str:
        """Получение описания стратегии"""
        descriptions = {
            PoolStrategy.LIFO: "Last In First Out - reuses most recently used connections",
            PoolStrategy.FIFO: "First In First Out - distributes load evenly across connections"
        }
        return descriptions.get(self, "Unknown strategy")


class SSLMode(str, Enum):
    """
    Режимы SSL подключения к базе данных
    
    Attributes:
        DISABLE: Отключить SSL
        ALLOW: Попытаться SSL, но допустить обычное соединение
        PREFER: Предпочитать SSL, но допустить обычное соединение
        REQUIRE: Требовать SSL
        VERIFY_CA: Требовать SSL с проверкой CA
        VERIFY_FULL: Требовать SSL с полной проверкой сертификата
    """
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"
    
    def requires_ca_file(self) -> bool:
        """Проверка необходимости CA файла"""
        return self in (SSLMode.VERIFY_CA, SSLMode.VERIFY_FULL)
    
    def requires_ssl(self) -> bool:
        """Проверка обязательности SSL"""
        return self in (
            SSLMode.REQUIRE,
            SSLMode.VERIFY_CA,
            SSLMode.VERIFY_FULL
        )
    
    def get_security_level(self) -> int:
        """
        Получение уровня безопасности (0-5)
        
        Returns:
            Числовой уровень безопасности
        """
        security_levels = {
            SSLMode.DISABLE: 0,
            SSLMode.ALLOW: 1,
            SSLMode.PREFER: 2,
            SSLMode.REQUIRE: 3,
            SSLMode.VERIFY_CA: 4,
            SSLMode.VERIFY_FULL: 5
        }
        return security_levels.get(self, 0)


class VacuumStrategy(str, Enum):
    """
    Стратегии VACUUM для PostgreSQL
    
    Attributes:
        STANDARD: Обычный VACUUM
        FULL: VACUUM FULL - полная очистка с блокировкой
        ANALYZE: VACUUM ANALYZE - с обновлением статистики
    """
    STANDARD = "standard"
    FULL = "full"
    ANALYZE = "analyze"
    FREEZE = "freeze"


class BackupType(str, Enum):
    """
    Типы резервного копирования
    
    Attributes:
        FULL: Полное копирование
        INCREMENTAL: Инкрементальное копирование
        DIFFERENTIAL: Дифференциальное копирование
    """
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class HealthStatus(str, Enum):
    """
    Статусы здоровья системы
    
    Attributes:
        HEALTHY: Система работает нормально
        DEGRADED: Система работает с ухудшениями
        UNHEALTHY: Система неработоспособна
        UNKNOWN: Статус неизвестен
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    
    def is_operational(self) -> bool:
        """Проверка работоспособности"""
        return self in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class AlertSeverity(str, Enum):
    """
    Уровни серьёзности алертов
    
    Attributes:
        INFO: Информационное сообщение
        WARNING: Предупреждение
        ERROR: Ошибка
        CRITICAL: Критическая ошибка
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def get_priority(self) -> int:
        """Получение числового приоритета (выше = серьёзнее)"""
        priorities = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3
        }
        return priorities.get(self, 0)


class OperationPriority(str, Enum):
    """
    Приоритеты выполнения операций
    
    Attributes:
        LOW: Низкий приоритет
        NORMAL: Обычный приоритет
        HIGH: Высокий приоритет
        CRITICAL: Критический приоритет
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    
    def get_weight(self) -> int:
        """Получение числового веса приоритета"""
        weights = {
            OperationPriority.LOW: 1,
            OperationPriority.NORMAL: 2,
            OperationPriority.HIGH: 3,
            OperationPriority.CRITICAL: 4
        }
        return weights.get(self, 2)


__all__ = [
    'DatabaseEngine',
    'PoolStrategy',
    'SSLMode',
    'VacuumStrategy',
    'BackupType',
    'HealthStatus',
    'AlertSeverity',
    'OperationPriority'
]