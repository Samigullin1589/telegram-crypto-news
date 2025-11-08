"""
Компонент управления кэшированием запросов и результатов

Архитектурные решения:
- Многоуровневое кэширование: memory -> Redis -> DB
- Адаптивное TTL на основе частоты доступа
- LRU/LFU эвикция с приоритизацией
- Умная инвалидация при изменениях
- Предзагрузка горячих данных
- Мониторинг эффективности кэша
"""

import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple


class CacheLevel(Enum):
    """Уровни кэша"""
    MEMORY = 'memory'  # In-memory кэш приложения
    REDIS = 'redis'    # Redis кэш
    DB = 'database'    # Кэш результатов в БД


class EvictionPolicy(Enum):
    """Политики вытеснения"""
    LRU = 'lru'    # Least Recently Used
    LFU = 'lfu'    # Least Frequently Used
    TTL = 'ttl'    # Time To Live
    MIXED = 'mixed'  # Комбинированная


@dataclass
class CacheEntry:
    """Запись в кэше"""
    key: str
    value_size_bytes: int
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl_seconds: int = 300
    level: CacheLevel = CacheLevel.MEMORY
    priority: int = 0  # 0=low, 1=normal, 2=high
    
    @property
    def age_seconds(self) -> float:
        """Возраст записи"""
        return time.time() - self.created_at
    
    @property
    def time_since_access(self) -> float:
        """Время с последнего доступа"""
        return time.time() - self.last_accessed
    
    @property
    def is_expired(self) -> bool:
        """Истекла ли запись"""
        return self.age_seconds > self.ttl_seconds
    
    @property
    def value_size_mb(self) -> float:
        """Размер в мегабайтах"""
        return self.value_size_bytes / (1024 * 1024)


@dataclass
class HotKey:
    """Горячий ключ"""
    key: str
    access_count: int
    last_access: float
    avg_value_size_bytes: int
    recommended_ttl: int
    
    @property
    def access_frequency(self) -> float:
        """Частота доступа (обращений в час)"""
        hours = max(1.0, (time.time() - self.last_access) / 3600)
        return self.access_count / hours


