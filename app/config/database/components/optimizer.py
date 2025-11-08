"""
Главный оркестратор оптимизации базы данных

Архитектурные решения:
- Координация всех компонентов оптимизации
- Приоритизация операций обслуживания
- Предотвращение конфликтов между компонентами
- Адаптивное планирование на основе нагрузки
- Централизованное управление метриками
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set

from .components.backup import BackupConfig
from .components.pool import ConnectionPoolConfig
from .components.pragma import PragmaConfig
from .components.indexes import IndexConfig
from .components.partitions import PartitionConfig
from .components.vacuum import VacuumConfig
from .components.cache import CacheConfig
from .components.monitoring import DatabaseMonitor
from .components.statistics import DatabaseStatistics
from .components.query_analyzer import QueryAnalyzer


class OptimizationPhase(Enum):
    """Фазы оптимизации"""
    MONITORING = 'monitoring'      # Сбор метрик
    ANALYSIS = 'analysis'          # Анализ данных
    PLANNING = 'planning'          # Планирование операций
    EXECUTION = 'execution'        # Выполнение операций
    VERIFICATION = 'verification'  # Проверка результатов


class MaintenanceOperation(Enum):
    """Типы операций обслуживания"""
    VACUUM = 'vacuum'
    REINDEX = 'reindex'
    ANALYZE = 'analyze'
    PARTITION_CREATE = 'partition_create'
    PARTITION_DROP = 'partition_drop'
    BACKUP = 'backup'
    CACHE_WARMUP = 'cache_warmup'
    STATISTICS_UPDATE = 'statistics_update'


@dataclass
class ScheduledOperation:
    """Запланированная операция обслуживания"""
    operation: MaintenanceOperation
    priority: int  # 0=highest
    scheduled_time: float
    estimated_duration_seconds: float
    component: str
    metadata: Dict[str, Any]
    
    def __lt__(self, other):
        """Сравнение для приоритетной очереди"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.scheduled_time < other.scheduled_time


