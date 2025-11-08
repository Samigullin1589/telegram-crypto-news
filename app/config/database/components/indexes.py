"""
Компонент управления индексами PostgreSQL

Архитектурные решения:
- Анализ использования индексов на основе pg_stat_user_indexes
- Обнаружение неиспользуемых индексов (0 scans за период)
- Обнаружение дублирующихся индексов
- Рекомендации по созданию составных индексов
- Мониторинг bloat в индексах
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta


class IndexType(Enum):
    """Типы индексов PostgreSQL"""
    BTREE = 'btree'
    HASH = 'hash'
    GIN = 'gin'
    GIST = 'gist'
    SPGIST = 'spgist'
    BRIN = 'brin'


class IndexHealth(Enum):
    """Состояние здоровья индекса"""
    HEALTHY = 'healthy'
    UNUSED = 'unused'
    DUPLICATE = 'duplicate'
    BLOATED = 'bloated'
    MISSING = 'missing'


@dataclass
class IndexMetrics:
    """Метрики индекса"""
    name: str
    table_name: str
    index_type: IndexType
    size_bytes: int
    scans: int = 0
    tuples_read: int = 0
    tuples_fetched: int = 0
    bloat_percent: float = 0.0
    last_used: Optional[datetime] = None
    health: IndexHealth = IndexHealth.HEALTHY
    duplicate_of: Optional[str] = None
    
    @property
    def size_mb(self) -> float:
        """Размер в мегабайтах"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def is_used(self) -> bool:
        """Используется ли индекс"""
        return self.scans > 0
    
    @property
    def efficiency(self) -> float:
        """Эффективность индекса (fetched/read ratio)"""
        if self.tuples_read == 0:
            return 0.0
        return (self.tuples_fetched / self.tuples_read) * 100


@dataclass
class IndexRecommendation:
    """Рекомендация по индексу"""
    action: str  # 'create', 'drop', 'rebuild', 'analyze'
    index_name: Optional[str]
    table_name: str
    columns: List[str]
    reason: str
    impact: str  # 'high', 'medium', 'low'
    estimated_size_mb: float = 0.0
    estimated_improvement: str = ''


