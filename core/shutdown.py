# core/shutdown.py
"""
Shutdown Manager
Graceful остановка приложения

Выполняет:
- Координацию остановки всех компонентов
- Правильную последовательность shutdown
- Обработку таймаутов
- Логирование процесса остановки
"""

import asyncio
from typing import Any, Optional, TYPE_CHECKING
from core.logging_config import get_logger
from core.tasks.manager import TaskManager
from core.initialization.database import DatabaseInitializer

# ИСПРАВЛЕНО: TYPE_CHECKING для избежания циклического импорта
if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor

logger = get_logger(__name__)


class ShutdownManager:
    """
    Менеджер graceful shutdown приложения
    
    Координирует остановку всех компонентов системы в правильном порядке,
    обеспечивая корректное освобождение ресурсов и сохранение данных.
    
    Порядок остановки:
    1. Остановка фоновых задач (TaskManager)
    2. Остановка мониторинга (IntegratedCryptoMonitor)
    3. Закрытие соединений с БД (DatabaseManager)
    
    Attributes:
        task_manager: Менеджер фоновых задач
        db_initializer: Инициализатор базы данных
        monitor: Система мониторинга (опционально)
        shutdown_timeout: Максимальное время на shutdown каждого компонента
        shutdown_in_progress: Флаг выполнения shutdown
    """
    
    # Таймауты для каждого этапа (в секундах)
    DEFAULT_TASK_SHUTDOWN_TIMEOUT = 30
    DEFAULT_MONITOR_SHUTDOWN_TIMEOUT = 15
    DEFAULT_DATABASE_SHUTDOWN_TIMEOUT = 10
    
    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        db_initializer: Optional[DatabaseInitializer] = None,
        monitor: Optional['IntegratedCryptoMonitor'] = None,
        db_manager: Optional[Any] = None,
        task_shutdown_timeout: int = DEFAULT_TASK_SHUTDOWN_TIMEOUT,
        monitor_shutdown_timeout: int = DEFAULT_MONITOR_SHUTDOWN_TIMEOUT,
        database_shutdown_timeout: int = DEFAULT_DATABASE_SHUTDOWN_TIMEOUT
    ):
        """
        Инициализация shutdown manager
        
        Args:
            task_manager: Менеджер задач для остановки
            db_initializer: Инициализатор БД для закрытия соединений
            monitor: Монитор для остановки (опционально)
            task_shutdown_timeout: Таймаут остановки задач (секунды)
            monitor_shutdown_timeout: Таймаут остановки монитора (секунды)
            database_shutdown_timeout: Таймаут закрытия БД (секунды)
        """
        self.task_manager = task_manager
        self.db_initializer = db_initializer
        self.db_manager = db_manager
        self.monitor = monitor
        
        # Таймауты
        self.task_shutdown_timeout = task_shutdown_timeout
        self.monitor_shutdown_timeout = monitor_shutdown_timeout
        self.database_shutdown_timeout = database_shutdown_timeout
        
        # Состояние
        self.shutdown_in_progress = False
        self.shutdown_completed = False
        
        logger.debug(
            f"ShutdownManager initialized with timeouts: "
            f"tasks={task_shutdown_timeout}s, "
            f"monitor={monitor_shutdown_timeout}s, "
            f"database={database_shutdown_timeout}s"
        )
    
    async def shutdown(self) -> bool:
        """
        Выполнение полного graceful shutdown
        
        Останавливает все компоненты системы в правильном порядке
        с соблюдением таймаутов и обработкой ошибок.
        
        Returns:
            True если все компоненты остановлены успешно
        """
        if self.shutdown_in_progress:
            logger.warning("⚠️ Shutdown already in progress, skipping duplicate call")
            return False
        
        if self.shutdown_completed:
            logger.warning("⚠️ Shutdown already completed")
            return True
        
        self.shutdown_in_progress = True
        
        logger.info("="*80)
        logger.info("🛑 Starting graceful shutdown sequence...")
        logger.info("="*80)
        
        shutdown_success = True
        
        try:
            # Шаг 1: Останавливаем фоновые задачи
            if not await self._stop_tasks():
                shutdown_success = False
            
            # Шаг 2: Останавливаем мониторинг
            if not await self._stop_monitor():
                shutdown_success = False
            
            # Шаг 3: Закрываем базу данных
            if not await self._close_database():
                shutdown_success = False
            
            if shutdown_success:
                logger.info("="*80)
                logger.info("✅ Graceful shutdown completed successfully")
                logger.info("="*80)
            else:
                logger.warning("="*80)
                logger.warning("⚠️ Shutdown completed with some errors")
                logger.warning("="*80)
            
            self.shutdown_completed = True
            return shutdown_success
        
        except Exception as e:
            logger.error(
                f"❌ Critical error during shutdown sequence: {e}",
                exc_info=True
            )
            return False
        
        finally:
            self.shutdown_in_progress = False
    
    async def _stop_tasks(self) -> bool:
        """
        Остановка всех фоновых задач
        
        Останавливает TaskManager с соблюдением таймаута.
        
        Returns:
            True если задачи остановлены успешно
        """
        try:
            logger.info("📋 Step 1/3: Stopping background tasks...")
            
            if not self.task_manager:
                logger.warning("⚠️ TaskManager is None, skipping")
                return True
            
            # Останавливаем задачи с таймаутом
            try:
                await asyncio.wait_for(
                    self.task_manager.stop_all(),
                    timeout=self.task_shutdown_timeout
                )
                logger.info("✅ Background tasks stopped successfully")
                return True
            
            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Task shutdown timeout ({self.task_shutdown_timeout}s) exceeded"
                )
                return False
        
        except Exception as e:
            logger.error(
                f"❌ Error stopping background tasks: {e}",
                exc_info=True
            )
            return False
    
    async def _stop_monitor(self) -> bool:
        """
        Остановка системы мониторинга
        
        Останавливает IntegratedCryptoMonitor с соблюдением таймаута.
        
        Returns:
            True если монитор остановлен успешно
        """
        try:
            logger.info("📊 Step 2/3: Stopping monitor...")
            
            if not self.monitor:
                logger.info("ℹ️ Monitor is not set, skipping")
                return True
            
            # Проверяем наличие метода stop
            if not hasattr(self.monitor, 'stop'):
                logger.warning("⚠️ Monitor has no stop method, skipping")
                return True
            
            # Останавливаем монитор с таймаутом
            try:
                stop_coro = self.monitor.stop()
                
                if asyncio.iscoroutine(stop_coro):
                    await asyncio.wait_for(
                        stop_coro,
                        timeout=self.monitor_shutdown_timeout
                    )
                else:
                    # Если stop не async, вызываем напрямую
                    self.monitor.stop()
                
                logger.info("✅ Monitor stopped successfully")
                return True
            
            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Monitor shutdown timeout ({self.monitor_shutdown_timeout}s) exceeded"
                )
                return False
        
        except Exception as e:
            logger.error(
                f"❌ Error stopping monitor: {e}",
                exc_info=True
            )
            return False
    
    async def _close_database(self) -> bool:
        """
        Закрытие соединений с базой данных
        
        Корректно закрывает DatabaseManager с соблюдением таймаута.
        
        Returns:
            True если БД закрыта успешно
        """
        try:
            logger.info("💾 Step 3/3: Closing database connections...")
            
            db_manager = self.db_manager
            if db_manager is None and self.db_initializer is not None:
                db_manager = self.db_initializer.get_manager()
            
            if not db_manager:
                logger.info("ℹ️ DatabaseManager is not initialized, skipping")
                return True
            
            # Проверяем состояние БД
            if hasattr(db_manager, 'is_initialized'):
                if not db_manager.is_initialized:
                    logger.info("ℹ️ Database is not initialized, skipping")
                    return True
            elif hasattr(db_manager, '_initialized'):
                if not db_manager._initialized:
                    logger.info("ℹ️ Database is not initialized, skipping")
                    return True
            
            # Закрываем БД с таймаутом
            try:
                async def close_db():
                    """Обертка для синхронного/асинхронного close"""
                    if hasattr(db_manager, 'close'):
                        if asyncio.iscoroutinefunction(db_manager.close):
                            await db_manager.close()
                        else:
                            db_manager.close()
                    elif hasattr(db_manager, 'shutdown'):
                        if asyncio.iscoroutinefunction(db_manager.shutdown):
                            await db_manager.shutdown()
                        else:
                            db_manager.shutdown()
                    else:
                        logger.warning("⚠️ DatabaseManager has no close/shutdown method")
                
                await asyncio.wait_for(
                    close_db(),
                    timeout=self.database_shutdown_timeout
                )
                
                logger.info("✅ Database connections closed successfully")
                return True
            
            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Database shutdown timeout ({self.database_shutdown_timeout}s) exceeded"
                )
                return False
        
        except Exception as e:
            logger.error(
                f"❌ Error closing database: {e}",
                exc_info=True
            )
            return False
    
    def set_monitor(self, monitor: 'IntegratedCryptoMonitor') -> None:
        """
        Установка монитора для shutdown
        
        Args:
            monitor: Экземпляр IntegratedCryptoMonitor
        """
        self.monitor = monitor
        logger.debug("Monitor set for shutdown management")
    
    def get_status(self) -> dict:
        """
        Получение статуса shutdown manager
        
        Returns:
            Словарь с информацией о состоянии
        """
        return {
            'shutdown_in_progress': self.shutdown_in_progress,
            'shutdown_completed': self.shutdown_completed,
            'has_task_manager': self.task_manager is not None,
            'has_db_initializer': self.db_initializer is not None,
            'has_db_manager': self.db_manager is not None,
            'has_monitor': self.monitor is not None,
            'timeouts': {
                'tasks': self.task_shutdown_timeout,
                'monitor': self.monitor_shutdown_timeout,
                'database': self.database_shutdown_timeout
            }
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        # ИСПРАВЛЕНО: вычисление вынесено из f-string для избежания syntax error
        components_count = sum([
            self.task_manager is not None,
            self.db_initializer is not None or self.db_manager is not None,
            self.monitor is not None
        ])
        
        return (
            f"ShutdownManager("
            f"in_progress={self.shutdown_in_progress}, "
            f"completed={self.shutdown_completed}, "
            f"components={components_count}"
            f")"
        )