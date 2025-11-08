"""
Компонент управления VACUUM операциями PostgreSQL

Архитектурные решения:
- Интеллектуальное планирование VACUUM на основе dead tuples
- Адаптивный выбор между VACUUM, VACUUM ANALYZE и VACUUM FULL
- Предотвращение блокировок в пиковые часы
- Мониторинг эффективности autovacuum
- Координация с другими операциями обслуживания
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class VacuumStrategy(Enum):
    """Стратегии VACUUM"""
    ANALYZE = 'analyze'           # VACUUM ANALYZE - быстрая очистка + статистика
    STANDARD = 'standard'         # VACUUM - стандартная очистка
    FULL = 'full'                 # VACUUM FULL - полная перестройка (блокирует таблицу)
    FREEZE = 'freeze'             # VACUUM FREEZE - обновление замороженных транзакций


class VacuumPriority(Enum):
    """Приоритет VACUUM операции"""
    CRITICAL = 'critical'  # Немедленное выполнение
    HIGH = 'high'          # Высокий приоритет
    NORMAL = 'normal'      # Обычный приоритет
    LOW = 'low'            # Низкий приоритет


@dataclass
class TableVacuumMetrics:
    """Метрики VACUUM для таблицы"""
    table_name: str
    schema_name: str = 'public'
    
    # Dead tuples метрики
    live_tuples: int = 0
    dead_tuples: int = 0
    dead_tuples_percent: float = 0.0
    
    # Bloat метрики
    table_size_bytes: int = 0
    bloat_bytes: int = 0
    bloat_percent: float = 0.0
    
    # История VACUUM
    last_vacuum: Optional[datetime] = None
    last_autovacuum: Optional[datetime] = None
    last_analyze: Optional[datetime] = None
    vacuum_count: int = 0
    autovacuum_count: int = 0
    
    # Транзакционные метрики
    age: int = 0  # Возраст в транзакциях
    freeze_max_age: int = 200_000_000
    
    @property
    def needs_vacuum(self) -> bool:
        """Нужна ли очистка"""
        return self.dead_tuples_percent > 10.0 or self.bloat_percent > 20.0
    
    @property
    def needs_freeze(self) -> bool:
        """Нужен ли FREEZE"""
        return self.age > (self.freeze_max_age * 0.75)
    
    @property
    def hours_since_vacuum(self) -> float:
        """Часов с последней очистки"""
        if not self.last_vacuum:
            return float('inf')
        return (datetime.now() - self.last_vacuum).total_seconds() / 3600
    
    @property
    def table_size_mb(self) -> float:
        """Размер таблицы в MB"""
        return self.table_size_bytes / (1024 * 1024)


@dataclass
class VacuumOperation:
    """Операция VACUUM"""
    table_name: str
    schema_name: str
    strategy: VacuumStrategy
    priority: VacuumPriority
    scheduled_time: datetime
    estimated_duration_seconds: float = 0.0
    blocks_reads: bool = False
    
    # Результаты выполнения
    executed: bool = False
    success: bool = False
    actual_duration_seconds: float = 0.0
    tuples_removed: int = 0
    pages_removed: int = 0
    error_message: Optional[str] = None
    
    @property
    def is_blocking(self) -> bool:
        """Блокирует ли операция таблицу"""
        return self.strategy == VacuumStrategy.FULL


class VacuumConfig:
    """
    Конфигурация и управление VACUUM операциями
    
    Ответственности:
    - Мониторинг состояния таблиц
    - Планирование VACUUM операций
    - Выбор оптимальной стратегии
    - Координация с autovacuum
    - Предотвращение конфликтов
    """
    
    def __init__(
        self,
        enabled: bool = True,
        
        # Пороги для запуска VACUUM
        dead_tuples_threshold_percent: float = 10.0,
        bloat_threshold_percent: float = 20.0,
        age_threshold_percent: float = 75.0,
        
        # Расписание
        preferred_vacuum_hours: List[int] = None,  # Часы для VACUUM (0-23)
        forbidden_vacuum_hours: List[int] = None,   # Запрещенные часы
        
        # Стратегии
        auto_choose_strategy: bool = True,
        default_strategy: VacuumStrategy = VacuumStrategy.ANALYZE,
        full_vacuum_bloat_threshold: float = 40.0,
        
        # Autovacuum координация
        respect_autovacuum: bool = True,
        autovacuum_max_workers: int = 3,
        
        # Безопасность
        max_concurrent_operations: int = 2,
        skip_large_tables_mb: float = 10000.0,  # Пропускать таблицы > 10GB
        
        # Мониторинг
        track_effectiveness: bool = True
    ):
        self.enabled = enabled
        self.dead_tuples_threshold_percent = dead_tuples_threshold_percent
        self.bloat_threshold_percent = bloat_threshold_percent
        self.age_threshold_percent = age_threshold_percent
        
        self.preferred_vacuum_hours = preferred_vacuum_hours or [2, 3, 4, 5]
        self.forbidden_vacuum_hours = forbidden_vacuum_hours or [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        
        self.auto_choose_strategy = auto_choose_strategy
        self.default_strategy = default_strategy
        self.full_vacuum_bloat_threshold = full_vacuum_bloat_threshold
        
        self.respect_autovacuum = respect_autovacuum
        self.autovacuum_max_workers = autovacuum_max_workers
        
        self.max_concurrent_operations = max_concurrent_operations
        self.skip_large_tables_mb = skip_large_tables_mb
        self.track_effectiveness = track_effectiveness
        
        # Кэш метрик таблиц
        self._tables_metrics: Dict[str, TableVacuumMetrics] = {}
        self._last_scan_time: Optional[float] = None
        
        # Очередь операций
        self._scheduled_operations: List[VacuumOperation] = []
        self._active_operations: Set[str] = set()
        
        # История и статистика
        self._completed_operations: List[VacuumOperation] = []
        self._failed_operations: List[VacuumOperation] = []
        
        # Агрегированные метрики
        self._total_operations = 0
        self._successful_operations = 0
        self._failed_operations = 0
        self._total_tuples_removed = 0
        self._total_duration_seconds = 0.0
    
    def analyze_tables(self, tables_data: List[Dict[str, Any]]) -> None:
        """
        Анализ состояния таблиц
        
        Args:
            tables_data: Данные из pg_stat_user_tables + pg_class
        """
        self._last_scan_time = time.time()
        self._tables_metrics.clear()
        
        for table_data in tables_data:
            metrics = TableVacuumMetrics(
                table_name=table_data['tablename'],
                schema_name=table_data.get('schemaname', 'public'),
                live_tuples=table_data.get('n_live_tup', 0),
                dead_tuples=table_data.get('n_dead_tup', 0),
                table_size_bytes=table_data.get('table_size', 0),
                bloat_bytes=table_data.get('bloat_size', 0),
                last_vacuum=table_data.get('last_vacuum'),
                last_autovacuum=table_data.get('last_autovacuum'),
                last_analyze=table_data.get('last_analyze'),
                vacuum_count=table_data.get('vacuum_count', 0),
                autovacuum_count=table_data.get('autovacuum_count', 0),
                age=table_data.get('age', 0)
            )
            
            # Расчет процентов
            total_tuples = metrics.live_tuples + metrics.dead_tuples
            if total_tuples > 0:
                metrics.dead_tuples_percent = (metrics.dead_tuples / total_tuples) * 100
            
            if metrics.table_size_bytes > 0:
                metrics.bloat_percent = (metrics.bloat_bytes / metrics.table_size_bytes) * 100
            
            self._tables_metrics[f"{metrics.schema_name}.{metrics.table_name}"] = metrics
    
    def plan_vacuum_operations(self) -> List[VacuumOperation]:
        """
        Планирование VACUUM операций на основе анализа
        
        Returns:
            Список запланированных операций
        """
        if not self.enabled:
            return []
        
        self._scheduled_operations.clear()
        current_time = datetime.now()
        
        for full_table_name, metrics in self._tables_metrics.items():
            # Пропускаем слишком большие таблицы
            if metrics.table_size_mb > self.skip_large_tables_mb:
                continue
            
            # Пропускаем таблицы в активных операциях
            if full_table_name in self._active_operations:
                continue
            
            # Определяем необходимость и приоритет
            priority = self._calculate_priority(metrics)
            if priority is None:
                continue  # VACUUM не нужен
            
            # Выбор стратегии
            strategy = self._choose_strategy(metrics)
            
            # Расчет времени выполнения
            scheduled_time = self._calculate_schedule_time(metrics, strategy, current_time)
            estimated_duration = self._estimate_duration(metrics, strategy)
            
            operation = VacuumOperation(
                table_name=metrics.table_name,
                schema_name=metrics.schema_name,
                strategy=strategy,
                priority=priority,
                scheduled_time=scheduled_time,
                estimated_duration_seconds=estimated_duration,
                blocks_reads=(strategy == VacuumStrategy.FULL)
            )
            
            self._scheduled_operations.append(operation)
        
        # Сортировка по приоритету и времени
        self._scheduled_operations.sort(
            key=lambda op: (
                -list(VacuumPriority).index(op.priority),
                op.scheduled_time
            )
        )
        
        return self._scheduled_operations.copy()
    
    def _calculate_priority(self, metrics: TableVacuumMetrics) -> Optional[VacuumPriority]:
        """
        Расчет приоритета VACUUM операции
        
        Args:
            metrics: Метрики таблицы
            
        Returns:
            Приоритет или None если VACUUM не нужен
        """
        # Критический: freeze age близок к лимиту
        if metrics.needs_freeze:
            return VacuumPriority.CRITICAL
        
        # Высокий: большой процент dead tuples
        if metrics.dead_tuples_percent > 30.0:
            return VacuumPriority.HIGH
        
        # Высокий: значительный bloat
        if metrics.bloat_percent > self.full_vacuum_bloat_threshold:
            return VacuumPriority.HIGH
        
        # Обычный: превышены пороги
        if (metrics.dead_tuples_percent > self.dead_tuples_threshold_percent or
            metrics.bloat_percent > self.bloat_threshold_percent):
            return VacuumPriority.NORMAL
        
        # Низкий: давно не было VACUUM
        if metrics.hours_since_vacuum > 168:  # Неделя
            return VacuumPriority.LOW
        
        return None
    
    def _choose_strategy(self, metrics: TableVacuumMetrics) -> VacuumStrategy:
        """
        Выбор стратегии VACUUM
        
        Args:
            metrics: Метрики таблицы
            
        Returns:
            Стратегия VACUUM
        """
        if not self.auto_choose_strategy:
            return self.default_strategy
        
        # FREEZE для старых транзакций
        if metrics.needs_freeze:
            return VacuumStrategy.FREEZE
        
        # FULL для сильного bloat (только в разрешенное время!)
        if (metrics.bloat_percent > self.full_vacuum_bloat_threshold and
            self._is_safe_time_for_full_vacuum()):
            return VacuumStrategy.FULL
        
        # ANALYZE для умеренных dead tuples
        if metrics.dead_tuples_percent < 20.0:
            return VacuumStrategy.ANALYZE
        
        # STANDARD для остальных случаев
        return VacuumStrategy.STANDARD
    
    def _calculate_schedule_time(
        self,
        metrics: TableVacuumMetrics,
        strategy: VacuumStrategy,
        current_time: datetime
    ) -> datetime:
        """
        Расчет времени выполнения VACUUM
        
        Args:
            metrics: Метрики таблицы
            strategy: Стратегия VACUUM
            current_time: Текущее время
            
        Returns:
            Запланированное время
        """
        current_hour = current_time.hour
        
        # Критические операции - немедленно
        if metrics.needs_freeze:
            return current_time
        
        # FULL VACUUM - только в предпочтительные часы
        if strategy == VacuumStrategy.FULL:
            if current_hour in self.preferred_vacuum_hours:
                return current_time
            else:
                # Находим ближайшее предпочтительное время
                return self._find_next_preferred_time(current_time)
        
        # Обычные операции - избегаем запрещенных часов
        if current_hour in self.forbidden_vacuum_hours:
            return self._find_next_allowed_time(current_time)
        
        return current_time
    
    def _find_next_preferred_time(self, from_time: datetime) -> datetime:
        """Поиск следующего предпочтительного времени"""
        next_time = from_time
        
        for _ in range(24):  # Максимум 24 часа вперед
            next_time += timedelta(hours=1)
            if next_time.hour in self.preferred_vacuum_hours:
                return next_time.replace(minute=0, second=0)
        
        return from_time + timedelta(hours=1)
    
    def _find_next_allowed_time(self, from_time: datetime) -> datetime:
        """Поиск следующего разрешенного времени"""
        next_time = from_time
        
        for _ in range(24):
            next_time += timedelta(hours=1)
            if next_time.hour not in self.forbidden_vacuum_hours:
                return next_time.replace(minute=0, second=0)
        
        return from_time + timedelta(hours=1)
    
    def _is_safe_time_for_full_vacuum(self) -> bool:
        """Безопасно ли время для FULL VACUUM"""
        current_hour = datetime.now().hour
        return current_hour in self.preferred_vacuum_hours
    
    def _estimate_duration(
        self,
        metrics: TableVacuumMetrics,
        strategy: VacuumStrategy
    ) -> float:
        """
        Оценка длительности VACUUM
        
        Args:
            metrics: Метрики таблицы
            strategy: Стратегия VACUUM
            
        Returns:
            Оценка в секундах
        """
        # Базовая оценка: 1GB/минуту для ANALYZE, 1GB/5минут для FULL
        size_gb = metrics.table_size_bytes / (1024 * 1024 * 1024)
        
        if strategy == VacuumStrategy.ANALYZE:
            return size_gb * 60  # 1 минута на GB
        elif strategy == VacuumStrategy.FULL:
            return size_gb * 300  # 5 минут на GB
        elif strategy == VacuumStrategy.FREEZE:
            return size_gb * 120  # 2 минуты на GB
        else:  # STANDARD
            return size_gb * 180  # 3 минуты на GB
    
    def can_start_operation(self, operation: VacuumOperation) -> bool:
        """
        Можно ли начать операцию
        
        Args:
            operation: Операция VACUUM
            
        Returns:
            True если можно начать
        """
        # Проверка времени
        if datetime.now() < operation.scheduled_time:
            return False
        
        # Проверка максимального количества параллельных операций
        if len(self._active_operations) >= self.max_concurrent_operations:
            return False
        
        # Проверка запрещенных часов для FULL
        if operation.is_blocking:
            current_hour = datetime.now().hour
            if current_hour in self.forbidden_vacuum_hours:
                return False
        
        return True
    
    def start_operation(self, operation: VacuumOperation) -> bool:
        """
        Начало выполнения операции
        
        Args:
            operation: Операция VACUUM
            
        Returns:
            True если операция началась
        """
        full_name = f"{operation.schema_name}.{operation.table_name}"
        
        if full_name in self._active_operations:
            return False
        
        self._active_operations.add(full_name)
        return True
    
    def complete_operation(
        self,
        operation: VacuumOperation,
        success: bool,
        duration_seconds: float,
        tuples_removed: int = 0,
        pages_removed: int = 0,
        error: Optional[str] = None
    ) -> None:
        """
        Завершение операции
        
        Args:
            operation: Операция VACUUM
            success: Успешность
            duration_seconds: Длительность
            tuples_removed: Удалено кортежей
            pages_removed: Удалено страниц
            error: Сообщение об ошибке
        """
        full_name = f"{operation.schema_name}.{operation.table_name}"
        self._active_operations.discard(full_name)
        
        operation.executed = True
        operation.success = success
        operation.actual_duration_seconds = duration_seconds
        operation.tuples_removed = tuples_removed
        operation.pages_removed = pages_removed
        operation.error_message = error
        
        self._total_operations += 1
        
        if success:
            self._successful_operations += 1
            self._total_tuples_removed += tuples_removed
            self._total_duration_seconds += duration_seconds
            self._completed_operations.append(operation)
        else:
            self._failed_operations += 1
            self._failed_operations.append(operation)
    
    def get_next_operations(self, count: int = 1) -> List[VacuumOperation]:
        """
        Получение следующих операций для выполнения
        
        Args:
            count: Количество операций
            
        Returns:
            Список операций готовых к выполнению
        """
        ready_operations = []
        
        for operation in self._scheduled_operations:
            if len(ready_operations) >= count:
                break
            
            if not operation.executed and self.can_start_operation(operation):
                ready_operations.append(operation)
        
        return ready_operations
    
    def get_table_metrics(self, table_name: str, schema: str = 'public') -> Optional[TableVacuumMetrics]:
        """Получение метрик таблицы"""
        full_name = f"{schema}.{table_name}"
        return self._tables_metrics.get(full_name)
    
    def get_effectiveness_report(self) -> Dict[str, Any]:
        """
        Отчет об эффективности VACUUM операций
        
        Returns:
            Словарь с метриками эффективности
        """
        if self._successful_operations == 0:
            return {
                'success_rate': 0.0,
                'avg_duration_seconds': 0.0,
                'total_space_reclaimed_mb': 0.0
            }
        
        # Средняя длительность
        avg_duration = self._total_duration_seconds / self._successful_operations
        
        # Оценка освобожденного места
        # (предположение: dead tuples занимают примерно столько же места)
        estimated_space_reclaimed_bytes = sum(
            self._tables_metrics[f"{op.schema_name}.{op.table_name}"].dead_tuples * 100
            for op in self._completed_operations[-10:]  # Последние 10
            if f"{op.schema_name}.{op.table_name}" in self._tables_metrics
        )
        
        return {
            'total_operations': self._total_operations,
            'successful_operations': self._successful_operations,
            'failed_operations': len(self._failed_operations),
            'success_rate': (self._successful_operations / self._total_operations) * 100,
            'avg_duration_seconds': avg_duration,
            'avg_duration_minutes': avg_duration / 60,
            'total_tuples_removed': self._total_tuples_removed,
            'estimated_space_reclaimed_mb': estimated_space_reclaimed_bytes / (1024 * 1024),
            'active_operations': len(self._active_operations),
            'scheduled_operations': len(self._scheduled_operations)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик компонента"""
        hours_since_scan = 0.0
        if self._last_scan_time:
            hours_since_scan = (time.time() - self._last_scan_time) / 3600
        
        # Статистика по таблицам
        tables_need_vacuum = sum(
            1 for m in self._tables_metrics.values() if m.needs_vacuum
        )
        tables_need_freeze = sum(
            1 for m in self._tables_metrics.values() if m.needs_freeze
        )
        
        return {
            'enabled': self.enabled,
            'total_tables': len(self._tables_metrics),
            'tables_need_vacuum': tables_need_vacuum,
            'tables_need_freeze': tables_need_freeze,
            'scheduled_operations': len(self._scheduled_operations),
            'active_operations': len(self._active_operations),
            'total_operations': self._total_operations,
            'successful_operations': self._successful_operations,
            'failed_operations': len(self._failed_operations),
            'hours_since_scan': hours_since_scan,
            'auto_choose_strategy': self.auto_choose_strategy,
            'default_strategy': self.default_strategy.value,
            'max_concurrent_operations': self.max_concurrent_operations
        }