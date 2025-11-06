# app/whales/publish/metrics.py
"""
Publishing Metrics System
Tracks success rates, errors, and performance
"""

from datetime import datetime, timezone
from typing import Dict, Optional


class PublishingMetrics:
    """Метрики публикации"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful = 0
        self.failed = 0
        self.markdown_fallbacks = 0
        self.errors_by_type: Dict[str, int] = {}
        self.last_publish_time: Optional[datetime] = None
    
    def record_attempt(self, success: bool, error_type: Optional[str] = None):
        """Регистрация попытки публикации"""
        self.total_attempts += 1
        
        if success:
            self.successful += 1
            self.last_publish_time = datetime.now(timezone.utc)
        else:
            self.failed += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def record_markdown_fallback(self):
        """Регистрация использования fallback без форматирования"""
        self.markdown_fallbacks += 1
    
    def get_success_rate(self) -> float:
        """Получение процента успешных публикаций"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful / self.total_attempts) * 100
    
    def get_stats(self) -> Dict:
        """Получение всей статистики"""
        return {
            "total_attempts": self.total_attempts,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.get_success_rate(),
            "markdown_fallbacks": self.markdown_fallbacks,
            "errors_by_type": dict(self.errors_by_type),
            "last_publish_time": self.last_publish_time.isoformat() if self.last_publish_time else None
        }
    
    def print_stats(self):
        """Вывод статистики в консоль"""
        stats = self.get_stats()
        
        print("\n" + "="*80)
        print("📊 PUBLISHER STATISTICS")
        print("="*80)
        print(f"Total Attempts:    {stats['total_attempts']}")
        print(f"Successful:        {stats['successful']}")
        print(f"Failed:            {stats['failed']}")
        print(f"Success Rate:      {stats['success_rate']:.1f}%")
        print(f"Markdown Fallback: {stats['markdown_fallbacks']}")
        
        if stats['errors_by_type']:
            print("\nErrors by Type:")
            for error_type, count in stats['errors_by_type'].items():
                print(f"  • {error_type}: {count}")
        
        print("="*80 + "\n")
    
    def reset(self):
        """Сброс всех метрик"""
        self.total_attempts = 0
        self.successful = 0
        self.failed = 0
        self.markdown_fallbacks = 0
        self.errors_by_type.clear()
        self.last_publish_time = None