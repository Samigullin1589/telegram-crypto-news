# app/whales/publisher/metrics.py
"""
Publishing Metrics
"""

from datetime import datetime, timezone
from typing import Optional, Dict


class PublishingMetrics:
    """Метрики публикации"""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful = 0
        self.failed = 0
        self.markdown_fallbacks = 0
        self.errors_by_type = {}
        self.last_publish_time = None
    
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
    
    def get_success_rate(self) -> float:
        """Получение процента успешных публикаций"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful / self.total_attempts) * 100
    
    def to_dict(self) -> Dict:
        """Экспорт метрик в словарь"""
        return {
            "total_attempts": self.total_attempts,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.get_success_rate(),
            "markdown_fallbacks": self.markdown_fallbacks,
            "errors_by_type": dict(self.errors_by_type),
            "last_publish_time": self.last_publish_time.isoformat() if self.last_publish_time else None
        }


__all__ = ['PublishingMetrics']