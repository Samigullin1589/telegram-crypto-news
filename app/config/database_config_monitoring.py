"""
Database Configuration Monitoring
Мониторинг, метрики и здоровье конфигурации БД
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .database_config_core import DatabaseConfig
    from .database.enums import HealthStatus

logger = logging.getLogger(__name__)


class DatabaseConfigMonitoring:
    """Миксин для мониторинга и метрик конфигурации"""
    
    def get_status(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Получение полного статуса конфигурации и менеджера
        
        Returns:
            Словарь со статусом
        """
        status = {
            'initialized': self._initialized,
            'config': self.to_dict(mask_sensitive=True),
            'diagnostic_info': self.get_diagnostic_info()
        }
        
        # Добавляем статус менеджера если есть
        if self._manager is not None:
            status['manager'] = self.manager.get_status()
            status['health'] = self.manager.get_health_status().value
        else:
            status['manager'] = None
            status['health'] = 'unknown'
        
        return status
    
    def get_metrics(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Получение метрик конфигурации и менеджера
        
        Returns:
            Словарь с метриками
        """
        metrics = {
            'config': {
                'engine': self.engine.value,
                'pool_size': f"{self.pool.min_size}-{self.pool.max_size}",
                'ssl_enabled': self.ssl.enabled,
                'monitoring_enabled': self.monitoring.enabled
            }
        }
        
        # Добавляем метрики менеджера если есть
        if self._manager is not None:
            metrics['manager'] = self.manager.get_metrics()
        
        return metrics
    
    def get_health_status(self: 'DatabaseConfig') -> 'HealthStatus':
        """
        Получение статуса здоровья
        
        Returns:
            Статус здоровья системы
        """
        from .database.enums import HealthStatus
        
        if not self._initialized:
            return HealthStatus.UNKNOWN
        
        if self._manager is not None:
            return self.manager.get_health_status()
        
        return HealthStatus.HEALTHY
    
    def get_alerts(self: 'DatabaseConfig', active_only: bool = True) -> Dict[str, Any]:
        """
        Получение алертов
        
        Args:
            active_only: Только активные алерты
            
        Returns:
            Словарь с алертами
        """
        if self._manager is None:
            return {'alerts': [], 'total': 0}
        
        return self.manager.get_alerts(active_only)
    
    async def health_check(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Выполнение проверки здоровья
        
        Returns:
            Результаты проверки
        """
        if self._manager is None:
            return {
                'healthy': False,
                'reason': 'manager_not_initialized'
            }
        
        return await self.manager.health_check()
    
    def get_performance_stats(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Получение статистики производительности
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            'config_enabled': {
                'query_logging': self.enable_query_logging,
                'performance_tracking': self.enable_performance_tracking,
                'connection_pooling': self.enable_connection_pooling,
                'auto_vacuum': self.enable_auto_vacuum,
                'auto_analyze': self.enable_auto_analyze
            }
        }
        
        if self._manager is not None:
            stats['manager'] = self.manager.get_metrics()
        
        return stats


__all__ = ['DatabaseConfigMonitoring']