# app/whales/monitor/components/monitor_stats.py
"""
Monitor Statistics
Сбор и агрегация статистики мониторинга
"""

import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class MonitorStats:
    """Статистика работы монитора"""
    
    def __init__(self):
        """Инициализация счётчиков"""
        self.total_events = 0
        self.total_errors = 0
        self.events_by_chain = {}
        self.scan_start_time = None
        self.scan_end_time = None
        
        logger.debug("🔧 [STATS] Инициализирован")
    
    def reset(self):
        """Сброс всех счётчиков"""
        self.total_events = 0
        self.total_errors = 0
        self.events_by_chain = {}
        self.scan_start_time = datetime.utcnow()
        self.scan_end_time = None
    
    def add_events(self, count: int):
        """
        Добавление событий к общему счётчику
        
        Args:
            count: Количество событий
        """
        self.total_events += count
    
    def add_chain_events(self, chain: str, count: int):
        """
        Добавление событий для конкретного chain
        
        Args:
            chain: Название блокчейна
            count: Количество событий
        """
        if chain not in self.events_by_chain:
            self.events_by_chain[chain] = 0
        
        self.events_by_chain[chain] += count
    
    def increment_errors(self):
        """Увеличение счётчика ошибок"""
        self.total_errors += 1
    
    def finalize_scan(self):
        """Завершение сканирования"""
        self.scan_end_time = datetime.utcnow()
    
    def get_summary(self) -> Dict:
        """
        Получение сводной статистики
        
        Returns:
            Dict со статистикой
        """
        summary = {
            'total_events': self.total_events,
            'total_errors': self.total_errors,
            'events_by_chain': self.events_by_chain.copy()
        }
        
        if self.scan_start_time and self.scan_end_time:
            duration = (self.scan_end_time - self.scan_start_time).total_seconds()
            summary['scan_duration_seconds'] = round(duration, 2)
            
            if duration > 0:
                summary['events_per_second'] = round(
                    self.total_events / duration, 2
                )
        
        return summary
    
    def log_summary(self):
        """Вывод статистики в лог"""
        summary = self.get_summary()
        
        logger.info("📊 [STATS] Сводная статистика:")
        logger.info(f"  • Всего событий: {summary['total_events']}")
        logger.info(f"  • Ошибок: {summary['total_errors']}")
        
        if summary['events_by_chain']:
            logger.info("  • По chains:")
            for chain, count in summary['events_by_chain'].items():
                logger.info(f"    - {chain}: {count}")
        
        if 'scan_duration_seconds' in summary:
            logger.info(f"  • Длительность: {summary['scan_duration_seconds']}s")
        
        if 'events_per_second' in summary:
            logger.info(f"  • Скорость: {summary['events_per_second']} events/s")