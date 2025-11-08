"""
Компонент сбора и анализа статистики БД

Архитектурные решения:
- Агрегация статистики по различным измерениям
- Расчет производительности запросов
- Анализ использования ресурсов
- Генерация отчетов
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, DefaultDict


class StatisticsPeriod(Enum):
    """Период статистики"""
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


@dataclass
class QueryStatistics:
    """Статистика запросов"""
    query_hash: str
    query_text: str
    calls: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    mean_time_ms: float = 0.0
    stddev_time_ms: float = 0.0
    rows: int = 0
    shared_blks_hit: int = 0
    shared_blks_read: int = 0
    shared_blks_written: int = 0
    temp_blks_read: int = 0
    temp_blks_written: int = 0
    blk_read_time_ms: float = 0.0
    blk_write_time_ms: float = 0.0
    
    @property
    def avg_time_ms(self) -> float:
        """Среднее время выполнения"""
        return self.total_time_ms / max(1, self.calls)
    
    @property
    def cache_hit_ratio(self) -> float:
        """Процент попаданий в кэш"""
        total_reads = self.shared_blks_hit + self.shared_blks_read
        if total_reads == 0:
            return 100.0
        return (self.shared_blks_hit / total_reads) * 100
    
    @property
    def uses_temp_files(self) -> bool:
        """Использует ли временные файлы"""
        return self.temp_blks_read > 0 or self.temp_blks_written > 0


@dataclass
class TableStatistics:
    """Статистика таблицы"""
    schema_name: str
    table_name: str
    seq_scan: int = 0
    seq_tup_read: int = 0
    idx_scan: int = 0
    idx_tup_fetch: int = 0
    n_tup_ins: int = 0
    n_tup_upd: int = 0
    n_tup_del: int = 0
    n_tup_hot_upd: int = 0
    n_live_tup: int = 0
    n_dead_tup: int = 0
    heap_blks_read: int = 0
    heap_blks_hit: int = 0
    idx_blks_read: int = 0
    idx_blks_hit: int = 0
    
    @property
    def cache_hit_ratio(self) -> float:
        """Процент попаданий в кэш"""
        total_reads = self.heap_blks_read + self.heap_blks_hit
        if total_reads == 0:
            return 100.0
        return (self.heap_blks_hit / total_reads) * 100
    
    @property
    def index_usage_ratio(self) -> float:
        """Процент использования индексов"""
        total_scans = self.seq_scan + self.idx_scan
        if total_scans == 0:
            return 0.0
        return (self.idx_scan / total_scans) * 100
    
    @property
    def dead_tuples_ratio(self) -> float:
        """Процент мертвых кортежей"""
        total_tup = self.n_live_tup + self.n_dead_tup
        if total_tup == 0:
            return 0.0
        return (self.n_dead_tup / total_tup) * 100
    
    @property
    def hot_update_ratio(self) -> float:
        """Процент HOT обновлений"""
        if self.n_tup_upd == 0:
            return 0.0
        return (self.n_tup_hot_upd / self.n_tup_upd) * 100


@dataclass
class ConnectionStatistics:
    """Статистика соединений"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    idle_in_transaction: int = 0
    waiting_connections: int = 0
    max_connections: int = 100
    
    @property
    def utilization_percent(self) -> float:
        """Процент использования пула"""
        if self.max_connections == 0:
            return 0.0
        return (self.total_connections / self.max_connections) * 100
    
    @property
    def active_percent(self) -> float:
        """Процент активных соединений"""
        if self.total_connections == 0:
            return 0.0
        return (self.active_connections / self.total_connections) * 100


