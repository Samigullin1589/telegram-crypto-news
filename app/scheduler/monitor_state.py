# app/scheduler/monitor_state.py
"""
Whale Monitor State Management
Управление состоянием монитора
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class MonitorState:
    """
    Состояние монитора whale транзакций
    
    Отслеживает:
    - Статус инициализации
    - Здоровье системы
    - Метрики обработки
    - История циклов
    """
    
    # Статусы
    is_initialized: bool = False
    is_healthy: bool = True
    
    # Временные метки
    initialized_at: Optional[datetime] = None
    last_cycle_time: Optional[datetime] = None
    
    # Метрики
    total_cycles: int = 0
    total_events_processed: int = 0
    total_events_published: int = 0
    total_errors: int = 0
    
    # Кэш просмотренных событий
    seen_keys: set = field(default_factory=set)
    
    def update_from_cycle(self, cycle_result: Dict[str, Any]):
        """
        Обновление состояния на основе результата цикла
        
        Args:
            cycle_result: Результат выполнения цикла
        """
        self.total_cycles += 1
        self.last_cycle_time = datetime.utcnow()
        
        if cycle_result.get('success'):
            metrics = cycle_result.get('metrics', {})
            self.total_events_processed += metrics.get('events_fetched', 0)
            self.total_events_published += metrics.get('events_published', 0)
        else:
            self.total_errors += 1
            self.is_healthy = False
    
    def reset(self):
        """Сброс состояния"""
        self.total_cycles = 0
        self.total_events_processed = 0
        self.total_events_published = 0
        self.total_errors = 0
        self.seen_keys.clear()
        self.is_healthy = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация состояния в словарь"""
        return {
            'is_initialized': self.is_initialized,
            'is_healthy': self.is_healthy,
            'initialized_at': (
                self.initialized_at.isoformat()
                if self.initialized_at
                else None
            ),
            'last_cycle_time': (
                self.last_cycle_time.isoformat()
                if self.last_cycle_time
                else None
            ),
            'total_cycles': self.total_cycles,
            'total_events_processed': self.total_events_processed,
            'total_events_published': self.total_events_published,
            'total_errors': self.total_errors,
            'seen_events_count': len(self.seen_keys)
        }


__all__ = ['MonitorState']