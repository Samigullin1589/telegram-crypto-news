"""
Database Manager
Центральный менеджер для управления БД и её компонентами
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import DatabaseConfigBase
from .loader import DatabaseConfigLoader
from .validators import DatabaseConfigValidator, ValidationResult
from .enums import HealthStatus
from .exceptions import (
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseValidationError
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONNECTION POOL MANAGER
# ============================================================================

class ConnectionPoolManager:
    """
    Менеджер пула соединений
    
    Управляет созданием, мониторингом и закрытием пула соединений к БД.
    """
    
    def __init__(self, config: DatabaseConfigBase):
        """
        Инициализация менеджера пула
        
        Args:
            config: Конфигурация БД
        """
        self.config = config
        self._pool = None
        self._initialized = False
        self._active_connections = 0
        self._total_connections_created = 0
        self._connection_errors = 0
        
        logger.debug("ConnectionPoolManager initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Инициализация пула соединений
        
        Returns:
            Результаты инициализации
        """
        if self._initialized:
            return {'status': 'already_initialized'}
        
        logger.info(
            f"Initializing connection pool: "
            f"min={self.config.pool.min_size}, max={self.config.pool.max_size}"
        )
        
        try:
            # Здесь будет реальное создание пула (asyncpg, aiosqlite и т.д.)
            # Пока создаём заглушку
            self._pool = {
                'min_size': self.config.pool.min_size,
                'max_size': self.config.pool.max_size,
                'timeout': self.config.pool.timeout,
                'created_at': datetime.now()
            }
            
            self._initialized = True
            
            logger.info("Connection pool initialized successfully")
            
            return {
                'status': 'initialized',
                'pool_size': f"{self.config.pool.min_size}-{self.config.pool.max_size}",
                'timeout': self.config.pool.timeout
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Pool initialization failed: {e}")
    
    async def close(self) -> Dict[str, Any]:
        """
        Закрытие пула соединений
        
        Returns:
            Результаты закрытия
        """
        if not self._initialized:
            return {'status': 'not_initialized'}
        
        logger.info("Closing connection pool")
        
        try:
            # Закрытие реального пула
            self._pool = None
            self._initialized = False
            
            logger.info("Connection pool closed successfully")
            
            return {
                'status': 'closed',
                'total_connections_created': self._total_connections_created,
                'connection_errors': self._connection_errors
            }
            
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик пула
        
        Returns:
            Словарь с метриками
        """
        return {
            'initialized': self._initialized,
            'active_connections': self._active_connections,
            'total_connections_created': self._total_connections_created,
            'connection_errors': self._connection_errors,
            'pool_config': {
                'min_size': self.config.pool.min_size,
                'max_size': self.config.pool.max_size,
                'timeout': self.config.pool.timeout
            }
        }
    
    def get_health_status(self) -> HealthStatus:
        """
        Получение статуса здоровья пула
        
        Returns:
            Статус здоровья
        """
        if not self._initialized:
            return HealthStatus.UNKNOWN
        
        # Проверка на большое количество ошибок
        if self._connection_errors > 10:
            return HealthStatus.UNHEALTHY
        
        # Проверка использования пула
        utilization = self._active_connections / self.config.pool.max_size if self.config.pool.max_size > 0 else 0
        
        if utilization > 0.9:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY


# ============================================================================
# DATABASE MONITORING
# ============================================================================

class DatabaseMonitoringService:
    """
    Сервис мониторинга БД
    
    Собирает метрики, отслеживает здоровье системы и генерирует алерты.
    """
    
    def __init__(self, config: DatabaseConfigBase):
        """
        Инициализация сервиса мониторинга
        
        Args:
            config: Конфигурация БД
        """
        self.config = config
        self.enabled = config.monitoring.enabled
        self._metrics_history: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
        self._last_check_time: Optional[datetime] = None
        
        logger.debug(f"DatabaseMonitoringService initialized (enabled={self.enabled})")
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """
        Сбор текущих метрик
        
        Returns:
            Словарь с метриками
        """
        if not self.enabled:
            return {}
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'database': self.config.database,
            'engine': self.config.engine.value,
            'host': self.config.host,
            'port': self.config.port
        }
        
        # Добавляем в историю
        self._metrics_history.append(metrics)
        
        # Ограничиваем размер истории
        max_history = 1000
        if len(self._metrics_history) > max_history:
            self._metrics_history = self._metrics_history[-max_history:]
        
        self._last_check_time = datetime.now()
        
        return metrics
    
    def check_health(self) -> HealthStatus:
        """
        Проверка общего здоровья системы
        
        Returns:
            Статус здоровья
        """
        if not self.enabled:
            return HealthStatus.UNKNOWN
        
        # Проверка времени последнего сбора метрик
        if self._last_check_time:
            time_since_check = (datetime.now() - self._last_check_time).total_seconds()
            
            # Если давно не собирали метрики - что-то не так
            if time_since_check > self.config.monitoring.interval_seconds * 3:
                return HealthStatus.DEGRADED
        
        # Проверка активных алертов
        critical_alerts = [a for a in self._alerts if a.get('severity') == 'critical']
        
        if critical_alerts:
            return HealthStatus.UNHEALTHY
        
        warning_alerts = [a for a in self._alerts if a.get('severity') == 'warning']
        
        if warning_alerts:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def create_alert(
        self,
        severity: str,
        metric_name: str,
        message: str,
        current_value: Any,
        threshold_value: Any
    ) -> None:
        """
        Создание алерта
        
        Args:
            severity: Серьёзность (critical/warning/info)
            metric_name: Имя метрики
            message: Сообщение
            current_value: Текущее значение
            threshold_value: Пороговое значение
        """
        alert = {
            'id': len(self._alerts) + 1,
            'severity': severity,
            'metric_name': metric_name,
            'message': message,
            'current_value': current_value,
            'threshold_value': threshold_value,
            'created_at': datetime.now().isoformat(),
            'acknowledged': False
        }
        
        self._alerts.append(alert)
        
        logger.warning(f"Alert created: [{severity}] {message}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Получение активных алертов
        
        Returns:
            Список активных алертов
        """
        return [a for a in self._alerts if not a.get('acknowledged', False)]
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Подтверждение алерта
        
        Args:
            alert_id: ID алерта
            
        Returns:
            True если алерт найден и подтверждён
        """
        for alert in self._alerts:
            if alert.get('id') == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now().isoformat()
                return True
        
        return False
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Получение сводки по метрикам
        
        Returns:
            Сводка метрик
        """
        return {
            'enabled': self.enabled,
            'metrics_collected': len(self._metrics_history),
            'active_alerts': len(self.get_active_alerts()),
            'total_alerts': len(self._alerts),
            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
            'health_status': self.check_health().value
        }


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """
    Главный менеджер базы данных
    
    Центральная точка управления всей системой БД:
    - Конфигурация и валидация
    - Пул соединений
    - Мониторинг и метрики
    - Здоровье системы
    
    Example:
        >>> manager = DatabaseManager()
        >>> await manager.initialize()
        >>> status = manager.get_status()
        >>> await manager.shutdown()
    """
    
    def __init__(
        self,
        config: Optional[DatabaseConfigBase] = None,
        enable_monitoring: bool = True
    ):
        """
        Инициализация менеджера БД
        
        Args:
            config: Конфигурация БД (если None - загружается из env)
            enable_monitoring: Включить мониторинг
        """
        logger.info("Initializing DatabaseManager")
        
        # Загрузка конфигурации
        if config is None:
            loader = DatabaseConfigLoader()
            config = loader.load_from_env()
        
        self.config = config
        
        # Валидация конфигурации
        validator = DatabaseConfigValidator(config)
        validation_result = validator.validate_all()
        
        if not validation_result.is_valid:
            error_messages = [str(e) for e in validation_result.errors]
            raise DatabaseValidationError(
                f"Database configuration is invalid: {'; '.join(error_messages)}"
            )
        
        logger.info("Configuration validated successfully")
        
        # Инициализация компонентов
        self.pool_manager = ConnectionPoolManager(config)
        self.monitoring = DatabaseMonitoringService(config) if enable_monitoring else None
        
        # Состояние
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._shutdown_requested = False
        
        logger.info(
            f"DatabaseManager created: "
            f"{config.engine.value}://{config.host}:{config.port}/{config.database}"
        )
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Инициализация менеджера и всех компонентов
        
        Returns:
            Результаты инициализации всех компонентов
        """
        if self._initialized:
            logger.warning("DatabaseManager already initialized")
            return {'status': 'already_initialized'}
        
        logger.info("Starting DatabaseManager initialization")
        
        results = {
            'status': 'initializing',
            'components': {}
        }
        
        try:
            # Инициализация пула соединений
            pool_result = await self.pool_manager.initialize()
            results['components']['pool'] = pool_result
            
            # Запуск мониторинга
            if self.monitoring and self.monitoring.enabled:
                await self.monitoring.collect_metrics()
                results['components']['monitoring'] = {
                    'status': 'started',
                    'interval': self.config.monitoring.interval_seconds
                }
            
            self._initialized = True
            self._start_time = datetime.now()
            results['status'] = 'initialized'
            
            logger.info("DatabaseManager initialized successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseManager initialization failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['error'] = str(e)
            raise DatabaseConnectionError(f"Manager initialization failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение полного статуса системы
        
        Returns:
            Словарь со статусом всех компонентов
        """
        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()
        
        status = {
            'initialized': self._initialized,
            'uptime_seconds': uptime,
            'config': {
                'engine': self.config.engine.value,
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'connection_string': self.config.test_connection_string()
            },
            'pool': self.pool_manager.get_metrics(),
            'health': self.get_health_status().value
        }
        
        if self.monitoring:
            status['monitoring'] = self.monitoring.get_metrics_summary()
        
        return status
    
    def get_health_status(self) -> HealthStatus:
        """
        Получение общего статуса здоровья
        
        Returns:
            Статус здоровья системы
        """
        if not self._initialized:
            return HealthStatus.UNKNOWN
        
        if self._shutdown_requested:
            return HealthStatus.DEGRADED
        
        # Проверка пула соединений
        pool_health = self.pool_manager.get_health_status()
        
        if pool_health == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY
        
        # Проверка мониторинга
        if self.monitoring:
            monitoring_health = self.monitoring.check_health()
            
            if monitoring_health == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
            
            if monitoring_health == HealthStatus.DEGRADED or pool_health == HealthStatus.DEGRADED:
                return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение всех метрик
        
        Returns:
            Словарь с метриками всех компонентов
        """
        metrics = {
            'pool': self.pool_manager.get_metrics(),
            'health_status': self.get_health_status().value
        }
        
        if self.monitoring:
            metrics['monitoring'] = self.monitoring.get_metrics_summary()
        
        return metrics
    
    def get_alerts(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Получение алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Словарь с алертами
        """
        if not self.monitoring:
            return {'alerts': [], 'total': 0}
        
        if active_only:
            alerts = self.monitoring.get_active_alerts()
        else:
            alerts = self.monitoring._alerts
        
        return {
            'total': len(alerts),
            'critical': len([a for a in alerts if a.get('severity') == 'critical']),
            'warning': len([a for a in alerts if a.get('severity') == 'warning']),
            'alerts': alerts
        }
    
    async def shutdown(self) -> Dict[str, Any]:
        """
        Graceful shutdown менеджера БД
        
        Returns:
            Результаты завершения работы
        """
        if not self._initialized:
            logger.warning("DatabaseManager not initialized, nothing to shutdown")
            return {'status': 'not_initialized'}
        
        logger.info("Starting DatabaseManager shutdown")
        
        self._shutdown_requested = True
        
        results = {
            'status': 'shutting_down',
            'components': {}
        }
        
        try:
            # Закрытие пула соединений
            pool_result = await self.pool_manager.close()
            results['components']['pool'] = pool_result
            
            # Финальный сбор метрик
            if self.monitoring and self.monitoring.enabled:
                await self.monitoring.collect_metrics()
                results['components']['monitoring'] = {
                    'status': 'stopped',
                    'final_metrics': self.monitoring.get_metrics_summary()
                }
            
            self._initialized = False
            results['status'] = 'shutdown_complete'
            
            uptime = None
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()
                results['total_uptime_seconds'] = uptime
            
            logger.info(f"DatabaseManager shutdown complete (uptime: {uptime}s)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            results['status'] = 'shutdown_error'
            results['error'] = str(e)
            return results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Выполнение проверки здоровья системы
        
        Returns:
            Результаты проверки
        """
        health_status = self.get_health_status()
        
        return {
            'healthy': health_status.is_operational(),
            'status': health_status.value,
            'checks': {
                'initialized': self._initialized,
                'pool_healthy': self.pool_manager.get_health_status().value,
                'monitoring_healthy': self.monitoring.check_health().value if self.monitoring else 'disabled'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"DatabaseManager("
            f"engine={self.config.engine.value}, "
            f"host={self.config.host}, "
            f"database={self.config.database}, "
            f"initialized={self._initialized}"
            f")"
        )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_global_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Получение глобального инстанса менеджера БД
    
    Returns:
        Глобальный DatabaseManager
    """
    global _global_db_manager
    
    if _global_db_manager is None:
        _global_db_manager = DatabaseManager()
    
    return _global_db_manager


def set_db_manager(manager: DatabaseManager) -> None:
    """
    Установка глобального инстанса менеджера БД
    
    Args:
        manager: DatabaseManager для установки
    """
    global _global_db_manager
    _global_db_manager = manager


def reset_db_manager() -> None:
    """Сброс глобального инстанса менеджера"""
    global _global_db_manager
    _global_db_manager = None


__all__ = [
    'ConnectionPoolManager',
    'DatabaseMonitoringService',
    'DatabaseManager',
    'get_db_manager',
    'set_db_manager',
    'reset_db_manager'
]