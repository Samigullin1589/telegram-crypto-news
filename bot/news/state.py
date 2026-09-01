# bot/news/state.py
"""
News Processor State Management
Управление состоянием процессора новостей
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional


@dataclass
class ProcessorState:
    """Состояние процессора новостей"""
    
    # Статусы инициализации
    core_initialized: bool = False
    database_initialized: bool = False
    baseline_loaded: bool = False
    
    # Статистика
    posts_this_hour: int = 0
    hour_start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_articles_fetched: int = 0
    total_articles_posted: int = 0
    total_filtered_quality: int = 0
    total_filtered_cooldown: int = 0
    total_filtered_batch_limit: int = 0
    total_cycles: int = 0
    last_post_time: Optional[datetime] = None
    
    # Контроль
    shutdown_requested: bool = False
    last_cycle_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consecutive_errors: int = 0
    
    def reset_hourly_stats(self):
        """Сброс почасовой статистики"""
        self.posts_this_hour = 0
        self.hour_start_time = datetime.now(timezone.utc)
    
    def check_hour_reset(self) -> bool:
        """Проверка нужен ли сброс почасовых счетчиков"""
        now = datetime.now(timezone.utc)
        if (now - self.hour_start_time).total_seconds() >= 3600:
            self.reset_hourly_stats()
            return True
        return False
    
    def increment_cycle(self):
        """Увеличить счетчик циклов"""
        self.total_cycles += 1
        self.last_cycle_time = datetime.now(timezone.utc)
        self.consecutive_errors = 0
    
    def increment_error(self):
        """Увеличить счетчик ошибок"""
        self.consecutive_errors += 1
    
    def is_ready(self) -> bool:
        """Проверка готовности процессора к работе"""
        return (
            self.core_initialized 
            and not self.shutdown_requested
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация состояния в словарь"""
        return {
            'core_initialized': self.core_initialized,
            'database_initialized': self.database_initialized,
            'baseline_loaded': self.baseline_loaded,
            'posts_this_hour': self.posts_this_hour,
            'total_cycles': self.total_cycles,
            'total_articles_fetched': self.total_articles_fetched,
            'total_articles_posted': self.total_articles_posted,
            'total_filtered_quality': self.total_filtered_quality,
            'total_filtered_cooldown': self.total_filtered_cooldown,
            'total_filtered_batch_limit': self.total_filtered_batch_limit,
            'last_post_time': (
                self.last_post_time.isoformat() if self.last_post_time else None
            ),
            'consecutive_errors': self.consecutive_errors,
            'is_ready': self.is_ready()
        }


class ProcessorLogger:
    """Логирование для процессора"""
    
    @staticmethod
    def log_header(title: str):
        """Вывод заголовка"""
        print("\n" + "="*80)
        print(f"📰 {title}")
        print("="*80 + "\n")
    
    @staticmethod
    def log_success(message: str):
        """Успешное действие"""
        print(f"✅ {message}")
    
    @staticmethod
    def log_info(message: str):
        """Информационное сообщение"""
        print(f"   • {message}")
    
    @staticmethod
    def log_warning(message: str):
        """Предупреждение"""
        print(f"⚠️  {message}")
    
    @staticmethod
    def log_error(message: str):
        """Ошибка"""
        print(f"❌ {message}")
    
    @staticmethod
    def log_section_end():
        """Конец секции"""
        print()