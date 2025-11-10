"""
Application lifecycle module
Управление жизненным циклом приложения
"""

import logging
import asyncio
from typing import Any, Optional

from .validators import ApplicationValidator
from .task_starter import TaskStarter

logger = logging.getLogger(__name__)


class ApplicationLifecycle:
    """
    Управление полным жизненным циклом приложения
    
    Отвечает за:
    - Инициализацию всех компонентов
    - Запуск фоновых задач
    - Graceful shutdown
    - Обработку ошибок
    """
    
    def __init__(self, config: Any, monitor: Any, db_manager: Any,
                 shutdown_manager: Any, task_manager: Any, health_server: Any):
        """
        Инициализация lifecycle менеджера
        
        Args:
            config: Конфигурация приложения
            monitor: Монитор системы
            db_manager: Менеджер базы данных
            shutdown_manager: Менеджер остановки
            task_manager: Менеджер задач
            health_server: Health check сервер
        """
        self.config = config
        self.monitor = monitor
        self.db_manager = db_manager
        self.shutdown_manager = shutdown_manager
        self.task_manager = task_manager
        self.health_server = health_server
        
        # Создание вспомогательных объектов
        self.validator = ApplicationValidator(config, monitor, db_manager)
        self.task_starter = TaskStarter(config, monitor, task_manager)
        
        # Состояние
        self.is_running = False
        self.start_time: Optional[float] = None
    
    async def startup(self):
        """
        Полная процедура запуска приложения
        
        Raises:
            RuntimeError: Если валидация не пройдена
        """
        import time
        self.start_time = time.time()
        
        logger.info("="*80)
        logger.info("🚀 STARTING APPLICATION LIFECYCLE")
        logger.info("="*80)
        
        # Валидация готовности
        is_valid, errors = self.validator.validate_all()
        if not is_valid:
            error_msg = f"Application validation failed: {errors}"
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
        # Запуск health сервера
        await self._start_health_server()
        
        # Запуск фоновых задач
        task_results = await self.task_starter.start_all_tasks()
        
        # Проверка критических ошибок
        if task_results.get('errors'):
            logger.warning("⚠️  Some tasks failed to start, but continuing...")
        
        self.is_running = True
        
        logger.info("="*80)
        logger.info("✅ APPLICATION STARTUP COMPLETE")
        logger.info("="*80)
    
    async def shutdown(self):
        """
        Graceful shutdown приложения
        """
        if not self.is_running:
            logger.info("Application not running, skipping shutdown")
            return
        
        logger.info("="*80)
        logger.info("⏹️  GRACEFUL SHUTDOWN")
        logger.info("="*80)
        
        try:
            # Остановка задач
            await self.task_starter.stop_all_tasks()
            
            # Остановка компонентов через shutdown_manager
            await self.shutdown_manager.shutdown()
            
            # Остановка health сервера
            await self._stop_health_server()
            
            # Вычисление uptime
            if self.start_time:
                import time
                uptime = time.time() - self.start_time
                logger.info(f"📊 Application uptime: {uptime:.2f} seconds")
            
            self.is_running = False
            
            logger.info("="*80)
            logger.info("✅ SHUTDOWN COMPLETE")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}", exc_info=True)
            raise
    
    async def _start_health_server(self):
        """Запуск health check сервера"""
        try:
            port = getattr(self.config, 'port', 8000)
            logger.info(f"Starting health check server on port {port}...")
            
            await self.health_server.start(port=port)
            
            logger.info(f"✅ Health check server started on port {port}")
        except Exception as e:
            logger.error(f"❌ Failed to start health server: {e}", exc_info=True)
            raise
    
    async def _stop_health_server(self):
        """Остановка health check сервера"""
        try:
            await self.health_server.stop()
            logger.info("✅ Health check server stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping health server: {e}", exc_info=True)
    
    async def run_until_stopped(self):
        """
        Запуск приложения до момента остановки
        
        Основной цикл работы приложения
        """
        try:
            await self.startup()
            
            # Ожидание сигнала остановки
            await self._wait_for_shutdown_signal()
            
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        except Exception as e:
            logger.error(f"❌ Critical error in application: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    async def _wait_for_shutdown_signal(self):
        """Ожидание сигнала остановки"""
        logger.info("Application running, waiting for shutdown signal...")
        
        # Создаем Future который будет ожидать сигнала
        shutdown_event = asyncio.Event()
        
        # В реальности здесь будет обработка сигналов SIGINT/SIGTERM
        # Для простоты просто ждем вечно, пока не будет отменено
        try:
            await shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Shutdown signal received")
            raise
    
    def get_status(self) -> dict:
        """
        Получение текущего статуса приложения
        
        Returns:
            dict: Статус приложения
        """
        import time
        
        uptime = None
        if self.start_time and self.is_running:
            uptime = time.time() - self.start_time
        
        return {
            'running': self.is_running,
            'uptime_seconds': uptime,
            'running_tasks': self.task_starter.get_running_tasks(),
            'system_info': self.validator.get_system_info()
        }


__all__ = ['ApplicationLifecycle']