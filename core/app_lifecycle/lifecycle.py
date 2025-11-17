# core/app_lifecycle/lifecycle.py
"""
Application Lifecycle Module v5.4
ИСПРАВЛЕНО: Monitor запускается как фоновая задача

ИСПРАВЛЕНО v5.4:
- Убран HealthServer (HTTP endpoints обрабатывает Monitor.HTTPServer)
- Исправлен конфликт портов между HealthServer и HTTPServer

ИСПРАВЛЕНО v5.3:
- HealthServer v5.3 compatibility (start() без параметра port)
- ApplicationValidator v5.3 compatibility (business layer)
"""

import logging
import asyncio
import time
from typing import Any, Optional, Dict

from .validators import ApplicationValidator

logger = logging.getLogger(__name__)


class ApplicationLifecycle:
    """
    Управление жизненным циклом v5.4

    ИСПРАВЛЕНО v5.4:
    - Убран health_server (HTTP сервер теперь в Monitor)
    - Исправлен конфликт портов

    ИСПРАВЛЕНО v5.1:
    - Monitor.run() запускается как фоновая задача
    - Ожидание через monitor.infrastructure.shutdown_event
    - Сохранение ссылки на monitor_task
    """

    def __init__(
        self,
        config: Any,
        monitor: Any,
        db_manager: Any,
        shutdown_manager: Any
    ):
        self.config = config
        self.monitor = monitor
        self.db_manager = db_manager
        self.shutdown_manager = shutdown_manager

        self.validator = ApplicationValidator(config, monitor, db_manager)

        self.is_running = False
        self.start_time: Optional[float] = None
        self.monitor_task: Optional[asyncio.Task] = None

        logger.debug("ApplicationLifecycle v5.4 initialized")
    
    async def startup(self) -> None:
        """
        Запуск приложения v5.4

        ИСПРАВЛЕНО v5.4:
        - Убран запуск HealthServer (HTTP сервер запускается в Monitor)
        """
        self.start_time = time.time()

        logger.info("="*80)
        logger.info("🚀 STARTING APPLICATION")
        logger.info("="*80)

        try:
            await self._validate_readiness()
            await self._start_monitor()

            self.is_running = True

            logger.info("="*80)
            logger.info("✅ STARTUP COMPLETE")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"❌ Startup failed: {e}", exc_info=True)
            raise
    
    async def _validate_readiness(self) -> None:
        """Валидация готовности"""
        logger.info("Validating readiness...")
        
        is_valid, errors = self.validator.validate_all()
        if not is_valid:
            raise RuntimeError(f"Validation failed: {errors}")
        
        logger.info("✅ Validated")
    
    
    async def _start_monitor(self) -> None:
        """Запуск monitor как фоновой задачи"""
        logger.info("Starting monitor...")
        
        try:
            # КРИТИЧЕСКИ ВАЖНО: Сохраняем ссылку на task!
            self.monitor_task = asyncio.create_task(
                self.monitor.run(),
                name="IntegratedCryptoMonitor"
            )
            
            # Даем время на запуск
            await asyncio.sleep(1.0)
            
            logger.info("✅ Monitor started")
        except Exception as e:
            logger.error(f"❌ Monitor failed: {e}", exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown v5.4

        ИСПРАВЛЕНО v5.4:
        - Убрана остановка HealthServer (HTTP сервер останавливается в Monitor)
        """
        if not self.is_running:
            return

        logger.info("="*80)
        logger.info("⏹️ SHUTDOWN")
        logger.info("="*80)

        try:
            await self._stop_monitor()
            await self._run_shutdown_manager()
            self._log_stats()

            self.is_running = False

            logger.info("="*80)
            logger.info("✅ SHUTDOWN COMPLETE")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}", exc_info=True)
            raise
    
    async def _stop_monitor(self) -> None:
        """Остановка monitor"""
        try:
            await self.monitor.stop()
            
            # Ждем завершения monitor_task
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("✅ Monitor stopped")
        except Exception as e:
            logger.error(f"❌ Monitor stop error: {e}", exc_info=True)
    
    async def _run_shutdown_manager(self) -> None:
        """Shutdown manager"""
        try:
            await self.shutdown_manager.shutdown()
            logger.info("✅ Shutdown manager done")
        except Exception as e:
            logger.error(f"❌ Shutdown manager error: {e}", exc_info=True)
    
    
    def _log_stats(self) -> None:
        """Статистика"""
        if self.start_time:
            uptime = time.time() - self.start_time
            logger.info(f"📊 Uptime: {uptime:.2f}s")
    
    async def run_until_stopped(self) -> None:
        """Главный цикл"""
        try:
            await self.startup()
            await self._wait_for_shutdown()
        except asyncio.CancelledError:
            logger.info("Cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Critical: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    async def _wait_for_shutdown(self) -> None:
        """Ожидание shutdown signal"""
        logger.info("Running, waiting for shutdown...")
        
        try:
            if not hasattr(self.monitor, 'infrastructure'):
                raise RuntimeError("Monitor missing infrastructure")
            
            shutdown_event = self.monitor.infrastructure.shutdown_event
            if not shutdown_event:
                raise RuntimeError("Shutdown event not available")
            
            # Ждем shutdown signal от Monitor
            await shutdown_event.wait()
            
            logger.info("Shutdown signal received")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error waiting: {e}", exc_info=True)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус"""
        uptime = None
        if self.start_time and self.is_running:
            uptime = time.time() - self.start_time
        
        monitor_status = {}
        if hasattr(self.monitor, 'get_status'):
            try:
                monitor_status = self.monitor.get_status()
            except Exception:
                pass
        
        return {
            'running': self.is_running,
            'uptime_seconds': uptime,
            'monitor': monitor_status
        }


__all__ = ['ApplicationLifecycle']