class DatabaseOptimizer:
    """
    Главный оркестратор оптимизации БД
    
    Ответственности:
    - Координация всех компонентов
    - Планирование операций обслуживания
    - Мониторинг общего состояния
    - Предотвращение конфликтов
    - Адаптивная оптимизация
    """
    
    def __init__(
        self,
        enabled: bool = True,
        
        # Компоненты
        backup_config: Optional[BackupConfig] = None,
        pool_config: Optional[ConnectionPoolConfig] = None,
        pragma_config: Optional[PragmaConfig] = None,
        index_config: Optional[IndexConfig] = None,
        partition_config: Optional[PartitionConfig] = None,
        vacuum_config: Optional[VacuumConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        monitor: Optional[DatabaseMonitor] = None,
        statistics: Optional[DatabaseStatistics] = None,
        query_analyzer: Optional[QueryAnalyzer] = None,
        
        # Планирование
        optimization_interval_seconds: int = 3600,  # Каждый час
        max_concurrent_operations: int = 2,
        respect_maintenance_window: bool = True,
        maintenance_start_hour: int = 2,
        maintenance_end_hour: int = 6,
        
        # Адаптивность
        adaptive_optimization: bool = True,
        load_threshold_percent: float = 70.0,
        defer_under_load: bool = True
    ):
        self.enabled = enabled
        self.optimization_interval_seconds = optimization_interval_seconds
        self.max_concurrent_operations = max_concurrent_operations
        self.respect_maintenance_window = respect_maintenance_window
        self.maintenance_start_hour = maintenance_start_hour
        self.maintenance_end_hour = maintenance_end_hour
        
        self.adaptive_optimization = adaptive_optimization
        self.load_threshold_percent = load_threshold_percent
        self.defer_under_load = defer_under_load
        
        # Инициализация компонентов (или создание дефолтных)
        self.backup = backup_config or BackupConfig()
        self.pool = pool_config or ConnectionPoolConfig()
        self.pragma = pragma_config or PragmaConfig()
        self.indexes = index_config or IndexConfig()
        self.partitions = partition_config or PartitionConfig()
        self.vacuum = vacuum_config or VacuumConfig()
        self.cache = cache_config or CacheConfig()
        self.monitor = monitor or DatabaseMonitor()
        self.statistics = statistics or DatabaseStatistics()
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        
        # Состояние оптимизатора
        self._current_phase: OptimizationPhase = OptimizationPhase.MONITORING
        self._active_operations: Set[MaintenanceOperation] = set()
        self._operation_queue: List[ScheduledOperation] = []
        
        # Метрики
        self._total_optimizations = 0
        self._successful_operations = 0
        self._failed_operations = 0
        self._last_optimization_time: Optional[float] = None
        self._current_load_percent: float = 0.0
        
        # Блокировки для предотвращения конфликтов
        self._operation_lock = asyncio.Lock()
        self._component_locks: Dict[str, asyncio.Lock] = {
            'backup': asyncio.Lock(),
            'vacuum': asyncio.Lock(),
            'indexes': asyncio.Lock(),
            'partitions': asyncio.Lock(),
            'cache': asyncio.Lock()
        }
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """
        Выполнение полного цикла оптимизации
        
        Returns:
            Результаты оптимизации
        """
        if not self.enabled:
            return {'status': 'disabled'}
        
        cycle_start = time.time()
        results = {
            'started_at': datetime.now().isoformat(),
            'phases': {},
            'operations_executed': 0,
            'operations_failed': 0
        }
        
        try:
            # Фаза 1: Мониторинг
            self._current_phase = OptimizationPhase.MONITORING
            monitoring_results = await self._run_monitoring_phase()
            results['phases']['monitoring'] = monitoring_results
            
            # Проверка нагрузки
            if self.defer_under_load and self._current_load_percent > self.load_threshold_percent:
                results['status'] = 'deferred_due_to_load'
                results['current_load_percent'] = self._current_load_percent
                return results
            
            # Фаза 2: Анализ
            self._current_phase = OptimizationPhase.ANALYSIS
            analysis_results = await self._run_analysis_phase()
            results['phases']['analysis'] = analysis_results
            
            # Фаза 3: Планирование
            self._current_phase = OptimizationPhase.PLANNING
            planning_results = await self._run_planning_phase()
            results['phases']['planning'] = planning_results
            
            # Фаза 4: Выполнение
            self._current_phase = OptimizationPhase.EXECUTION
            execution_results = await self._run_execution_phase()
            results['phases']['execution'] = execution_results
            results['operations_executed'] = execution_results.get('executed', 0)
            results['operations_failed'] = execution_results.get('failed', 0)
            
            # Фаза 5: Верификация
            self._current_phase = OptimizationPhase.VERIFICATION
            verification_results = await self._run_verification_phase()
            results['phases']['verification'] = verification_results
            
            self._total_optimizations += 1
            self._last_optimization_time = time.time()
            results['status'] = 'completed'
            
        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
        
        results['duration_seconds'] = time.time() - cycle_start
        return results
    
    async def _run_monitoring_phase(self) -> Dict[str, Any]:
        """Фаза мониторинга - сбор всех метрик"""
        results = {
            'phase': 'monitoring',
            'collected_metrics': []
        }
        
        # Обновление текущей нагрузки (упрощенная версия)
        # В реальности нужно получать из БД
        self._current_load_percent = 50.0  # Заглушка
        
        # Сбор метрик от всех компонентов
        components_metrics = {
            'backup': self.backup.get_metrics(),
            'pool': self.pool.get_metrics(),
            'pragma': self.pragma.get_metrics(),
            'indexes': self.indexes.get_metrics(),
            'partitions': self.partitions.get_metrics(),
            'vacuum': self.vacuum.get_metrics(),
            'cache': self.cache.get_metrics(),
            'monitor': self.monitor.get_metrics(),
            'statistics': self.statistics.get_metrics(),
            'query_analyzer': self.query_analyzer.get_metrics()
        }
        
        results['components'] = components_metrics
        results['current_load_percent'] = self._current_load_percent
        
        # Запись метрик в монитор
        for component_name, metrics in components_metrics.items():
            # Ключевые метрики каждого компонента
            if component_name == 'pool':
                self.monitor.record_metric(
                    'connection_utilization_percent',
                    metrics.get('utilization_percent', 0.0)
                )
            elif component_name == 'cache':
                self.monitor.record_metric(
                    'cache_hit_rate_percent',
                    metrics.get('hit_rate_percent', 0.0)
                )
            elif component_name == 'vacuum':
                tables_need_vacuum = metrics.get('tables_need_vacuum', 0)
                self.monitor.record_metric(
                    'tables_needing_vacuum',
                    float(tables_need_vacuum)
                )
        
        return results
    
    async def _run_analysis_phase(self) -> Dict[str, Any]:
        """Фаза анализа - обработка собранных данных"""
        results = {
            'phase': 'analysis',
            'issues_found': []
        }
        
        # Расчет baselines если нужно
        if self.monitor.should_recalculate_baselines():
            baselines_calculated = self.monitor.calculate_all_baselines()
            results['baselines_calculated'] = baselines_calculated
        
        # Предсказание проблем
        predictions = self.monitor.predict_issues()
        if predictions:
            results['issues_found'].extend(predictions)
        
        # Анализ индексов
        if self.indexes.enabled:
            impact = self.indexes.estimate_maintenance_impact()
            if impact['total_recommendations'] > 0:
                results['issues_found'].append({
                    'component': 'indexes',
                    'type': 'recommendations',
                    'count': impact['total_recommendations'],
                    'reclaimable_mb': impact['total_reclaimable_mb']
                })
        
        # Анализ партиций
        if self.partitions.enabled:
            expired = self.partitions.get_expired_partitions()
            to_create = self.partitions.get_partitions_to_create()
            
            if expired or to_create:
                results['issues_found'].append({
                    'component': 'partitions',
                    'expired_count': len(expired),
                    'to_create_count': len(to_create)
                })
        
        # Анализ VACUUM потребностей
        if self.vacuum.enabled:
            vacuum_ops = self.vacuum.plan_vacuum_operations()
            if vacuum_ops:
                results['issues_found'].append({
                    'component': 'vacuum',
                    'operations_needed': len(vacuum_ops)
                })
        
        # Рекомендации по запросам
        if self.query_analyzer.enabled:
            recommendations = self.query_analyzer.get_all_recommendations('high')
            if recommendations:
                results['issues_found'].append({
                    'component': 'query_analyzer',
                    'high_priority_recommendations': len(recommendations)
                })
        
        return results
    
    async def _run_planning_phase(self) -> Dict[str, Any]:
        """Фаза планирования - создание плана операций"""
        results = {
            'phase': 'planning',
            'operations_planned': 0
        }
        
        self._operation_queue.clear()
        current_time = time.time()
        
        # Проверка окна обслуживания
        in_maintenance_window = self._is_maintenance_window()
        
        # Планирование VACUUM
        if self.vacuum.enabled:
            vacuum_ops = self.vacuum.get_next_operations(count=3)
            for vac_op in vacuum_ops:
                # Блокирующие операции только в окне обслуживания
                if vac_op.is_blocking and not in_maintenance_window:
                    continue
                
                scheduled = ScheduledOperation(
                    operation=MaintenanceOperation.VACUUM,
                    priority=1 if vac_op.priority.value == 'critical' else 2,
                    scheduled_time=current_time,
                    estimated_duration_seconds=vac_op.estimated_duration_seconds,
                    component='vacuum',
                    metadata={'vacuum_operation': vac_op}
                )
                self._operation_queue.append(scheduled)
        
        # Планирование бэкапов
        if self.backup.enabled and self.backup.should_backup_now():
            scheduled = ScheduledOperation(
                operation=MaintenanceOperation.BACKUP,
                priority=0,  # Highest
                scheduled_time=current_time,
                estimated_duration_seconds=self.backup.estimate_backup_duration(),
                component='backup',
                metadata={}
            )
            self._operation_queue.append(scheduled)
        
        # Планирование создания партиций
        if self.partitions.enabled:
            partitions_to_create = self.partitions.get_partitions_to_create()
            for part_name, start_date, end_date in partitions_to_create:
                scheduled = ScheduledOperation(
                    operation=MaintenanceOperation.PARTITION_CREATE,
                    priority=3,
                    scheduled_time=current_time,
                    estimated_duration_seconds=60.0,
                    component='partitions',
                    metadata={
                        'partition_name': part_name,
                        'start_date': start_date,
                        'end_date': end_date
                    }
                )
                self._operation_queue.append(scheduled)
        
        # Планирование удаления партиций (только в окне обслуживания)
        if self.partitions.enabled and in_maintenance_window:
            expired = self.partitions.get_expired_partitions()
            for partition in expired[:5]:  # Максимум 5 за раз
                scheduled = ScheduledOperation(
                    operation=MaintenanceOperation.PARTITION_DROP,
                    priority=4,
                    scheduled_time=current_time,
                    estimated_duration_seconds=30.0,
                    component='partitions',
                    metadata={'partition_info': partition}
                )
                self._operation_queue.append(scheduled)
        
        # Планирование разогрева кэша
        if self.cache.enabled and self.cache.preload_hot_data:
            hot_keys = self.cache.get_hot_keys(top_n=20)
            if hot_keys:
                scheduled = ScheduledOperation(
                    operation=MaintenanceOperation.CACHE_WARMUP,
                    priority=5,
                    scheduled_time=current_time,
                    estimated_duration_seconds=120.0,
                    component='cache',
                    metadata={'hot_keys': [k.key for k in hot_keys]}
                )
                self._operation_queue.append(scheduled)
        
        # Сортировка по приоритету
        self._operation_queue.sort()
        
        results['operations_planned'] = len(self._operation_queue)
        results['in_maintenance_window'] = in_maintenance_window
        
        return results
    
    async def _run_execution_phase(self) -> Dict[str, Any]:
        """Фаза выполнения - выполнение запланированных операций"""
        results = {
            'phase': 'execution',
            'executed': 0,
            'failed': 0,
            'skipped': 0,
            'operations': []
        }
        
        executed_count = 0
        
        for operation in self._operation_queue:
            # Ограничение параллельных операций
            if len(self._active_operations) >= self.max_concurrent_operations:
                results['skipped'] += 1
                continue
            
            # Проверка конфликтов
            if not self._can_execute_operation(operation):
                results['skipped'] += 1
                continue
            
            # Выполнение операции
            try:
                async with self._operation_lock:
                    self._active_operations.add(operation.operation)
                
                execution_result = await self._execute_operation(operation)
                
                if execution_result['success']:
                    self._successful_operations += 1
                    results['executed'] += 1
                else:
                    self._failed_operations += 1
                    results['failed'] += 1
                
                results['operations'].append(execution_result)
                
            except Exception as e:
                self._failed_operations += 1
                results['failed'] += 1
                results['operations'].append({
                    'operation': operation.operation.value,
                    'success': False,
                    'error': str(e)
                })
            
            finally:
                self._active_operations.discard(operation.operation)
            
            executed_count += 1
            
            # Ограничение операций за один цикл
            if executed_count >= 5:
                break
        
        return results
    
    async def _run_verification_phase(self) -> Dict[str, Any]:
        """Фаза верификации - проверка результатов"""
        results = {
            'phase': 'verification',
            'health_checks': {}
        }
        
        # Проверка здоровья компонентов
        components_health = {
            'backup': self.backup.get_metrics(),
            'pool': self.pool.get_metrics(),
            'cache': self.cache.get_metrics(),
            'vacuum': self.vacuum.get_metrics(),
            'indexes': self.indexes.get_metrics()
        }
        
        for component, metrics in components_health.items():
            health_status = self._assess_component_health(component, metrics)
            results['health_checks'][component] = health_status
        
        # Общее здоровье
        overall_health = self.monitor.calculate_overall_health()
        results['overall_health'] = overall_health.value
        
        return results
    
    def _is_maintenance_window(self) -> bool:
        """Проверка находимся ли в окне обслуживания"""
        if not self.respect_maintenance_window:
            return True
        
        current_hour = datetime.now().hour
        
        if self.maintenance_start_hour <= self.maintenance_end_hour:
            return self.maintenance_start_hour <= current_hour < self.maintenance_end_hour
        else:
            # Окно через полночь
            return current_hour >= self.maintenance_start_hour or current_hour < self.maintenance_end_hour
    
    def _can_execute_operation(self, operation: ScheduledOperation) -> bool:
        """Проверка можно ли выполнить операцию"""
        # Проверка времени
        if time.time() < operation.scheduled_time:
            return False
        
        # Проверка конфликтов с активными операциями
        if operation.operation in self._active_operations:
            return False
        
        # VACUUM и REINDEX не могут выполняться одновременно
        if operation.operation == MaintenanceOperation.VACUUM:
            if MaintenanceOperation.REINDEX in self._active_operations:
                return False
        
        if operation.operation == MaintenanceOperation.REINDEX:
            if MaintenanceOperation.VACUUM in self._active_operations:
                return False
        
        return True
    
    async def _execute_operation(self, operation: ScheduledOperation) -> Dict[str, Any]:
        """
        Выполнение операции обслуживания
        
        Args:
            operation: Операция для выполнения
            
        Returns:
            Результат выполнения
        """
        start_time = time.time()
        result = {
            'operation': operation.operation.value,
            'component': operation.component,
            'success': False,
            'duration_seconds': 0.0
        }
        
        try:
            # Получение блокировки компонента
            component_lock = self._component_locks.get(operation.component)
            
            async with component_lock if component_lock else asyncio.Lock():
                if operation.operation == MaintenanceOperation.VACUUM:
                    result['success'] = await self._execute_vacuum(operation)
                
                elif operation.operation == MaintenanceOperation.BACKUP:
                    result['success'] = await self._execute_backup(operation)
                
                elif operation.operation == MaintenanceOperation.PARTITION_CREATE:
                    result['success'] = await self._execute_partition_create(operation)
                
                elif operation.operation == MaintenanceOperation.PARTITION_DROP:
                    result['success'] = await self._execute_partition_drop(operation)
                
                elif operation.operation == MaintenanceOperation.CACHE_WARMUP:
                    result['success'] = await self._execute_cache_warmup(operation)
                
                elif operation.operation == MaintenanceOperation.STATISTICS_UPDATE:
                    result['success'] = await self._execute_statistics_update(operation)
        
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        result['duration_seconds'] = time.time() - start_time
        return result
    
    async def _execute_vacuum(self, operation: ScheduledOperation) -> bool:
        """Выполнение VACUUM операции"""
        # В реальности здесь будет выполнение SQL
        # Сейчас просто эмуляция
        vacuum_op = operation.metadata.get('vacuum_operation')
        if not vacuum_op:
            return False
        
        # Эмуляция выполнения
        await asyncio.sleep(0.1)
        
        # Обновление метрик в компоненте
        self.vacuum.start_operation(vacuum_op)
        
        # Эмуляция успешного завершения
        self.vacuum.complete_vacuum(
            success=True,
            duration_seconds=operation.estimated_duration_seconds,
            tuples_removed=1000
        )
        
        return True
    
    async def _execute_backup(self, operation: ScheduledOperation) -> bool:
        """Выполнение бэкапа"""
        await asyncio.sleep(0.1)
        
        # Обновление метрик
        self.backup.update_metrics(
            success=True,
            size_bytes=1024 * 1024 * 100,  # 100 MB
            duration_seconds=operation.estimated_duration_seconds
        )
        
        return True
    
    async def _execute_partition_create(self, operation: ScheduledOperation) -> bool:
        """Создание партиции"""
        await asyncio.sleep(0.1)
        
        partition_name = operation.metadata.get('partition_name')
        if partition_name:
            self.partitions.record_partition_operation('create', partition_name)
        
        return True
    
    async def _execute_partition_drop(self, operation: ScheduledOperation) -> bool:
        """Удаление партиции"""
        await asyncio.sleep(0.1)
        
        partition_info = operation.metadata.get('partition_info')
        if partition_info:
            self.partitions.record_partition_operation('drop', partition_info.name)
        
        return True
    
    async def _execute_cache_warmup(self, operation: ScheduledOperation) -> bool:
        """Разогрев кэша"""
        await asyncio.sleep(0.1)
        
        # Предзагрузка горячих ключей
        hot_keys = operation.metadata.get('hot_keys', [])
        
        # В реальности здесь будет загрузка данных
        
        return True
    
    async def _execute_statistics_update(self, operation: ScheduledOperation) -> bool:
        """Обновление статистики"""
        await asyncio.sleep(0.1)
        return True
    
    def _assess_component_health(
        self,
        component_name: str,
        metrics: Dict[str, Any]
    ) -> str:
        """Оценка здоровья компонента"""
        # Упрощенная оценка
        if not metrics.get('enabled', True):
            return 'disabled'
        
        # Проверка специфичных метрик
        if component_name == 'pool':
            utilization = metrics.get('utilization_percent', 0.0)
            if utilization > 90:
                return 'critical'
            elif utilization > 70:
                return 'warning'
        
        elif component_name == 'cache':
            hit_rate = metrics.get('hit_rate_percent', 0.0)
            if hit_rate < 60:
                return 'critical'
            elif hit_rate < 80:
                return 'warning'
        
        return 'healthy'
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Получение полного статуса оптимизатора"""
        return {
            'enabled': self.enabled,
            'current_phase': self._current_phase.value,
            'current_load_percent': self._current_load_percent,
            'in_maintenance_window': self._is_maintenance_window(),
            
            # Операции
            'active_operations': [op.value for op in self._active_operations],
            'queued_operations': len(self._operation_queue),
            
            # История
            'total_optimizations': self._total_optimizations,
            'successful_operations': self._successful_operations,
            'failed_operations': self._failed_operations,
            'last_optimization': datetime.fromtimestamp(self._last_optimization_time).isoformat() if self._last_optimization_time else None,
            
            # Компоненты
            'components': {
                'backup': self.backup.get_metrics(),
                'pool': self.pool.get_metrics(),
                'pragma': self.pragma.get_metrics(),
                'indexes': self.indexes.get_metrics(),
                'partitions': self.partitions.get_metrics(),
                'vacuum': self.vacuum.get_metrics(),
                'cache': self.cache.get_metrics(),
                'monitor': self.monitor.get_metrics(),
                'statistics': self.statistics.get_metrics(),
                'query_analyzer': self.query_analyzer.get_metrics()
            },
            
            # Здоровье
            'overall_health': self.monitor.calculate_overall_health().value,
            'active_alerts': len(self.monitor.get_active_alerts())
        }