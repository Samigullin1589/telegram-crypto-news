# core/tasks.py
"""
Task management and execution
"""

import asyncio
import logging
import traceback
import os
from typing import Any, List, Optional
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
            self.tasks.append(
                asyncio.create_task(
                    self._run_news_system(),
                    name='news_system'
                )
            )
        
        if self.components.whale_scheduler:
            self.tasks.append(
                asyncio.create_task(
                    self._run_whale_system(),
                    name='whale_system'
                )
            )
        
        if self.components.bot_application:
            self.tasks.append(
                asyncio.create_task(
                    self._run_bot_webhook(),
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
        """
        Ждет завершения первой задачи
        
        Returns:
            Множество завершенных задач
        """
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
    
    async def _run_news_system(self):
        """Запуск новостной системы"""
        await NewsSystemRunner(
            self.components.news_processor,
            self.health_monitor,
            self.resource_monitor,
            self.statistics,
            self.shutdown_event
        ).run()
    
    async def _run_whale_system(self):
        """Запуск whale monitoring системы"""
        await WhaleSystemRunner(
            self.components.whale_scheduler,
            self.health_monitor,
            self.resource_monitor,
            self.statistics,
            self.shutdown_event
        ).run()
    
    async def _run_bot_webhook(self):
        """Запуск Telegram bot в режиме WEBHOOK"""
        await BotWebhookRunner(
            self.components.bot_application,
            self.health_monitor,
            self.statistics,
            self.shutdown_event
        ).run()
    
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
                logger.error(f"❌ [HEALTH] Ошибка проверки здоровья: {e}")
                traceback.print_exc()
                await asyncio.sleep(self.health_monitor.check_interval)
        
        logger.info("💚 [HEALTH] Health monitor остановлен")
    
    async def _coordination_loop(self):
        """Координация публикаций и управление ресурсами"""
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


class BotWebhookRunner:
    """Запуск Telegram bot в режиме WEBHOOK"""
    
    def __init__(self, bot_application, health_monitor, statistics, shutdown_event):
        self.bot_application = bot_application
        self.health_monitor = health_monitor
        self.statistics = statistics
        self.shutdown_event = shutdown_event
    
    async def run(self):
        """Основной цикл бота"""
        try:
            logger.info("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            await asyncio.wait_for(self.bot_application.initialize(), timeout=30.0)
            await asyncio.wait_for(self.bot_application.start(), timeout=30.0)
            
            webhook_url = self._determine_webhook_url()
            
            logger.info(f"🤖 [BOT] Устанавливаем webhook: {webhook_url}")
            
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(drop_pending_updates=True),
                timeout=10.0
            )
            
            webhook_info = await asyncio.wait_for(
                self.bot_application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=None,
                    drop_pending_updates=True
                ),
                timeout=10.0
            )
            
            if webhook_info:
                logger.info("✅ [BOT] Webhook установлен успешно")
            else:
                logger.warning("⚠️  [BOT] Webhook set вернул False, но продолжаем")
            
            self.health_monitor.update_bot_heartbeat()
            
            logger.info("✅ [BOT] Command handler активен в WEBHOOK режиме")
            logger.info(f"   Webhook URL: {webhook_url}")
            logger.info("   Доступные команды: /start, /help, /status, /positions, /performance")
            
            while not self.shutdown_event.is_set():
                self.health_monitor.update_bot_heartbeat()
                await asyncio.sleep(60)
            
            logger.info("🤖 [BOT] Получен сигнал остановки")
        
        except asyncio.TimeoutError:
            logger.error("❌ [BOT] Timeout при инициализации")
        
        except asyncio.CancelledError:
            logger.info("🤖 [BOT] Получен сигнал отмены")
        
        except Exception as e:
            self.health_monitor.record_error('bot')
            self.statistics.increment_errors()
            logger.error(f"❌ [BOT] Ошибка при установке webhook: {e}")
            traceback.print_exc()
        
        finally:
            await self._cleanup()
    
    def _determine_webhook_url(self) -> str:
        """Определяет URL для webhook"""
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        
        if not webhook_url:
            render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
            if render_url:
                webhook_url = f"{render_url}/webhook/telegram"
            else:
                service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
        
        return webhook_url
    
    async def _cleanup(self):
        """Cleanup bot resources"""
        logger.info("🤖 [BOT] Останавливаем command handler...")
        
        try:
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(),
                timeout=10.0
            )
            logger.info("   ✓ Webhook удалён")
            
            if self.bot_application.running:
                await asyncio.wait_for(
                    self.bot_application.stop(),
                    timeout=10.0
                )
                logger.info("   ✓ Application остановлен")
            
            await asyncio.wait_for(
                self.bot_application.shutdown(),
                timeout=10.0
            )
            logger.info("   ✓ Shutdown завершён")
        
        except asyncio.TimeoutError:
            logger.warning("   ⚠️  Timeout при shutdown")
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка при shutdown: {e}")
        
        logger.info("✅ [BOT] Command handler полностью остановлен")