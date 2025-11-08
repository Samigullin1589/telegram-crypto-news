"""
Компонент управления партиционированием таблиц

Архитектурные решения:
- Автоматическое создание партиций на основе времени
- Удаление устаревших партиций по retention policy
- Мониторинг размеров партиций
- Балансировка данных между партициями
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class PartitionStrategy(Enum):
    """Стратегии партиционирования"""
    RANGE = 'range'  # По диапазону (обычно время)
    LIST = 'list'    # По списку значений
    HASH = 'hash'    # По хэшу


class PartitionPeriod(Enum):
    """Период партиций"""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'


@dataclass
class PartitionInfo:
    """Информация о партиции"""
    name: str
    table_name: str
    strategy: PartitionStrategy
    period: PartitionPeriod
    start_date: datetime
    end_date: datetime
    size_bytes: int
    row_count: int
    is_current: bool = False
    is_future: bool = False
    
    @property
    def size_mb(self) -> float:
        """Размер в мегабайтах"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def age_days(self) -> int:
        """Возраст партиции в днях"""
        return (datetime.now() - self.start_date).days
    
    @property
    def is_expired(self) -> bool:
        """Истекла ли партиция"""
        return datetime.now() > self.end_date


class PartitionConfig:
    """
    Конфигурация и управление партиционированием
    
    Ответственности:
    - Автосоздание партиций на будущее
    - Удаление устаревших партиций
    - Мониторинг баланса данных
    - Архивирование старых партиций
    """
    
    def __init__(
        self,
        enabled: bool = True,
        strategy: PartitionStrategy = PartitionStrategy.RANGE,
        period: PartitionPeriod = PartitionPeriod.MONTHLY,
        retention_months: int = 12,
        auto_create_future: bool = True,
        future_partitions_count: int = 3,
        auto_drop_expired: bool = False,
        archive_before_drop: bool = True,
        rebalance_threshold_percent: float = 20.0
    ):
        self.enabled = enabled
        self.strategy = strategy
        self.period = period
        self.retention_months = retention_months
        self.auto_create_future = auto_create_future
        self.future_partitions_count = future_partitions_count
        self.auto_drop_expired = auto_drop_expired
        self.archive_before_drop = archive_before_drop
        self.rebalance_threshold_percent = rebalance_threshold_percent
        
        # Метрики
        self._total_partitions = 0
        self._active_partitions = 0
        self._expired_partitions = 0
        self._future_partitions = 0
        self._total_size_bytes = 0
        self._total_rows = 0
        
        # Кэш партиций
        self._partitions_cache: Dict[str, PartitionInfo] = {}
        self._last_scan_time: Optional[float] = None
        
        # История операций
        self._partitions_created: List[str] = []
        self._partitions_dropped: List[str] = []
        self._partitions_archived: List[str] = []
        
        # Статистика балансировки
        self._rebalance_operations = 0
        self._last_rebalance_time: Optional[float] = None
    
    def analyze_partitions(self, partitions_data: List[Dict[str, Any]]) -> None:
        """
        Анализ партиций на основе данных из БД
        
        Args:
            partitions_data: Список словарей с данными партиций
        """
        self._last_scan_time = time.time()
        self._partitions_cache.clear()
        
        current_date = datetime.now()
        
        for part_data in partitions_data:
            partition = PartitionInfo(
                name=part_data['partition_name'],
                table_name=part_data['table_name'],
                strategy=PartitionStrategy(part_data.get('strategy', 'range')),
                period=PartitionPeriod(part_data.get('period', 'monthly')),
                start_date=part_data['start_date'],
                end_date=part_data['end_date'],
                size_bytes=part_data['size_bytes'],
                row_count=part_data['row_count']
            )
            
            # Определение статуса партиции
            partition.is_current = (
                partition.start_date <= current_date < partition.end_date
            )
            partition.is_future = partition.start_date > current_date
            
            self._partitions_cache[partition.name] = partition
        
        # Обновление агрегированных метрик
        self._update_aggregated_metrics()
    
    def _update_aggregated_metrics(self) -> None:
        """Обновление агрегированных метрик"""
        self._total_partitions = len(self._partitions_cache)
        self._active_partitions = 0
        self._expired_partitions = 0
        self._future_partitions = 0
        self._total_size_bytes = 0
        self._total_rows = 0
        
        for partition in self._partitions_cache.values():
            self._total_size_bytes += partition.size_bytes
            self._total_rows += partition.row_count
            
            if partition.is_current:
                self._active_partitions += 1
            elif partition.is_future:
                self._future_partitions += 1
            elif partition.is_expired:
                self._expired_partitions += 1
    
    def get_partitions_to_create(self) -> List[Tuple[str, datetime, datetime]]:
        """
        Получение списка партиций для создания
        
        Returns:
            Список кортежей (имя_партиции, start_date, end_date)
        """
        if not self.auto_create_future:
            return []
        
        partitions_to_create = []
        current_date = datetime.now()
        
        # Определяем последнюю существующую дату
        max_end_date = current_date
        for partition in self._partitions_cache.values():
            if partition.end_date > max_end_date:
                max_end_date = partition.end_date
        
        # Создаем будущие партиции
        for i in range(self.future_partitions_count):
            start_date = self._calculate_next_period_start(max_end_date, i)
            end_date = self._calculate_period_end(start_date)
            
            partition_name = self._generate_partition_name(start_date)
            
            # Проверяем, что партиция еще не существует
            if partition_name not in self._partitions_cache:
                partitions_to_create.append((partition_name, start_date, end_date))
        
        return partitions_to_create
    
    def get_expired_partitions(self) -> List[PartitionInfo]:
        """
        Получение устаревших партиций для удаления
        
        Returns:
            Список устаревших партиций
        """
        if not self.auto_drop_expired:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_months * 30)
        
        return [
            partition for partition in self._partitions_cache.values()
            if partition.end_date < cutoff_date
        ]
    
    def _calculate_next_period_start(self, from_date: datetime, offset: int = 0) -> datetime:
        """
        Расчет начала следующего периода
        
        Args:
            from_date: Дата, от которой считать
            offset: Смещение периодов
            
        Returns:
            Дата начала периода
        """
        if self.period == PartitionPeriod.DAILY:
            return from_date + timedelta(days=1 + offset)
        elif self.period == PartitionPeriod.WEEKLY:
            return from_date + timedelta(weeks=1 + offset)
        elif self.period == PartitionPeriod.MONTHLY:
            # Первый день следующего месяца
            month = from_date.month + 1 + offset
            year = from_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            return datetime(year, month, 1)
        elif self.period == PartitionPeriod.QUARTERLY:
            # Первый день следующего квартала
            quarter = (from_date.month - 1) // 3 + 1 + offset
            year = from_date.year + (quarter - 1) // 4
            quarter = ((quarter - 1) % 4) + 1
            month = (quarter - 1) * 3 + 1
            return datetime(year, month, 1)
        elif self.period == PartitionPeriod.YEARLY:
            return datetime(from_date.year + 1 + offset, 1, 1)
        
        return from_date
    
    def _calculate_period_end(self, start_date: datetime) -> datetime:
        """
        Расчет конца периода
        
        Args:
            start_date: Дата начала периода
            
        Returns:
            Дата конца периода
        """
        if self.period == PartitionPeriod.DAILY:
            return start_date + timedelta(days=1)
        elif self.period == PartitionPeriod.WEEKLY:
            return start_date + timedelta(weeks=1)
        elif self.period == PartitionPeriod.MONTHLY:
            # Последний день месяца
            if start_date.month == 12:
                return datetime(start_date.year + 1, 1, 1)
            else:
                return datetime(start_date.year, start_date.month + 1, 1)
        elif self.period == PartitionPeriod.QUARTERLY:
            # Последний день квартала
            month = ((start_date.month - 1) // 3 + 1) * 3
            if month == 12:
                return datetime(start_date.year + 1, 1, 1)
            else:
                return datetime(start_date.year, month + 1, 1)
        elif self.period == PartitionPeriod.YEARLY:
            return datetime(start_date.year + 1, 1, 1)
        
        return start_date
    
    def _generate_partition_name(self, start_date: datetime) -> str:
        """
        Генерация имени партиции
        
        Args:
            start_date: Дата начала периода
            
        Returns:
            Имя партиции
        """
        if self.period == PartitionPeriod.DAILY:
            return f"partition_{start_date.strftime('%Y%m%d')}"
        elif self.period == PartitionPeriod.WEEKLY:
            return f"partition_{start_date.strftime('%Y_w%W')}"
        elif self.period == PartitionPeriod.MONTHLY:
            return f"partition_{start_date.strftime('%Y%m')}"
        elif self.period == PartitionPeriod.QUARTERLY:
            quarter = (start_date.month - 1) // 3 + 1
            return f"partition_{start_date.year}_q{quarter}"
        elif self.period == PartitionPeriod.YEARLY:
            return f"partition_{start_date.year}"
        
        return f"partition_{start_date.strftime('%Y%m%d')}"
    
    def check_balance(self) -> Dict[str, Any]:
        """
        Проверка баланса данных между партициями
        
        Returns:
            Словарь с информацией о балансе
        """
        if not self._partitions_cache:
            return {'balanced': True, 'imbalance_percent': 0.0}
        
        # Средний размер партиции
        avg_size = self._total_size_bytes / len(self._partitions_cache)
        
        # Находим максимальное отклонение
        max_deviation_percent = 0.0
        unbalanced_partitions = []
        
        for partition in self._partitions_cache.values():
            if avg_size == 0:
                deviation_percent = 0.0
            else:
                deviation_percent = abs(partition.size_bytes - avg_size) / avg_size * 100
            
            if deviation_percent > self.rebalance_threshold_percent:
                unbalanced_partitions.append({
                    'name': partition.name,
                    'deviation_percent': deviation_percent,
                    'size_mb': partition.size_mb,
                    'avg_size_mb': avg_size / (1024 * 1024)
                })
            
            if deviation_percent > max_deviation_percent:
                max_deviation_percent = deviation_percent
        
        return {
            'balanced': max_deviation_percent <= self.rebalance_threshold_percent,
            'imbalance_percent': max_deviation_percent,
            'avg_size_mb': avg_size / (1024 * 1024),
            'unbalanced_partitions': unbalanced_partitions,
            'threshold_percent': self.rebalance_threshold_percent
        }
    
    def record_partition_operation(
        self,
        operation: str,
        partition_name: str
    ) -> None:
        """
        Запись операции над партицией
        
        Args:
            operation: Тип операции ('create', 'drop', 'archive')
            partition_name: Имя партиции
        """
        if operation == 'create':
            self._partitions_created.append(partition_name)
        elif operation == 'drop':
            self._partitions_dropped.append(partition_name)
            self._partitions_cache.pop(partition_name, None)
        elif operation == 'archive':
            self._partitions_archived.append(partition_name)
    
    def record_rebalance(self) -> None:
        """Запись операции ребалансировки"""
        self._rebalance_operations += 1
        self._last_rebalance_time = time.time()
    
    def get_partition_info(self, partition_name: str) -> Optional[PartitionInfo]:
        """
        Получение информации о партиции
        
        Args:
            partition_name: Имя партиции
            
        Returns:
            Информация о партиции или None
        """
        return self._partitions_cache.get(partition_name)
    
    def get_storage_forecast(self, months_ahead: int = 6) -> Dict[str, Any]:
        """
        Прогноз использования хранилища
        
        Args:
            months_ahead: Месяцев для прогноза
            
        Returns:
            Прогноз хранилища
        """
        if not self._partitions_cache:
            return {'forecast_gb': 0.0, 'growth_rate_percent': 0.0}
        
        # Расчет среднего роста на основе последних партиций
        recent_partitions = sorted(
            [p for p in self._partitions_cache.values() if not p.is_future],
            key=lambda x: x.start_date,
            reverse=True
        )[:3]  # Последние 3 партиции
        
        if len(recent_partitions) < 2:
            growth_rate = 0.0
        else:
            # Средний размер последних партиций
            avg_recent_size = sum(p.size_bytes for p in recent_partitions) / len(recent_partitions)
            # Средний размер всех партиций
            avg_total_size = self._total_size_bytes / len(self._partitions_cache)
            # Процент роста
            if avg_total_size > 0:
                growth_rate = ((avg_recent_size - avg_total_size) / avg_total_size) * 100
            else:
                growth_rate = 0.0
        
        # Прогноз
        current_size_gb = self._total_size_bytes / (1024 * 1024 * 1024)
        forecast_gb = current_size_gb * (1 + (growth_rate / 100)) ** months_ahead
        
        return {
            'current_size_gb': current_size_gb,
            'forecast_gb': forecast_gb,
            'growth_rate_percent': growth_rate,
            'months_ahead': months_ahead,
            'additional_gb_needed': forecast_gb - current_size_gb
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик партиционирования"""
        hours_since_scan = 0.0
        if self._last_scan_time:
            hours_since_scan = (time.time() - self._last_scan_time) / 3600
        
        hours_since_rebalance = 0.0
        if self._last_rebalance_time:
            hours_since_rebalance = (time.time() - self._last_rebalance_time) / 3600
        
        balance_info = self.check_balance()
        
        return {
            'enabled': self.enabled,
            'strategy': self.strategy.value,
            'period': self.period.value,
            'total_partitions': self._total_partitions,
            'active_partitions': self._active_partitions,
            'expired_partitions': self._expired_partitions,
            'future_partitions': self._future_partitions,
            'total_size_mb': self._total_size_bytes / (1024 * 1024),
            'total_size_gb': self._total_size_bytes / (1024 * 1024 * 1024),
            'total_rows': self._total_rows,
            'hours_since_scan': hours_since_scan,
            'retention_months': self.retention_months,
            'partitions_created': len(self._partitions_created),
            'partitions_dropped': len(self._partitions_dropped),
            'partitions_archived': len(self._partitions_archived),
            'rebalance_operations': self._rebalance_operations,
            'hours_since_rebalance': hours_since_rebalance,
            'balanced': balance_info['balanced'],
            'imbalance_percent': balance_info['imbalance_percent']
        }