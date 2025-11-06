# core/tasks/whale_runner.py
"""
Whale System Runner
"""

import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)


class WhaleSystemRunner:
    """Запуск и управление whale monitoring системой"""
    
    def __init__(self, whale_scheduler, health_monitor, resource_monitor, statistics, shutdown_event):
        self.whale_scheduler = whale_scheduler
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
    
    async def run(self):
        """Основной цикл whale системы"""
        logger.info("🐋 [WHALE] Запуск Whale Monitor...")
        
        max_consecutive_errors = 5
        consecutive_errors = 0
        
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_whale_heartbeat()
                
                await asyncio.wait_for(
                    self.whale_scheduler.run_cycle(),
                    timeout=120.0
                )
                
                consecutive_errors = 0
                self.statistics.increment_whale()
                
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️  [WHALE] Memory pressure, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(1)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️  [WHALE] Timeout (120s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("🐋 [WHALE] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error('whale')
                self.statistics.increment_errors()
                
                logger.error(f"❌ [WHALE] Ошибка ({consecutive_errors}/{max_consecutive_errors}): {e}")
                traceback.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [WHALE] Слишком много ошибок, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.statistics.increment_restarts()
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [WHALE] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("🐋 [WHALE] Whale system остановлена")


__all__ = ['WhaleSystemRunner']