class CacheConfig:
    """
    Конфигурация и управление кэшированием
    
    Ответственности:
    - Управление памятью кэша
    - Адаптивное TTL
    - Эвикция записей
    - Предзагрузка данных
    - Мониторинг эффективности
    - Инвалидация при изменениях
    """
    
    def __init__(
        self,
        enabled: bool = True,
        
        # Размеры кэша
        memory_cache_size_mb: int = 256,
        redis_enabled: bool = True,
        redis_cache_size_mb: int = 1024,
        
        # TTL настройки
        default_ttl_seconds: int = 300,
        min_ttl_seconds: int = 60,
        max_ttl_seconds: int = 3600,
        adaptive_ttl: bool = True,
        
        # Эвикция
        eviction_policy: EvictionPolicy = EvictionPolicy.MIXED,
        memory_pressure_threshold: float = 0.85,  # 85% заполнения
        
        # Предзагрузка
        preload_hot_data: bool = True,
        hot_key_threshold: int = 10,  # Обращений для hot key
        preload_on_startup: bool = True,
        
        # Приоритизация
        use_priorities: bool = True,
        high_priority_preserve_percent: float = 0.3,  # 30% для high priority
        
        # Мониторинг
        track_access_patterns: bool = True,
        access_pattern_window_hours: int = 24
    ):
        self.enabled = enabled
        self.memory_cache_size_mb = memory_cache_size_mb
        self.redis_enabled = redis_enabled
        self.redis_cache_size_mb = redis_cache_size_mb
        
        self.default_ttl_seconds = default_ttl_seconds
        self.min_ttl_seconds = min_ttl_seconds
        self.max_ttl_seconds = max_ttl_seconds
        self.adaptive_ttl = adaptive_ttl
        
        self.eviction_policy = eviction_policy
        self.memory_pressure_threshold = memory_pressure_threshold
        
        self.preload_hot_data = preload_hot_data
        self.hot_key_threshold = hot_key_threshold
        self.preload_on_startup = preload_on_startup
        
        self.use_priorities = use_priorities
        self.high_priority_preserve_percent = high_priority_preserve_percent
        
        self.track_access_patterns = track_access_patterns
        self.access_pattern_window_hours = access_pattern_window_hours
        
        # Кэш записей
        self._memory_entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._redis_entries: Dict[str, CacheEntry] = {}
        
        # Метрики доступа
        self._total_requests = 0
        self._memory_hits = 0
        self._redis_hits = 0
        self._cache_misses = 0
        self._current_memory_bytes = 0
        self._current_redis_bytes = 0
        
        # Эвикция
        self._evictions_count = 0
        self._evictions_by_ttl = 0
        self._evictions_by_size = 0
        self._evictions_by_lru = 0
        
        # Горячие ключи
        self._hot_keys: Dict[str, HotKey] = {}
        self._access_history: Dict[str, List[float]] = {}  # key -> [timestamps]
        
        # Инвалидация
        self._invalidation_patterns: Set[str] = set()  # Паттерны для инвалидации
        self._total_invalidations = 0
    
    @property
    def memory_utilization_percent(self) -> float:
        """Использование памяти"""
        max_bytes = self.memory_cache_size_mb * 1024 * 1024
        if max_bytes == 0:
            return 0.0
        return (self._current_memory_bytes / max_bytes) * 100
    
    @property
    def redis_utilization_percent(self) -> float:
        """Использование Redis"""
        if not self.redis_enabled:
            return 0.0
        max_bytes = self.redis_cache_size_mb * 1024 * 1024
        if max_bytes == 0:
            return 0.0
        return (self._current_redis_bytes / max_bytes) * 100
    
    @property
    def hit_rate_percent(self) -> float:
        """Процент попаданий в кэш"""
        if self._total_requests == 0:
            return 0.0
        total_hits = self._memory_hits + self._redis_hits
        return (total_hits / self._total_requests) * 100
    
    @property
    def memory_hit_rate_percent(self) -> float:
        """Процент попаданий в memory кэш"""
        if self._total_requests == 0:
            return 0.0
        return (self._memory_hits / self._total_requests) * 100
    
    def record_access(
        self,
        key: str,
        hit: bool,
        level: Optional[CacheLevel] = None,
        value_size_bytes: int = 0
    ) -> None:
        """
        Запись обращения к кэшу
        
        Args:
            key: Ключ кэша
            hit: Попадание или промах
            level: Уровень кэша где найдено
            value_size_bytes: Размер значения
        """
        self._total_requests += 1
        current_time = time.time()
        
        if hit:
            if level == CacheLevel.MEMORY:
                self._memory_hits += 1
                # Обновление LRU порядка
                if key in self._memory_entries:
                    entry = self._memory_entries[key]
                    entry.last_accessed = current_time
                    entry.access_count += 1
                    # Перемещение в конец (most recently used)
                    self._memory_entries.move_to_end(key)
            
            elif level == CacheLevel.REDIS:
                self._redis_hits += 1
                if key in self._redis_entries:
                    entry = self._redis_entries[key]
                    entry.last_accessed = current_time
                    entry.access_count += 1
        else:
            self._cache_misses += 1
        
        # Отслеживание паттернов доступа
        if self.track_access_patterns:
            self._track_access(key, current_time, value_size_bytes, hit)
        
        # Обновление горячих ключей
        self._update_hot_keys(key, current_time, value_size_bytes)
    
    def _track_access(
        self,
        key: str,
        timestamp: float,
        value_size: int,
        hit: bool
    ) -> None:
        """Отслеживание паттерна доступа"""
        if key not in self._access_history:
            self._access_history[key] = []
        
        self._access_history[key].append(timestamp)
        
        # Очистка старых записей
        cutoff = timestamp - (self.access_pattern_window_hours * 3600)
        self._access_history[key] = [
            t for t in self._access_history[key] if t > cutoff
        ]
    
    def _update_hot_keys(
        self,
        key: str,
        timestamp: float,
        value_size: int
    ) -> None:
        """Обновление информации о горячих ключах"""
        if key in self._hot_keys:
            hot_key = self._hot_keys[key]
            hot_key.access_count += 1
            hot_key.last_access = timestamp
            # Экспоненциальное сглаживание размера
            hot_key.avg_value_size_bytes = int(
                0.9 * hot_key.avg_value_size_bytes + 0.1 * value_size
            )
        else:
            # Создание новой записи
            hot_key = HotKey(
                key=key,
                access_count=1,
                last_access=timestamp,
                avg_value_size_bytes=value_size,
                recommended_ttl=self.default_ttl_seconds
            )
            self._hot_keys[key] = hot_key
        
        # Расчет рекомендуемого TTL
        if self.adaptive_ttl:
            hot_key.recommended_ttl = self._calculate_adaptive_ttl(hot_key)
    
    def _calculate_adaptive_ttl(self, hot_key: HotKey) -> int:
        """
        Расчет адаптивного TTL на основе паттернов доступа
        
        Args:
            hot_key: Горячий ключ
            
        Returns:
            Рекомендуемый TTL в секундах
        """
        # Частота доступа определяет TTL
        frequency = hot_key.access_frequency
        
        if frequency > 100:  # Очень частый доступ (>100/час)
            ttl = self.max_ttl_seconds
        elif frequency > 10:  # Частый доступ
            ttl = self.default_ttl_seconds * 2
        elif frequency > 1:  # Умеренный доступ
            ttl = self.default_ttl_seconds
        else:  # Редкий доступ
            ttl = self.min_ttl_seconds
        
        # Ограничение диапазона
        return max(self.min_ttl_seconds, min(ttl, self.max_ttl_seconds))
    
    def put(
        self,
        key: str,
        value_size_bytes: int,
        level: CacheLevel = CacheLevel.MEMORY,
        priority: int = 0,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Добавление записи в кэш
        
        Args:
            key: Ключ
            value_size_bytes: Размер значения
            level: Уровень кэша
            priority: Приоритет (0=low, 1=normal, 2=high)
            ttl: TTL в секундах (None = адаптивный)
            
        Returns:
            True если добавлено
        """
        if not self.enabled:
            return False
        
        # Определение TTL
        if ttl is None:
            if key in self._hot_keys:
                ttl = self._hot_keys[key].recommended_ttl
            else:
                ttl = self.default_ttl_seconds
        
        current_time = time.time()
        
        entry = CacheEntry(
            key=key,
            value_size_bytes=value_size_bytes,
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl_seconds=ttl,
            level=level,
            priority=priority
        )
        
        if level == CacheLevel.MEMORY:
            # Проверка давления памяти
            if self._needs_eviction(value_size_bytes, CacheLevel.MEMORY):
                self._evict_entries(value_size_bytes, CacheLevel.MEMORY)
            
            self._memory_entries[key] = entry
            self._current_memory_bytes += value_size_bytes
            
        elif level == CacheLevel.REDIS and self.redis_enabled:
            if self._needs_eviction(value_size_bytes, CacheLevel.REDIS):
                self._evict_entries(value_size_bytes, CacheLevel.REDIS)
            
            self._redis_entries[key] = entry
            self._current_redis_bytes += value_size_bytes
        
        return True
    
    def _needs_eviction(self, new_size: int, level: CacheLevel) -> bool:
        """
        Нужна ли эвикция
        
        Args:
            new_size: Размер новой записи
            level: Уровень кэша
            
        Returns:
            True если нужна эвикция
        """
        if level == CacheLevel.MEMORY:
            max_bytes = self.memory_cache_size_mb * 1024 * 1024
            current = self._current_memory_bytes
        elif level == CacheLevel.REDIS:
            max_bytes = self.redis_cache_size_mb * 1024 * 1024
            current = self._current_redis_bytes
        else:
            return False
        
        future_utilization = (current + new_size) / max_bytes
        return future_utilization > self.memory_pressure_threshold
    
    def _evict_entries(self, space_needed: int, level: CacheLevel) -> None:
        """
        Вытеснение записей из кэша
        
        Args:
            space_needed: Сколько места нужно освободить
            level: Уровень кэша
        """
        if level == CacheLevel.MEMORY:
            entries = self._memory_entries
        elif level == CacheLevel.REDIS:
            entries = self._redis_entries
        else:
            return
        
        space_freed = 0
        keys_to_remove = []
        
        # Выбор стратегии эвикции
        if self.eviction_policy == EvictionPolicy.LRU:
            # Удаляем least recently used (начало OrderedDict)
            for key, entry in entries.items():
                if self.use_priorities and entry.priority >= 2:
                    continue  # Сохраняем high priority
                keys_to_remove.append(key)
                space_freed += entry.value_size_bytes
                if space_freed >= space_needed:
                    break
        
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Сортируем по частоте доступа
            sorted_entries = sorted(
                entries.items(),
                key=lambda x: x[1].access_count
            )
            for key, entry in sorted_entries:
                if self.use_priorities and entry.priority >= 2:
                    continue
                keys_to_remove.append(key)
                space_freed += entry.value_size_bytes
                if space_freed >= space_needed:
                    break
        
        elif self.eviction_policy == EvictionPolicy.TTL:
            # Удаляем истекшие и самые старые
            sorted_entries = sorted(
                entries.items(),
                key=lambda x: x[1].age_seconds,
                reverse=True
            )
            for key, entry in sorted_entries:
                if self.use_priorities and entry.priority >= 2:
                    continue
                keys_to_remove.append(key)
                space_freed += entry.value_size_bytes
                if space_freed >= space_needed:
                    break
        
        elif self.eviction_policy == EvictionPolicy.MIXED:
            # Комбинированный подход
            # 1. Сначала удаляем истекшие
            for key, entry in list(entries.items()):
                if entry.is_expired:
                    keys_to_remove.append(key)
                    space_freed += entry.value_size_bytes
                    self._evictions_by_ttl += 1
            
            # 2. Затем LRU для низкого приоритета
            if space_freed < space_needed:
                for key, entry in entries.items():
                    if key in keys_to_remove:
                        continue
                    if entry.priority == 0:  # Low priority
                        keys_to_remove.append(key)
                        space_freed += entry.value_size_bytes
                        self._evictions_by_lru += 1
                        if space_freed >= space_needed:
                            break
            
            # 3. Затем LRU для нормального приоритета
            if space_freed < space_needed:
                for key, entry in entries.items():
                    if key in keys_to_remove or entry.priority >= 2:
                        continue
                    keys_to_remove.append(key)
                    space_freed += entry.value_size_bytes
                    self._evictions_by_lru += 1
                    if space_freed >= space_needed:
                        break
        
        # Удаление выбранных записей
        for key in keys_to_remove:
            entry = entries[key]
            del entries[key]
            
            if level == CacheLevel.MEMORY:
                self._current_memory_bytes -= entry.value_size_bytes
            elif level == CacheLevel.REDIS:
                self._current_redis_bytes -= entry.value_size_bytes
            
            self._evictions_count += 1
            self._evictions_by_size += 1
    
    def invalidate(self, pattern: str) -> int:
        """
        Инвалидация записей по паттерну
        
        Args:
            pattern: Паттерн для поиска ключей
            
        Returns:
            Количество инвалидированных записей
        """
        invalidated = 0
        
        # Memory cache
        keys_to_remove = [
            key for key in self._memory_entries.keys()
            if pattern in key
        ]
        for key in keys_to_remove:
            entry = self._memory_entries[key]
            del self._memory_entries[key]
            self._current_memory_bytes -= entry.value_size_bytes
            invalidated += 1
        
        # Redis cache
        if self.redis_enabled:
            keys_to_remove = [
                key for key in self._redis_entries.keys()
                if pattern in key
            ]
            for key in keys_to_remove:
                entry = self._redis_entries[key]
                del self._redis_entries[key]
                self._current_redis_bytes -= entry.value_size_bytes
                invalidated += 1
        
        self._total_invalidations += invalidated
        return invalidated
    
    def get_hot_keys(self, top_n: int = 10) -> List[HotKey]:
        """
        Получение топ N горячих ключей
        
        Args:
            top_n: Количество ключей
            
        Returns:
            Список горячих ключей
        """
        return sorted(
            self._hot_keys.values(),
            key=lambda x: x.access_frequency,
            reverse=True
        )[:top_n]
    
    def should_preload_key(self, key: str) -> bool:
        """
        Нужна ли предзагрузка ключа
        
        Args:
            key: Ключ для проверки
            
        Returns:
            True если нужна предзагрузка
        """
        if not self.preload_hot_data:
            return False
        
        hot_key = self._hot_keys.get(key)
        if not hot_key:
            return False
        
        return hot_key.access_count >= self.hot_key_threshold
    
    def cleanup_expired(self) -> int:
        """
        Очистка истекших записей
        
        Returns:
            Количество удаленных записей
        """
        removed = 0
        
        # Memory cache
        keys_to_remove = [
            key for key, entry in self._memory_entries.items()
            if entry.is_expired
        ]
        for key in keys_to_remove:
            entry = self._memory_entries[key]
            del self._memory_entries[key]
            self._current_memory_bytes -= entry.value_size_bytes
            removed += 1
            self._evictions_by_ttl += 1
        
        # Redis cache
        if self.redis_enabled:
            keys_to_remove = [
                key for key, entry in self._redis_entries.items()
                if entry.is_expired
            ]
            for key in keys_to_remove:
                entry = self._redis_entries[key]
                del self._redis_entries[key]
                self._current_redis_bytes -= entry.value_size_bytes
                removed += 1
                self._evictions_by_ttl += 1
        
        return removed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик кэширования"""
        return {
            'enabled': self.enabled,
            
            # Запросы
            'total_requests': self._total_requests,
            'memory_hits': self._memory_hits,
            'redis_hits': self._redis_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': self.hit_rate_percent,
            'memory_hit_rate_percent': self.memory_hit_rate_percent,
            
            # Размеры
            'memory_entries_count': len(self._memory_entries),
            'redis_entries_count': len(self._redis_entries),
            'memory_size_mb': self._current_memory_bytes / (1024 * 1024),
            'redis_size_mb': self._current_redis_bytes / (1024 * 1024),
            'memory_utilization_percent': self.memory_utilization_percent,
            'redis_utilization_percent': self.redis_utilization_percent,
            
            # Эвикция
            'total_evictions': self._evictions_count,
            'evictions_by_ttl': self._evictions_by_ttl,
            'evictions_by_size': self._evictions_by_size,
            'evictions_by_lru': self._evictions_by_lru,
            
            # Горячие ключи
            'hot_keys_count': len(self._hot_keys),
            'preload_enabled': self.preload_hot_data,
            
            # Инвалидация
            'total_invalidations': self._total_invalidations,
            
            # Настройки
            'adaptive_ttl': self.adaptive_ttl,
            'eviction_policy': self.eviction_policy.value,
            'default_ttl_seconds': self.default_ttl_seconds
        }