class DatabaseStatistics:
    """
    Сбор и анализ статистики БД
    
    Ответственности:
    - Сбор статистики из pg_stat_*
    - Агрегация по периодам
    - Расчет производительности
    - Генерация отчетов
    """
    
    def __init__(
        self,
        enabled: bool = True,
        collection_interval_seconds: int = 300,  # 5 минут
        retention_days: int = 30,
        
        # Что собирать
        collect_query_stats: bool = True,
        collect_table_stats: bool = True,
        collect_index_stats: bool = True,
        collect_connection_stats: bool = True,
        
        # Пороги для отчетов
        slow_query_threshold_ms: float = 1000.0,
        large_table_threshold_mb: float = 100.0,
        unused_index_threshold_scans: int = 100
    ):
        self.enabled = enabled
        self.collection_interval_seconds = collection_interval_seconds
        self.retention_days = retention_days
        
        self.collect_query_stats = collect_query_stats
        self.collect_table_stats = collect_table_stats
        self.collect_index_stats = collect_index_stats
        self.collect_connection_stats = collect_connection_stats
        
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.large_table_threshold_mb = large_table_threshold_mb
        self.unused_index_threshold_scans = unused_index_threshold_scans
        
        # Хранение статистики
        self._query_stats: Dict[str, QueryStatistics] = {}
        self._table_stats: Dict[str, TableStatistics] = {}
        self._index_stats: Dict[str, Dict[str, Any]] = {}
        self._connection_stats_history: List[Tuple[float, ConnectionStatistics]] = []
        
        # Агрегированная статистика
        self._hourly_stats: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
        self._daily_stats: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Метрики
        self._total_queries_tracked = 0
        self._total_tables_tracked = 0
        self._total_indexes_tracked = 0
        self._last_collection_time: Optional[float] = None
        
        # Отчеты
        self._reports_generated = 0
        self._last_report_time: Optional[float] = None
    
    def collect_query_statistics(self, queries_data: List[Dict[str, Any]]) -> None:
        """
        Сбор статистики запросов из pg_stat_statements
        
        Args:
            queries_data: Данные из pg_stat_statements
        """
        if not self.collect_query_stats:
            return
        
        for query_data in queries_data:
            query_hash = query_data['queryid']
            
            stats = QueryStatistics(
                query_hash=str(query_hash),
                query_text=query_data['query'],
                calls=query_data.get('calls', 0),
                total_time_ms=query_data.get('total_exec_time', 0.0),
                min_time_ms=query_data.get('min_exec_time', 0.0),
                max_time_ms=query_data.get('max_exec_time', 0.0),
                mean_time_ms=query_data.get('mean_exec_time', 0.0),
                stddev_time_ms=query_data.get('stddev_exec_time', 0.0),
                rows=query_data.get('rows', 0),
                shared_blks_hit=query_data.get('shared_blks_hit', 0),
                shared_blks_read=query_data.get('shared_blks_read', 0),
                shared_blks_written=query_data.get('shared_blks_written', 0),
                temp_blks_read=query_data.get('temp_blks_read', 0),
                temp_blks_written=query_data.get('temp_blks_written', 0),
                blk_read_time_ms=query_data.get('blk_read_time', 0.0),
                blk_write_time_ms=query_data.get('blk_write_time', 0.0)
            )
            
            self._query_stats[stats.query_hash] = stats
        
        self._total_queries_tracked = len(self._query_stats)
        self._last_collection_time = time.time()
    
    def collect_table_statistics(self, tables_data: List[Dict[str, Any]]) -> None:
        """
        Сбор статистики таблиц из pg_stat_user_tables
        
        Args:
            tables_data: Данные из pg_stat_user_tables
        """
        if not self.collect_table_stats:
            return
        
        for table_data in tables_data:
            full_name = f"{table_data['schemaname']}.{table_data['tablename']}"
            
            stats = TableStatistics(
                schema_name=table_data['schemaname'],
                table_name=table_data['tablename'],
                seq_scan=table_data.get('seq_scan', 0),
                seq_tup_read=table_data.get('seq_tup_read', 0),
                idx_scan=table_data.get('idx_scan', 0),
                idx_tup_fetch=table_data.get('idx_tup_fetch', 0),
                n_tup_ins=table_data.get('n_tup_ins', 0),
                n_tup_upd=table_data.get('n_tup_upd', 0),
                n_tup_del=table_data.get('n_tup_del', 0),
                n_tup_hot_upd=table_data.get('n_tup_hot_upd', 0),
                n_live_tup=table_data.get('n_live_tup', 0),
                n_dead_tup=table_data.get('n_dead_tup', 0),
                heap_blks_read=table_data.get('heap_blks_read', 0),
                heap_blks_hit=table_data.get('heap_blks_hit', 0),
                idx_blks_read=table_data.get('idx_blks_read', 0),
                idx_blks_hit=table_data.get('idx_blks_hit', 0)
            )
            
            self._table_stats[full_name] = stats
        
        self._total_tables_tracked = len(self._table_stats)
    
    def collect_connection_statistics(self, connection_data: Dict[str, Any]) -> None:
        """
        Сбор статистики соединений
        
        Args:
            connection_data: Данные о соединениях
        """
        if not self.collect_connection_stats:
            return
        
        stats = ConnectionStatistics(
            total_connections=connection_data.get('total', 0),
            active_connections=connection_data.get('active', 0),
            idle_connections=connection_data.get('idle', 0),
            idle_in_transaction=connection_data.get('idle_in_transaction', 0),
            waiting_connections=connection_data.get('waiting', 0),
            max_connections=connection_data.get('max_connections', 100)
        )
        
        self._connection_stats_history.append((time.time(), stats))
        
        # Очистка старых записей
        cutoff_time = time.time() - (self.retention_days * 86400)
        self._connection_stats_history = [
            (t, s) for t, s in self._connection_stats_history if t > cutoff_time
        ]
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryStatistics]:
        """
        Получение медленных запросов
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список медленных запросов
        """
        slow_queries = [
            stats for stats in self._query_stats.values()
            if stats.avg_time_ms >= self.slow_query_threshold_ms
        ]
        
        return sorted(
            slow_queries,
            key=lambda x: x.avg_time_ms,
            reverse=True
        )[:limit]
    
    def get_most_called_queries(self, limit: int = 10) -> List[QueryStatistics]:
        """
        Получение самых частых запросов
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список частых запросов
        """
        return sorted(
            self._query_stats.values(),
            key=lambda x: x.calls,
            reverse=True
        )[:limit]
    
    def get_queries_using_temp_files(self) -> List[QueryStatistics]:
        """
        Получение запросов использующих временные файлы
        
        Returns:
            Список запросов
        """
        return [
            stats for stats in self._query_stats.values()
            if stats.uses_temp_files
        ]
    
    def get_tables_with_sequential_scans(self, limit: int = 10) -> List[TableStatistics]:
        """
        Получение таблиц с частыми sequential scans
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список таблиц
        """
        return sorted(
            self._table_stats.values(),
            key=lambda x: x.seq_scan,
            reverse=True
        )[:limit]
    
    def get_tables_with_dead_tuples(self, min_percent: float = 10.0) -> List[TableStatistics]:
        """
        Получение таблиц с мертвыми кортежами
        
        Args:
            min_percent: Минимальный процент dead tuples
            
        Returns:
            Список таблиц
        """
        return [
            stats for stats in self._table_stats.values()
            if stats.dead_tuples_ratio >= min_percent
        ]
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Генерация отчета о производительности
        
        Returns:
            Словарь с отчетом
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': 'current',
            
            # Запросы
            'query_statistics': {
                'total_queries': len(self._query_stats),
                'slow_queries_count': len([
                    q for q in self._query_stats.values()
                    if q.avg_time_ms >= self.slow_query_threshold_ms
                ]),
                'queries_with_temp_files': len(self.get_queries_using_temp_files()),
                'top_slow_queries': [
                    {
                        'query': q.query_text[:100],
                        'avg_time_ms': q.avg_time_ms,
                        'calls': q.calls,
                        'cache_hit_ratio': q.cache_hit_ratio
                    }
                    for q in self.get_slow_queries(5)
                ],
                'top_frequent_queries': [
                    {
                        'query': q.query_text[:100],
                        'calls': q.calls,
                        'total_time_ms': q.total_time_ms,
                        'avg_time_ms': q.avg_time_ms
                    }
                    for q in self.get_most_called_queries(5)
                ]
            },
            
            # Таблицы
            'table_statistics': {
                'total_tables': len(self._table_stats),
                'tables_with_dead_tuples': len(self.get_tables_with_dead_tuples()),
                'avg_cache_hit_ratio': sum(
                    t.cache_hit_ratio for t in self._table_stats.values()
                ) / max(1, len(self._table_stats)),
                'tables_needing_vacuum': [
                    {
                        'table': f"{t.schema_name}.{t.table_name}",
                        'dead_tuples_ratio': t.dead_tuples_ratio,
                        'n_dead_tup': t.n_dead_tup
                    }
                    for t in self.get_tables_with_dead_tuples()[:5]
                ],
                'tables_with_seq_scans': [
                    {
                        'table': f"{t.schema_name}.{t.table_name}",
                        'seq_scan': t.seq_scan,
                        'index_usage_ratio': t.index_usage_ratio
                    }
                    for t in self.get_tables_with_sequential_scans(5)
                ]
            },
            
            # Соединения
            'connection_statistics': self._get_connection_summary()
        }
        
        self._reports_generated += 1
        self._last_report_time = time.time()
        
        return report
    
    def _get_connection_summary(self) -> Dict[str, Any]:
        """Получение сводки по соединениям"""
        if not self._connection_stats_history:
            return {}
        
        recent_stats = [s for _, s in self._connection_stats_history[-12:]]  # Последний час
        
        return {
            'current_total': recent_stats[-1].total_connections if recent_stats else 0,
            'current_active': recent_stats[-1].active_connections if recent_stats else 0,
            'current_utilization': recent_stats[-1].utilization_percent if recent_stats else 0.0,
            'avg_total': sum(s.total_connections for s in recent_stats) / len(recent_stats),
            'avg_active': sum(s.active_connections for s in recent_stats) / len(recent_stats),
            'avg_utilization': sum(s.utilization_percent for s in recent_stats) / len(recent_stats),
            'max_total': max(s.total_connections for s in recent_stats),
            'max_connections_limit': recent_stats[-1].max_connections if recent_stats else 100
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик статистики"""
        hours_since_collection = 0.0
        if self._last_collection_time:
            hours_since_collection = (time.time() - self._last_collection_time) / 3600
        
        hours_since_report = 0.0
        if self._last_report_time:
            hours_since_report = (time.time() - self._last_report_time) / 3600
        
        return {
            'enabled': self.enabled,
            'total_queries_tracked': self._total_queries_tracked,
            'total_tables_tracked': self._total_tables_tracked,
            'total_indexes_tracked': self._total_indexes_tracked,
            'connection_history_size': len(self._connection_stats_history),
            'hours_since_collection': hours_since_collection,
            'reports_generated': self._reports_generated,
            'hours_since_report': hours_since_report,
            'retention_days': self.retention_days
        }