# core/tasks/task_lifecycle.py
"""
Task Lifecycle Management
Управление жизненным циклом задач
"""

import asyncio
import logging
import gc
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskLifecycle:
    """
    Управление жизненным циклом задач
    
    Координация и обслуживание задач
    """
    
    def __init__(self, shutdown_event: asyncio.Event):
        """
        Инициализация lifecycle manager
        
        Args:
            shutdown_event: Event для shutdown
        """
        self.shutdown_event = shutdown_event
        self.last_gc = datetime.now(timezone.utc)
        self.gc_runs = 0
        self.gc_interval = 300  # 5 минут
    
    async def run_coordination(self):
        """Координационный цикл"""
        # Начальная задержка
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                await self._coordination_tick()
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [COORDINATOR] Error: {e}", exc_info=True)
                await asyncio.sleep(60)
        
        logger.info("🔄 [COORDINATOR] Coordinator stopped")
    
    async def _coordination_tick(self):
        """Один тик координации"""
        now = datetime.now(timezone.utc)
        time_since_gc = (now - self.last_gc).seconds
        
        # Garbage collection
        if time_since_gc > self.gc_interval:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._run_garbage_collection
            )
    
    def _run_garbage_collection(self):
        """Запуск garbage collection"""
        gc.collect()
        self.last_gc = datetime.now(timezone.utc)
        self.gc_runs += 1
        logger.debug(f"🗑️  [GC] Collection #{self.gc_runs} completed")
    
    async def wait_for_shutdown(self):
        """Ожидание сигнала shutdown"""
        await self.shutdown_event.wait()
        logger.info("✅ [SHUTDOWN] Shutdown signal received")


__all__ = ['TaskLifecycle']