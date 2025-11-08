"""
Централизованный API для управления базой данных

Этот модуль предоставляет простой интерфейс для работы со всей
системой управления и оптимизации базы данных.
"""

from typing import Optional, Dict, Any

from .base import DatabaseConfigBase
from .enums import DatabaseEngine, PoolStrategy, SSLMode
from .exceptions import (
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseValidationError
)
from .loader import DatabaseConfigLoader
from .protocols import DatabaseConfigProtocol
from .validators import DatabaseConfigValidator

from .optimizer import DatabaseOptimizer
from .components import (
    BackupConfig,
    ConnectionPoolConfig,
    PragmaConfig,
    IndexConfig,
    PartitionConfig,
    VacuumConfig,
    CacheConfig,
    DatabaseMonitor,
    DatabaseStatistics,
    QueryAnalyzer
)


class DatabaseManager:
    """
    Главный менеджер базы данных
    
    Предоставляет единую точку входа для:
    - Конфигурации БД
    - Оптимизации
    - Мониторинга
    - Статистики
    
    Использование:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Запуск оптимизации
        results = await db_manager.run_optimization()
        
        # Получение статуса
        status = db_manager.get_status()
    """
    
    def __init__(
        self,
        config: Optional[DatabaseConfigBase] = None,
        enable_optimization: bool = True,
        enable_monitoring: bool = True,
        enable_statistics: bool = True
    ):
        """
        Инициализация менеджера БД
        
        Args:
            config: Конфигурация БД (если None - загружается из env)
            enable_optimization: Включить оптимизацию
            enable_monitoring: Включить мониторинг
            enable_statistics: Включить сбор статистики
        """
        # Загрузка конфигурации
        if config is None:
            loader = DatabaseConfigLoader()
            config = loader.load_from_env()
        
        self.config = config
        
        # Валидация
        validator = DatabaseConfigValidator(config)
        validation_result = validator.validate_all()
        
        if not validation_result.is_valid:
            raise DatabaseValidationError(
                f"Database configuration is invalid: {validation_result.errors}"
            )
        
        # Инициализация компонентов оптимизации
        self.backup_config = BackupConfig(enabled=True)
        self.pool_config = ConnectionPoolConfig(
            min_size=config.pool.min_size,
            max_size=config.pool.max_size
        )
        self.pragma_config = PragmaConfig()
        self.index_config = IndexConfig(enabled=True)
        self.partition_config = PartitionConfig(enabled=True)
        self.vacuum_config = VacuumConfig(enabled=True)
        self.cache_config = CacheConfig(enabled=True)
        
        # Инициализация мониторинга и статистики
        self.monitor = DatabaseMonitor(enabled=enable_monitoring)
        self.statistics = DatabaseStatistics(enabled=enable_statistics)
        self.query_analyzer = QueryAnalyzer(enabled=True)
        
        # Главный оптимизатор
        self.optimizer = DatabaseOptimizer(
            enabled=enable_optimization,
            backup_config=self.backup_config,
            pool_config=self.pool_config,
            pragma_config=self.pragma_config,
            index_config=self.index_config,
            partition_config=self.partition_config,
            vacuum_config=self.vacuum_config,
            cache_config=self.cache_config,
            monitor=self.monitor,
            statistics=self.statistics,
            query_analyzer=self.query_analyzer
        )
        
        self._initialized = False
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Инициализация менеджера БД
        
        Returns:
            Результаты инициализации
        """
        if self._initialized:
            return {'status': 'already_initialized'}
        
        results = {
            'status': 'initializing',
            'components': {}
        }
        
        # Инициализация подключения
        # В реальности здесь будет создание пула соединений
        results['components']['connection'] = {'status': 'ready'}
        
        # Инициализация мониторинга
        if self.monitor.enabled:
            # Расчет начальных baselines
            baselines = self.monitor.calculate_all_baselines()
            results['components']['monitoring'] = {
                'status': 'ready',
                'baselines_calculated': baselines
            }
        
        # Инициализация статистики
        if self.statistics.enabled:
            results['components']['statistics'] = {'status': 'ready'}
        
        self._initialized = True
        results['status'] = 'initialized'
        
        return results
    
    async def run_optimization(self) -> Dict[str, Any]:
        """
        Запуск цикла оптимизации
        
        Returns:
            Результаты оптимизации
        """
        if not self._initialized:
            await self.initialize()
        
        return await self.optimizer.run_optimization_cycle()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение полного статуса системы
        
        Returns:
            Словарь со статусом всех компонентов
        """
        return {
            'initialized': self._initialized,
            'config': {
                'engine': self.config.engine.value,
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database
            },
            'optimizer': self.optimizer.get_comprehensive_status() if self._initialized else None,
            'health': self.monitor.calculate_overall_health().value if self.monitor.enabled else 'unknown'
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение всех метрик
        
        Returns:
            Словарь с метриками всех компонентов
        """
        return {
            'backup': self.backup_config.get_metrics(),
            'pool': self.pool_config.get_metrics(),
            'pragma': self.pragma_config.get_metrics(),
            'indexes': self.index_config.get_metrics(),
            'partitions': self.partition_config.get_metrics(),
            'vacuum': self.vacuum_config.get_metrics(),
            'cache': self.cache_config.get_metrics(),
            'monitoring': self.monitor.get_metrics(),
            'statistics': self.statistics.get_metrics(),
            'query_analyzer': self.query_analyzer.get_metrics()
        }
    
    def get_recommendations(self, severity: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение всех рекомендаций по оптимизации
        
        Args:
            severity: Фильтр по серьезности ('high', 'medium', 'low')
            
        Returns:
            Словарь с рекомендациями от всех компонентов
        """
        recommendations = {
            'indexes': self.index_config.get_recommendations(severity),
            'queries': self.query_analyzer.get_all_recommendations(severity),
            'vacuum': [],
            'partitions': []
        }
        
        # Рекомендации по VACUUM
        if self.vacuum_config.enabled:
            vacuum_ops = self.vacuum_config.plan_vacuum_operations()
            recommendations['vacuum'] = [
                {
                    'table': f"{op.schema_name}.{op.table_name}",
                    'strategy': op.strategy.value,
                    'priority': op.priority.value,
                    'estimated_duration': op.estimated_duration_seconds
                }
                for op in vacuum_ops[:10]  # Top 10
            ]
        
        # Рекомендации по партициям
        if self.partition_config.enabled:
            expired = self.partition_config.get_expired_partitions()
            to_create = self.partition_config.get_partitions_to_create()
            
            recommendations['partitions'] = {
                'expired_to_drop': len(expired),
                'new_to_create': len(to_create)
            }
        
        return recommendations
    
    def get_alerts(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Получение алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Словарь с алертами
        """
        if not self.monitor.enabled:
            return {'alerts': []}
        
        if active_only:
            alerts = self.monitor.get_active_alerts()
        else:
            alerts = self.monitor.get_alert_history(hours=24)
        
        return {
            'total': len(alerts),
            'critical': len([a for a in alerts if a.severity.value == 'critical']),
            'warning': len([a for a in alerts if a.severity.value == 'warning']),
            'alerts': [
                {
                    'id': a.id,
                    'severity': a.severity.value,
                    'metric': a.metric_name,
                    'message': a.message,
                    'current_value': a.current_value,
                    'threshold': a.threshold_value,
                    'created_at': a.created_at,
                    'duration_seconds': a.duration_seconds,
                    'acknowledged': a.acknowledged
                }
                for a in alerts
            ]
        }
    
    async def shutdown(self) -> Dict[str, Any]:
        """
        Graceful shutdown менеджера БД
        
        Returns:
            Результаты завершения
        """
        results = {
            'status': 'shutting_down',
            'components': {}
        }
        
        # Завершение активных операций
        if self.optimizer._active_operations:
            results['components']['optimizer'] = {
                'active_operations': len(self.optimizer._active_operations),
                'status': 'waiting_for_completion'
            }
            
            # Ожидание завершения (с таймаутом)
            import asyncio
            try:
                await asyncio.wait_for(
                    self._wait_for_operations(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                results['components']['optimizer']['status'] = 'forced_shutdown'
        
        # Закрытие соединений
        # В реальности здесь будет закрытие пула
        results['components']['connection'] = {'status': 'closed'}
        
        self._initialized = False
        results['status'] = 'shutdown_complete'
        
        return results
    
    async def _wait_for_operations(self) -> None:
        """Ожидание завершения активных операций"""
        import asyncio
        while self.optimizer._active_operations:
            await asyncio.sleep(1.0)


# Создание глобального инстанса (опционально)
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


__all__ = [
    # Main API
    'DatabaseManager',
    'get_db_manager',
    'set_db_manager',
    
    # Base
    'DatabaseConfigBase',
    
    # Enums
    'DatabaseEngine',
    'PoolStrategy',
    'SSLMode',
    
    # Exceptions
    'DatabaseConfigError',
    'DatabaseConnectionError',
    'DatabaseValidationError',
    
    # Loader & Validator
    'DatabaseConfigLoader',
    'DatabaseConfigValidator',
    
    # Protocols
    'DatabaseConfigProtocol',
    
    # Optimizer
    'DatabaseOptimizer',
    
    # Components
    'BackupConfig',
    'ConnectionPoolConfig',
    'PragmaConfig',
    'IndexConfig',
    'PartitionConfig',
    'VacuumConfig',
    'CacheConfig',
    'DatabaseMonitor',
    'DatabaseStatistics',
    'QueryAnalyzer'
]