# app/scheduler/whale_components/metrics_collector.py
"""
Metrics Collector
Сбор и агрегация метрик работы системы
"""

import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Сборщик метрик системы мониторинга"""
    
    def __init__(self):
        """Инициализация счётчиков"""
        self.events_fetched = 0
        self.events_qualified = 0
        self.events_queued = 0
        self.events_published = 0
        
        self.cycle_count = 0
        self.error_count = 0
        
        self.filtering_stats = {}
        
        self.start_time = datetime.utcnow()
    
    def reset_cycle(self):
        """Сброс метрик для нового цикла"""
        self.events_fetched = 0
        self.events_qualified = 0
        self.events_queued = 0
        self.events_published = 0
        
        self.filtering_stats = {}
    
    def record_filtering_reason(self, reason: str):
        """
        Запись причины фильтрации
        
        Args:
            reason: Причина фильтрации
        """
        if reason not in self.filtering_stats:
            self.filtering_stats[reason] = 0
        self.filtering_stats[reason] += 1
    
    def record_error(self):
        """Запись ошибки"""
        self.error_count += 1
    
    def increment_cycle_count(self):
        """Увеличение счётчика циклов"""
        self.cycle_count += 1
    
    def get_filtering_stats(self) -> Dict:
        """
        Получение статистики фильтрации
        
        Returns:
            Dict с причинами фильтрации и их количеством
        """
        return self.filtering_stats.copy()
    
    def get_summary(self) -> Dict:
        """
        Получение общей статистики
        
        Returns:
            Dict с агрегированными метриками
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'total_cycles': self.cycle_count,
            'total_errors': self.error_count,
            'uptime_seconds': round(uptime, 2),
            'current_cycle': {
                'fetched': self.events_fetched,
                'qualified': self.events_qualified,
                'queued': self.events_queued,
                'published': self.events_published
            }
        }
    
    def get_funnel_stats(self) -> Dict:
        """
        Получение статистики воронки обработки
        
        Returns:
            Dict с процентами прохождения на каждом этапе
        """
        if self.events_fetched == 0:
            return {
                'qualification_rate': 0,
                'queue_rate': 0,
                'publication_rate': 0
            }
        
        return {
            'qualification_rate': round(
                (self.events_qualified / self.events_fetched) * 100, 2
            ),
            'queue_rate': round(
                (self.events_queued / self.events_fetched) * 100, 2
            ),
            'publication_rate': round(
                (self.events_published / self.events_fetched) * 100, 2
            )
        }