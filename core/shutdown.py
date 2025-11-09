# core/shutdown.py
"""
Shutdown Manager - Graceful остановка приложения
"""

import asyncio
from typing import Optional
from core.logging_config import get_logger
from core.tasks.manager import TaskManager
from core.initialization.database import DatabaseInitializer
from core.monitor import IntegratedCryptoMonitor

logger = get_logger(__name__)


class ShutdownManager:
    """
    Управление graceful shutdown
    
    Координирует остановку всех компонентов в правильном порядке
    """
    
    def __init__(
        self,
        task_manager: TaskManager,
        db_initializer: DatabaseInitializer,
        monitor: Optional[IntegratedCryptoMonitor] = None
    ):
        """
        Args:
            task_manager: Менеджер задач
            db_initializer: Инициализатор БД
            monitor: Монитор (опционально)
        """
        self.task_manager = task_manager
        self.db_initializer = db_initializer
        self.monitor = monitor
        self.shutdown_in_progress = False
    
    async def shutdown(self) -> None:
        """Выполнение graceful shutdown"""
        if self.shutdown_in_progress:
            logger.warning("Shutdown already in progress")
            return
        
        self.shutdown_in_progress = True
        
        try:
            # Шаг 1: Останавливаем задачи
            await self._stop_tasks()
            
            # Шаг 2: Останавливаем мониторинг
            await self._stop_monitor()
            
            # Шаг 3: Закрываем БД
            await self._close_database()
            
            logger.info("✅ All components stopped successfully")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    async def _stop_tasks(self) -> None:
        """Остановка всех задач"""
        try:
            logger.info("Stopping tasks...")
            await self.task_manager.stop_all()
            logger.info("✅ Tasks stopped")
        
        except Exception as e:
            logger.error(f"Error stopping tasks: {e}", exc_info=True)
    
    async def _stop_monitor(self) -> None:
        """Остановка мониторинга"""
        if not self.monitor:
            return
        
        try:
            logger.info("Stopping monitor...")
            # Если у монитора есть метод stop
            if hasattr(self.monitor, 'stop'):
                await self.monitor.stop()
            logger.info("✅ Monitor stopped")
        
        except Exception as e:
            logger.error(f"Error stopping monitor: {e}", exc_info=True)
    
    async def _close_database(self) -> None:
        """Закрытие БД"""
        try:
            db_manager = self.db_initializer.get_manager()
            if db_manager and db_manager.is_initialized:
                logger.info("Closing database...")
                db_manager.close()
                logger.info("✅ Database closed")
        
        except Exception as e:
            logger.error(f"Error closing database: {e}", exc_info=True)