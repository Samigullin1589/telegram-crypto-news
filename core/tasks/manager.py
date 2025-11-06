# core/tasks/manager.py
"""
Task Manager - orchestrates all system tasks
"""

import asyncio
import logging
import traceback
from typing import Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskManager:
    """Управление задачами системы"""
    
    def __init__(
        self,
        components: Any,
        health_monitor: Any,
        resource_monitor: Any,
        statistics: Any,
        shutdown_event: asyncio.Event
    ):
        self.components = components
        self.health_monitor = health_monitor
        self.resource_monitor = resource_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
        self.tasks: List[asyncio.Task] = []
    
    async def start_all_tasks(self):
        """Запускает все задачи системы"""
        self.tasks = []
        
        if self.components.news_processor:
            from core.tasks.news_runner import NewsSystemRunner
            
            self.tasks.append(
                asyncio.create_task(
                    NewsSystemRunner(
                        self.components.news_processor,
                        self.health_monitor,
                        self.resource_monitor,
                        self.statistics,
                        self.shutdown_event
                    ).run(),
                    name='news_system'
                )
            )
        
        if self.components.whale_scheduler:
            from core.tasks.whale_runner import WhaleSystemRunner
            
            self.tasks.append(
                asyncio.create_task(
                    WhaleSystemRunner(
                        self.components.whale_scheduler,
                        self.health_monitor,
                        self.resource_monitor,
                        self.statistics,
                        self.shutdown_event
                    ).run(),
                    name='whale_system'
                )
            )
        
        if self.components.bot_application:
            from core.tasks.bot_runner import BotWebhookRunner
            
            self.tasks.append(
                asyncio.create_task(
                    BotWebhookRunner(
                        self.components.bot_application,
                        self.health_monitor,
                        self.statistics,
                        self.shutdown_event
                    ).run(),
                    name='bot_commands'
                )
            )
        
        self.tasks.extend([
            asyncio.create_task(self._health_check_loop(), name='health_monitor'),
            asyncio.create_task(self._coordination_loop(), name='coordinator'),
            asyncio.create_task(self._wait_for_shutdown(), name='shutdown_waiter')
        ])
        
        logger.info(f"\n🚀 Запущено {len(self.tasks)} задач:")
        for task in self.tasks:
            logger.info(f"   • {task.get_name()}")
        logger.info("")
    
    async def wait_for_completion(self) -> set:
        """Ждет завершения первой задачи"""
        done, pending = await asyncio.wait(
            self.tasks,
            return_when=asyncio.FIRST_COMPLETED
        )
        return done
    
    async def cancel_all_tasks(self):
        """Отменяет все задачи"""
        if not self.tasks:
            return
        
        for task in self.tasks:
            if not task.done() and task.get_name() != 'shutdown_waiter':
                task.cancel()
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.tasks, return_exceptions=True),
                timeout=30.0
            )
            logger.info("   ✓ Все задачи завершены")
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout ожидания задач")
    
    def handle_completed_tasks(self, done: set):
        """Обрабатывает завершенные задачи"""
        for task in done:
            task_name = task.get_name()
            
            if task_name == 'shutdown_waiter':
                logger.info("✅ Получен сигнал graceful shutdown")
            else:
                exc = task.exception()
                if exc:
                    logger.error(f"\n❌ [CRITICAL] Task '{task_name}' crashed:")
                    logger.error("=" * 80)
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
                    logger.error("=" * 80)
                    self.statistics.increment_errors()
                else:
                    logger.warning(f"⚠️  Task '{task_name}' завершилась без ошибок")
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья"""
        await asyncio.sleep(300)
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    logger.warning("\n" + "=" * 80)
                    logger.warning("⚠️  [HEALTH] ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
                    logger.warning("=" * 80)
                    for issue in issues:
                        logger.warning(f"   {issue}")
                    logger.warning("=" * 80 + "\n")
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.resource_monitor.check_memory
                )
                
                await asyncio.sleep(self.health_monitor.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [HEALTH] Ошибка проверки: {e}")
                traceback.print_exc()
                await asyncio.sleep(self.health_monitor.check_interval)
        
        logger.info("💚 [HEALTH] Health monitor остановлен")
    
    async def _coordination_loop(self):
        """Координация публикаций"""
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now(timezone.utc)
                time_since_gc = (now - self.resource_monitor.last_gc).seconds
                
                if time_since_gc > self.resource_monitor.gc_interval:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._run_garbage_collection
                    )
                
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [COORDINATOR] Ошибка: {e}")
                traceback.print_exc()
                await asyncio.sleep(60)
        
        logger.info("🔄 [COORDINATOR] Coordinator остановлен")
    
    def _run_garbage_collection(self):
        """Запуск garbage collection"""
        import gc
        gc.collect()
        self.resource_monitor.last_gc = datetime.now(timezone.utc)
        self.resource_monitor.gc_runs += 1
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала shutdown"""
        await self.shutdown_event.wait()
        logger.info("✅ [SHUTDOWN] Shutdown signal получен")


__all__ = ['TaskManager']