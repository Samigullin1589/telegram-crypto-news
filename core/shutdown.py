# core/shutdown.py
"""
Graceful shutdown management
"""

import asyncio
import logging
import signal
from typing import Any

logger = logging.getLogger(__name__)


class ShutdownManager:
    """Управление graceful shutdown"""
    
    def __init__(self, shutdown_event: asyncio.Event):
        self.shutdown_event = shutdown_event
        self._shutdown_in_progress = False
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"\n⚠️  [SIGNAL] Получен сигнал {signal_name}")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("✅ Установлен обработчик для SIGINT")
        logger.info("✅ Установлен обработчик для SIGTERM")
    
    async def shutdown(
        self,
        http_server: Any,
        task_manager: Any,
        component_manager: Any
    ):
        """Выполняет graceful shutdown"""
        if self._shutdown_in_progress:
            logger.warning("⚠️  [SHUTDOWN] Shutdown уже в процессе")
            return
        
        self._shutdown_in_progress = True
        self.shutdown_event.set()
        
        logger.info("\n" + "=" * 80)
        logger.info("🛑 INITIATING GRACEFUL SHUTDOWN")
        logger.info("=" * 80 + "\n")
        
        logger.info("⏳ [1/4] Останавливаем HTTP health server...")
        await http_server.stop()
        
        logger.info("\n⏳ [2/4] Ждём завершения всех задач...")
        await task_manager.cancel_all_tasks()
        
        logger.info("\n⏳ [3/4] Останавливаем компоненты...")
        await component_manager.stop_all()
        
        logger.info("\n⏳ [4/4] Финализация...")
        import gc
        gc.collect()
        logger.info("   ✓ Garbage collection выполнен")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ SHUTDOWN COMPLETE")
        logger.info("=" * 80)
    
    async def cleanup(self):
        """Финальная очистка ресурсов"""
        logger.info("\n🧹 [CLEANUP] Финальная очистка ресурсов...")
        
        import gc
        gc.collect()
        
        logger.info("✅ [CLEANUP] Очистка завершена")