class IndexConfig:
    """
    Конфигурация и управление индексами БД
    
    Ответственности:
    - Мониторинг использования индексов
    - Обнаружение проблемных индексов
    - Генерация рекомендаций по оптимизации
    - Отслеживание метрик производительности
    """
    
    def __init__(
        self,
        enabled: bool = True,
        auto_analyze: bool = True,
        unused_threshold_days: int = 30,
        bloat_threshold_percent: float = 30.0,
        min_index_size_mb: float = 10.0,
        check_duplicates: bool = True,
        suggest_missing: bool = True,
        rebuild_bloated: bool = False
    ):
        self.enabled = enabled
        self.auto_analyze = auto_analyze
        self.unused_threshold_days = unused_threshold_days
        self.bloat_threshold_percent = bloat_threshold_percent
        self.min_index_size_mb = min_index_size_mb
        self.check_duplicates = check_duplicates
        self.suggest_missing = suggest_missing
        self.rebuild_bloated = rebuild_bloated
        
        # Метрики
        self._total_indexes = 0
        self._healthy_indexes = 0
        self._unused_indexes = 0
        self._duplicate_indexes = 0
        self._bloated_indexes = 0
        self._total_index_size_bytes = 0
        
        # Кэш индексов
        self._indexes_cache: Dict[str, IndexMetrics] = {}
        self._last_scan_time: Optional[float] = None
        self._recommendations: List[IndexRecommendation] = []
        
        # История
        self._indexes_dropped: List[str] = []
        self._indexes_created: List[str] = []
        self._indexes_rebuilt: List[str] = []
    
    def analyze_indexes(self, indexes_data: List[Dict[str, Any]]) -> None:
        """
        Анализ индексов на основе данных из БД
        
        Args:
            indexes_data: Список словарей с данными индексов из pg_stat_user_indexes
        """
        self._last_scan_time = time.time()
        self._indexes_cache.clear()
        
        for idx_data in indexes_data:
            metrics = IndexMetrics(
                name=idx_data['indexname'],
                table_name=idx_data['tablename'],
                index_type=IndexType(idx_data.get('type', 'btree')),
                size_bytes=idx_data['size_bytes'],
                scans=idx_data.get('idx_scan', 0),
                tuples_read=idx_data.get('idx_tup_read', 0),
                tuples_fetched=idx_data.get('idx_tup_fetch', 0),
                bloat_percent=idx_data.get('bloat_percent', 0.0),
                last_used=idx_data.get('last_used')
            )
            
            # Определение здоровья
            metrics.health = self._determine_health(metrics)
            
            self._indexes_cache[metrics.name] = metrics
        
        # Обновление агрегированных метрик
        self._update_aggregated_metrics()
        
        # Генерация рекомендаций
        if self.enabled:
            self._generate_recommendations()
    
    def _determine_health(self, metrics: IndexMetrics) -> IndexHealth:
        """
        Определение состояния здоровья индекса
        
        Args:
            metrics: Метрики индекса
            
        Returns:
            Состояние здоровья
        """
        # Проверка на bloat
        if metrics.bloat_percent >= self.bloat_threshold_percent:
            return IndexHealth.BLOATED
        
        # Проверка на использование
        if metrics.scans == 0:
            if metrics.last_used:
                days_unused = (datetime.now() - metrics.last_used).days
                if days_unused >= self.unused_threshold_days:
                    return IndexHealth.UNUSED
            else:
                # Индекс никогда не использовался
                return IndexHealth.UNUSED
        
        return IndexHealth.HEALTHY
    
    def _update_aggregated_metrics(self) -> None:
        """Обновление агрегированных метрик"""
        self._total_indexes = len(self._indexes_cache)
        self._healthy_indexes = 0
        self._unused_indexes = 0
        self._bloated_indexes = 0
        self._total_index_size_bytes = 0
        
        for metrics in self._indexes_cache.values():
            self._total_index_size_bytes += metrics.size_bytes
            
            if metrics.health == IndexHealth.HEALTHY:
                self._healthy_indexes += 1
            elif metrics.health == IndexHealth.UNUSED:
                self._unused_indexes += 1
            elif metrics.health == IndexHealth.BLOATED:
                self._bloated_indexes += 1
            elif metrics.health == IndexHealth.DUPLICATE:
                self._duplicate_indexes += 1
    
    def _generate_recommendations(self) -> None:
        """Генерация рекомендаций по оптимизации индексов"""
        self._recommendations.clear()
        
        # Рекомендации по удалению неиспользуемых индексов
        if self.check_duplicates:
            for metrics in self._indexes_cache.values():
                if metrics.health == IndexHealth.UNUSED and metrics.size_mb >= self.min_index_size_mb:
                    self._recommendations.append(IndexRecommendation(
                        action='drop',
                        index_name=metrics.name,
                        table_name=metrics.table_name,
                        columns=[],
                        reason=f'Индекс не используется более {self.unused_threshold_days} дней',
                        impact='high',
                        estimated_size_mb=metrics.size_mb,
                        estimated_improvement=f'Освободит {metrics.size_mb:.2f} MB'
                    ))
        
        # Рекомендации по перестройке bloated индексов
        if self.rebuild_bloated:
            for metrics in self._indexes_cache.values():
                if metrics.health == IndexHealth.BLOATED and metrics.size_mb >= self.min_index_size_mb:
                    estimated_reduction = metrics.size_mb * (metrics.bloat_percent / 100)
                    self._recommendations.append(IndexRecommendation(
                        action='rebuild',
                        index_name=metrics.name,
                        table_name=metrics.table_name,
                        columns=[],
                        reason=f'Индекс раздут на {metrics.bloat_percent:.1f}%',
                        impact='medium',
                        estimated_size_mb=metrics.size_mb,
                        estimated_improvement=f'Сократит размер на ~{estimated_reduction:.2f} MB'
                    ))
    
    def find_duplicate_indexes(self) -> List[Tuple[str, str]]:
        """
        Поиск дублирующихся индексов
        
        Returns:
            Список кортежей (индекс1, индекс2) дубликатов
        """
        if not self.check_duplicates:
            return []
        
        duplicates = []
        processed = set()
        
        for name1, metrics1 in self._indexes_cache.items():
            if name1 in processed:
                continue
                
            for name2, metrics2 in self._indexes_cache.items():
                if name1 == name2 or name2 in processed:
                    continue
                
                # Одна таблица, одинаковый тип
                if (metrics1.table_name == metrics2.table_name and 
                    metrics1.index_type == metrics2.index_type):
                    
                    # В реальности нужно сравнить колонки индексов
                    # Здесь упрощенная проверка
                    duplicates.append((name1, name2))
                    processed.add(name1)
                    processed.add(name2)
        
        return duplicates
    
    def get_inefficient_indexes(self, min_efficiency: float = 50.0) -> List[IndexMetrics]:
        """
        Получение неэффективных индексов
        
        Args:
            min_efficiency: Минимальная эффективность в процентах
            
        Returns:
            Список метрик неэффективных индексов
        """
        return [
            metrics for metrics in self._indexes_cache.values()
            if metrics.is_used and metrics.efficiency < min_efficiency
        ]
    
    def get_large_indexes(self, min_size_mb: float = 100.0) -> List[IndexMetrics]:
        """
        Получение больших индексов
        
        Args:
            min_size_mb: Минимальный размер в MB
            
        Returns:
            Список метрик больших индексов
        """
        return sorted(
            [m for m in self._indexes_cache.values() if m.size_mb >= min_size_mb],
            key=lambda x: x.size_bytes,
            reverse=True
        )
    
    def should_rebuild_index(self, index_name: str) -> bool:
        """
        Нужна ли перестройка индекса
        
        Args:
            index_name: Имя индекса
            
        Returns:
            True если перестройка рекомендуется
        """
        if not self.rebuild_bloated or index_name not in self._indexes_cache:
            return False
        
        metrics = self._indexes_cache[index_name]
        return (
            metrics.health == IndexHealth.BLOATED and 
            metrics.size_mb >= self.min_index_size_mb
        )
    
    def record_index_operation(self, operation: str, index_name: str) -> None:
        """
        Запись операции над индексом
        
        Args:
            operation: Тип операции ('create', 'drop', 'rebuild')
            index_name: Имя индекса
        """
        if operation == 'create':
            self._indexes_created.append(index_name)
        elif operation == 'drop':
            self._indexes_dropped.append(index_name)
            # Удаление из кэша
            self._indexes_cache.pop(index_name, None)
        elif operation == 'rebuild':
            self._indexes_rebuilt.append(index_name)
    
    def get_recommendations(self, priority: Optional[str] = None) -> List[IndexRecommendation]:
        """
        Получение рекомендаций
        
        Args:
            priority: Фильтр по приоритету ('high', 'medium', 'low')
            
        Returns:
            Список рекомендаций
        """
        if priority:
            return [r for r in self._recommendations if r.impact == priority]
        return self._recommendations.copy()
    
    def get_index_metrics(self, index_name: str) -> Optional[IndexMetrics]:
        """
        Получение метрик индекса
        
        Args:
            index_name: Имя индекса
            
        Returns:
            Метрики индекса или None
        """
        return self._indexes_cache.get(index_name)
    
    def estimate_maintenance_impact(self) -> Dict[str, Any]:
        """
        Оценка влияния обслуживания индексов
        
        Returns:
            Словарь с оценками
        """
        total_reclaimable_mb = sum(
            m.size_mb for m in self._indexes_cache.values()
            if m.health == IndexHealth.UNUSED
        )
        
        total_bloat_mb = sum(
            m.size_mb * (m.bloat_percent / 100)
            for m in self._indexes_cache.values()
            if m.health == IndexHealth.BLOATED
        )
        
        return {
            'total_reclaimable_mb': total_reclaimable_mb,
            'total_bloat_mb': total_bloat_mb,
            'unused_indexes_count': self._unused_indexes,
            'bloated_indexes_count': self._bloated_indexes,
            'duplicate_indexes_count': self._duplicate_indexes,
            'total_recommendations': len(self._recommendations),
            'high_priority_recommendations': len([r for r in self._recommendations if r.impact == 'high'])
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик управления индексами"""
        hours_since_scan = 0.0
        if self._last_scan_time:
            hours_since_scan = (time.time() - self._last_scan_time) / 3600
        
        return {
            'enabled': self.enabled,
            'total_indexes': self._total_indexes,
            'healthy_indexes': self._healthy_indexes,
            'unused_indexes': self._unused_indexes,
            'duplicate_indexes': self._duplicate_indexes,
            'bloated_indexes': self._bloated_indexes,
            'total_size_mb': self._total_index_size_bytes / (1024 * 1024),
            'total_size_gb': self._total_index_size_bytes / (1024 * 1024 * 1024),
            'hours_since_scan': hours_since_scan,
            'recommendations_count': len(self._recommendations),
            'indexes_created': len(self._indexes_created),
            'indexes_dropped': len(self._indexes_dropped),
            'indexes_rebuilt': len(self._indexes_rebuilt),
            'auto_analyze': self.auto_analyze,
            'unused_threshold_days': self.unused_threshold_days,
            'bloat_threshold_percent': self.bloat_threshold_percent
        }