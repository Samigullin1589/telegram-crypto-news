# core/tasks/task_health.py
"""
Task Health Monitoring
Мониторинг здоровья задач
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TaskHealthMonitor:
    """
    Мониторинг здоровья задач
    
    Периодическая проверка системы
    """
    
    def __init__(self, health_monitor: Any, resource_monitor: Any):
        """
        Инициализация health monitor
        
        Args:
            health_monitor: Системный монитор здоровья
            resource_monitor: Монитор ресурсов
        """
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.check_interval = getattr(health_monitor, 'check_interval', 300)
    
    async def run_health_checks(self):
        """Запуск проверок здоровья"""
        # Начальная задержка
        await asyncio.sleep(self.check_interval)
        
        shutdown_event = getattr(self.health_monitor, 'shutdown_event', None)
        
        while True:
            try:
                # Проверка shutdown
                if shutdown_event and shutdown_event.is_set():
                    break
                
                await self._health_check_tick()
                await asyncio.sleep(self.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [HEALTH] Check error: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
        
        logger.info("💚 [HEALTH] Health monitor stopped")
    
    async def _health_check_tick(self):
        """Один тик проверки здоровья"""
        # Проверка здоровья системы
        is_healthy, issues = self.health_monitor.check_health()
        
        if not is_healthy:
            self._log_health_issues(issues)
        
        # Проверка памяти
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.resource_monitor.check_memory
        )
    
    def _log_health_issues(self, issues: list):
        """Логирование проблем со здоровьем"""
        logger.warning("\n" + "=" * 80)
        logger.warning("⚠️  [HEALTH] DETECTED ISSUES:")
        logger.warning("=" * 80)
        
        for issue in issues:
            logger.warning(f"   {issue}")
        
        logger.warning("=" * 80 + "\n")


__all__ = ['TaskHealthMonitor']