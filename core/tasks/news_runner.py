# core/tasks/news_runner.py
"""
News System Runner
"""

import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)


class NewsSystemRunner:
    """Запуск и управление новостной системой"""
    
    def __init__(self, news_processor, health_monitor, resource_monitor, statistics, shutdown_event):
        self.news_processor = news_processor
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
    
    async def run(self):
        """Основной цикл новостной системы"""
        logger.info("📰 [NEWS] Запуск News Bot...")
        
        max_consecutive_errors = 5
        consecutive_errors = 0
        
        await asyncio.sleep(5)
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_news_heartbeat()
                
                await self._execute_news_cycle()
                
                consecutive_errors = 0
                self.statistics.increment_news()
                
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️  [NEWS] Memory pressure, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(300)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️  [NEWS] Timeout (180s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("📰 [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error('news')
                self.statistics.increment_errors()
                
                logger.error(f"❌ [NEWS] Ошибка ({consecutive_errors}/{max_consecutive_errors}): {e}")
                traceback.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [NEWS] Слишком много ошибок, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.statistics.increment_restarts()
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [NEWS] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("📰 [NEWS] News system остановлена")
    
    async def _execute_news_cycle(self):
        """Выполняет один цикл обработки новостей"""
        if hasattr(self.news_processor, 'run_cycle'):
            await asyncio.wait_for(
                self.news_processor.run_cycle(),
                timeout=180.0
            )
        elif hasattr(self.news_processor, 'process_news'):
            await asyncio.wait_for(
                self.news_processor.process_news(),
                timeout=180.0
            )
        elif hasattr(self.news_processor, 'run'):
            await asyncio.wait_for(
                self.news_processor.run(),
                timeout=180.0
            )
        else:
            logger.warning("⚠️  [NEWS] NewsProcessor не имеет известных методов")
            await asyncio.sleep(300)


__all__ = ['NewsSystemRunner']