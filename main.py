"""
INTEGRATED CRYPTO MONITOR v4.5 - Production Ready Edition
Unified system: News Bot + Whale Monitor + Trading System + Telegram Commands

ARCHITECTURE IMPROVEMENTS v4.5:
✅ Modular structure with separated concerns
✅ Enhanced async coordination
✅ Optimized resource management
✅ Production-grade error handling
✅ Zero blocking operations
✅ Clean separation of responsibilities
"""

import asyncio
import signal
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import traceback as tb

if sys.version_info < (3, 8):
    print("❌ Требуется Python 3.8 или выше")
    sys.exit(1)

# Import core modules
from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegratedCryptoMonitor:
    """
    Production-ready интегрированная система мониторинга криптовалют v4.5
    
    Архитектура:
    - Modular design с разделением ответственности
    - Non-blocking async координация
    - Production-grade error recovery
    - Resource-aware execution
    - Clean shutdown protocol
    """
    
    def __init__(self):
        logger.info("\n" + "="*80)
        logger.info("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.5")
        logger.info("="*80 + "\n")
        
        # Core components
        self.rate_limiter = ChainRateLimiter()
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450'))
        )
        self.health_monitor = SystemHealthMonitor()
        
        # Business logic components
        self.news_processor = self._load_news_processor()
        self.whale_scheduler = self._load_whale_scheduler()
        self.bot_application = self._load_bot_application()
        
        # HTTP server
        self.http_server = HTTPServer(
            health_monitor=self.health_monitor,
            resource_monitor=self.resource_monitor,
            rate_limiter=self.rate_limiter,
            bot_application=self.bot_application
        )
        
        # Connect rate limiter to whale scheduler
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'set_rate_limiter'):
            self.whale_scheduler.set_rate_limiter(self.rate_limiter)
            logger.info("✅ Rate Limiter v2.1 подключен к Whale Scheduler")
        
        # State management
        self.shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._shutdown_in_progress = False
        
        # Statistics
        self.stats = {
            "start_time": datetime.now(timezone.utc),
            "total_publications": 0,
            "news_publications": 0,
            "whale_publications": 0,
            "trading_publications": 0,
            "bot_commands": 0,
            "errors_caught": 0,
            "restarts": 0
        }
        
        logger.info("\n✅ Integrated Crypto Monitor v4.5 инициализирован")
    
    def _load_news_processor(self) -> Optional[Any]:
        """Загрузка News Processor"""
        try:
            from bot.processor import NewsProcessor
            processor = NewsProcessor()
            logger.info("✅ News Processor loaded")
            return processor
        except ImportError as e:
            logger.warning(f"⚠️ News Processor not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Failed to load News Processor: {e}")
            tb.print_exc()
            return None
    
    def _load_whale_scheduler(self) -> Optional[Any]:
        """Загрузка Whale Scheduler"""
        try:
            from app.scheduler import scheduler as whale_scheduler
            logger.info("✅ Whale Scheduler loaded")
            return whale_scheduler
        except ImportError as e:
            logger.warning(f"⚠️ Whale Scheduler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Failed to load Whale Scheduler: {e}")
            tb.print_exc()
            return None
    
    def _load_bot_application(self) -> Optional[Any]:
        """Загрузка Bot Application"""
        try:
            from app.bot import application as bot_application
            logger.info("✅ Bot Commands Handler loaded")
            
            if self._patch_bot_handlers(bot_application):
                logger.info("   ✓ Bot handlers патчинг успешен")
            
            return bot_application
        except ImportError as e:
            logger.warning(f"⚠️ Bot Commands Handler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Bot Commands Handler not loaded: {e}")
            tb.print_exc()
            return None
    
    def _patch_bot_handlers(self, bot_app: Any) -> bool:
        """Патчим обработчики команд для мониторинга"""
        if not bot_app or not hasattr(bot_app, 'handlers'):
            return False
        
        try:
            from functools import wraps
            
            handlers_dict = bot_app.handlers
            if not handlers_dict or 0 not in handlers_dict:
                return False
            
            handlers_list = handlers_dict[0]
            if not handlers_list:
                return False
            
            patched_count = 0
            
            for handler in handlers_list:
                if not hasattr(handler, 'callback'):
                    continue
                
                original_callback = handler.callback
                health_monitor = self.health_monitor
                stats = self.stats
                
                @wraps(original_callback)
                async def wrapped_callback(update, context, original=original_callback, 
                                         monitor=health_monitor, stats_dict=stats):
                    monitor.record_bot_command()
                    stats_dict["bot_commands"] += 1
                    
                    try:
                        return await original(update, context)
                    except Exception as e:
                        monitor.record_error("bot")
                        logger.error(f"❌ [BOT] Error in command handler: {e}")
                        raise
                
                handler.callback = wrapped_callback
                patched_count += 1
            
            if patched_count > 0:
                logger.info(f"   ✓ Патчинг {patched_count} handlers успешен")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"   ⚠️ Ошибка при патчинге handlers: {e}")
            tb.print_exc()
            return False
    
    async def run(self):
        """Главный цикл выполнения"""
        self._print_startup_banner()
        self._setup_signal_handlers()
        
        try:
            # Start HTTP server
            await self.http_server.start()
            
            # Create and start all tasks
            await self._start_all_tasks()
            
            # Wait for first task completion or shutdown
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Handle completed tasks
            await self._handle_completed_tasks(done)
            
            # Initiate shutdown if not already in progress
            if not self._shutdown_in_progress:
                logger.info("\n⚠️ Инициируется shutdown из-за завершения задачи...")
                await self.shutdown()
        
        except asyncio.CancelledError:
            logger.info("\n⏹️ [INFO] Задачи отменены")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ [STOP] Получен Ctrl+C")
            await self.shutdown()
        
        except Exception as e:
            logger.error(f"\n❌ [FATAL] Критическая ошибка в main loop:")
            logger.error("="*80)
            tb.print_exc()
            logger.error("="*80)
            self.stats["errors_caught"] += 1
        
        finally:
            await self.cleanup()
    
    async def _start_all_tasks(self):
        """Запуск всех задач системы"""
        self._tasks = []
        
        # Business logic tasks
        if self.news_processor:
            self._tasks.append(
                asyncio.create_task(self._run_news_system(), name="news_system")
            )
        
        if self.whale_scheduler:
            self._tasks.append(
                asyncio.create_task(self._run_whale_system(), name="whale_system")
            )
        
        if self.bot_application:
            self._tasks.append(
                asyncio.create_task(self._run_bot_webhook(), name="bot_commands")
            )
        
        # System tasks
        self._tasks.extend([
            asyncio.create_task(self._health_check_loop(), name="health_monitor"),
            asyncio.create_task(self._coordination_loop(), name="coordinator"),
            asyncio.create_task(self._wait_for_shutdown(), name="shutdown_waiter")
        ])
        
        logger.info(f"\n🚀 Запущено {len(self._tasks)} задач:")
        for task in self._tasks:
            logger.info(f"   • {task.get_name()}")
        logger.info("")
    
    async def _handle_completed_tasks(self, done: set):
        """Обработка завершенных задач"""
        for task in done:
            task_name = task.get_name()
            
            if task_name == "shutdown_waiter":
                logger.info("✅ Получен сигнал graceful shutdown")
            else:
                exc = task.exception()
                if exc:
                    logger.error(f"\n❌ [CRITICAL] Task '{task_name}' crashed:")
                    logger.error("="*80)
                    tb.print_exception(type(exc), exc, exc.__traceback__)
                    logger.error("="*80)
                    self.stats["errors_caught"] += 1
                else:
                    logger.warning(f"⚠️ Task '{task_name}' завершилась без ошибок")
    
    async def _run_news_system(self):
        """Запуск новостной системы с адаптивным error handling"""
        logger.info("📰 [NEWS] Запуск News Bot...")
        
        max_consecutive_errors = 5
        consecutive_errors = 0
        
        await asyncio.sleep(5)
        
        while not self.shutdown_event.is_set():
            try:
                self.health_monitor.update_news_heartbeat()
                
                # Determine which method to call
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
                    logger.warning("⚠️ [NEWS] NewsProcessor не имеет известных методов")
                    await asyncio.sleep(300)
                    continue
                
                consecutive_errors = 0
                self.stats['news_publications'] += 1
                self.stats['total_publications'] += 1
                
                # Check memory pressure
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️ [NEWS] Memory pressure, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(300)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️ [NEWS] Timeout (180s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("📰 [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("news")
                self.stats["errors_caught"] += 1
                
                logger.error(f"❌ [NEWS] Ошибка ({consecutive_errors}/{max_consecutive_errors}): {e}")
                tb.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [NEWS] Слишком много ошибок, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [NEWS] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("📰 [NEWS] News system остановлена")
    
    async def _run_whale_system(self):
        """Запуск whale monitoring системы с адаптивным error handling"""
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
                self.stats['whale_publications'] += 1
                self.stats['total_publications'] += 1
                
                # Check memory pressure
                if not self.resource_monitor.check_memory():
                    logger.warning("⚠️ [WHALE] Memory pressure, slowing down...")
                    await asyncio.sleep(30)
                
                await asyncio.sleep(1)
            
            except asyncio.TimeoutError:
                logger.warning("⚠️ [WHALE] Timeout (120s)")
                consecutive_errors += 1
            
            except asyncio.CancelledError:
                logger.info("🐋 [WHALE] Получен сигнал остановки")
                break
            
            except Exception as e:
                consecutive_errors += 1
                self.health_monitor.record_error("whale")
                self.stats["errors_caught"] += 1
                
                logger.error(f"❌ [WHALE] Ошибка ({consecutive_errors}/{max_consecutive_errors}): {e}")
                tb.print_exc()
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("❌ [WHALE] Слишком много ошибок, перезапуск через 5 минут...")
                    await asyncio.sleep(300)
                    consecutive_errors = 0
                    self.stats["restarts"] += 1
                else:
                    delay = min(30 * (2 ** consecutive_errors), 300)
                    logger.info(f"⏳ [WHALE] Повторная попытка через {delay}с...")
                    await asyncio.sleep(delay)
        
        logger.info("🐋 [WHALE] Whale system остановлена")
    
    async def _run_bot_webhook(self):
        """Запуск Telegram bot в режиме WEBHOOK"""
        try:
            logger.info("🤖 [BOT] Инициализация command handler (WEBHOOK MODE)...")
            
            await asyncio.wait_for(self.bot_application.initialize(), timeout=30.0)
            await asyncio.wait_for(self.bot_application.start(), timeout=30.0)
            
            # Determine webhook URL
            webhook_url = os.environ.get('WEBHOOK_URL', '')
            if not webhook_url:
                render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
                if render_url:
                    webhook_url = f"{render_url}/webhook/telegram"
                else:
                    service_name = os.environ.get('RENDER_SERVICE_NAME', 'crypto-compass')
                    webhook_url = f"https://{service_name}.onrender.com/webhook/telegram"
            
            logger.info(f"🤖 [BOT] Устанавливаем webhook: {webhook_url}")
            
            # Delete old webhook
            await asyncio.wait_for(
                self.bot_application.bot.delete_webhook(drop_pending_updates=True),
                timeout=10.0
            )
            
            # Set new webhook
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
                logger.warning("⚠️ [BOT] Webhook set вернул False, но продолжаем")
            
            self.health_monitor.update_bot_heartbeat()
            
            logger.info("✅ [BOT] Command handler активен в WEBHOOK режиме")
            logger.info(f"   Webhook URL: {webhook_url}")
            logger.info("   Доступные команды: /start, /help, /status, /positions, /performance")
            
            # Keep alive loop
            while not self.shutdown_event.is_set():
                self.health_monitor.update_bot_heartbeat()
                await asyncio.sleep(60)
            
            logger.info("🤖 [BOT] Получен сигнал остановки")
        
        except asyncio.TimeoutError:
            logger.error("❌ [BOT] Timeout при инициализации")
        
        except asyncio.CancelledError:
            logger.info("🤖 [BOT] Получен сигнал отмены")
        
        except Exception as e:
            self.health_monitor.record_error("bot")
            self.stats["errors_caught"] += 1
            logger.error(f"❌ [BOT] Ошибка при установке webhook: {e}")
            tb.print_exc()
        
        finally:
            await self._cleanup_bot()
    
    async def _cleanup_bot(self):
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
            logger.warning("   ⚠️ Timeout при shutdown")
        except Exception as e:
            logger.warning(f"   ⚠️ Ошибка при shutdown: {e}")
        
        logger.info("✅ [BOT] Command handler полностью остановлен")
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья всех систем"""
        await asyncio.sleep(300)
        
        while not self.shutdown_event.is_set():
            try:
                is_healthy, issues = self.health_monitor.check_health()
                
                if not is_healthy:
                    logger.warning("\n" + "="*80)
                    logger.warning("⚠️ [HEALTH] ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
                    logger.warning("="*80)
                    for issue in issues:
                        logger.warning(f"   {issue}")
                    logger.warning("="*80 + "\n")
                
                # Check memory without blocking
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.resource_monitor.check_memory
                )
                
                # Print rate limiter stats
                self.rate_limiter.print_stats()
                
                await asyncio.sleep(self.health_monitor.check_interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [HEALTH] Ошибка проверки здоровья: {e}")
                tb.print_exc()
                await asyncio.sleep(self.health_monitor.check_interval)
        
        logger.info("💚 [HEALTH] Health monitor остановлен")
    
    async def _coordination_loop(self):
        """
        Координация публикаций и управление ресурсами
        
        v4.5: Non-blocking coordination with proper async handling
        """
        await asyncio.sleep(10)
        
        while not self.shutdown_event.is_set():
            try:
                # Run GC in executor to avoid blocking
                if (datetime.now(timezone.utc) - self.resource_monitor.last_gc).seconds > self.resource_monitor.gc_interval:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._run_garbage_collection
                    )
                
                # Yield control to event loop
                await asyncio.sleep(60)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"❌ [COORDINATOR] Ошибка: {e}")
                tb.print_exc()
                await asyncio.sleep(60)
        
        logger.info("🔄 [COORDINATOR] Coordinator остановлен")
    
    def _run_garbage_collection(self):
        """Run garbage collection in separate thread"""
        import gc
        gc.collect()
        self.resource_monitor.last_gc = datetime.now(timezone.utc)
        self.resource_monitor.gc_runs += 1
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала shutdown"""
        await self.shutdown_event.wait()
        logger.info("✅ [SHUTDOWN] Shutdown signal получен")
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"\n⚠️ [SIGNAL] Получен сигнал {signal_name}")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("✅ Установлен обработчик для SIGINT")
        logger.info("✅ Установлен обработчик для SIGTERM")
    
    async def shutdown(self):
        """Graceful shutdown всех систем"""
        if self._shutdown_in_progress:
            logger.warning("⚠️ [SHUTDOWN] Shutdown уже в процессе")
            return
        
        self._shutdown_in_progress = True
        self.shutdown_event.set()
        
        logger.info("\n" + "="*80)
        logger.info("🛑 INITIATING GRACEFUL SHUTDOWN")
        logger.info("="*80 + "\n")
        
        # Stop HTTP server
        logger.info("⏳ [1/4] Останавливаем HTTP health server...")
        await self.http_server.stop()
        
        # Cancel all tasks
        logger.info("\n⏳ [2/4] Ждём завершения всех задач...")
        if self._tasks:
            for task in self._tasks:
                if not task.done() and task.get_name() != "shutdown_waiter":
                    task.cancel()
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=30.0
                )
                logger.info("   ✓ Все задачи завершены")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️ Timeout ожидания задач")
        
        # Stop components
        logger.info("\n⏳ [3/4] Останавливаем компоненты...")
        await self._stop_components()
        
        # Final cleanup
        logger.info("\n⏳ [4/4] Финализация...")
        import gc
        gc.collect()
        logger.info("   ✓ Garbage collection выполнен")
        
        logger.info("\n" + "="*80)
        logger.info("✅ SHUTDOWN COMPLETE")
        logger.info("="*80)
    
    async def _stop_components(self):
        """Stop all business logic components"""
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.whale_scheduler.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ Whale Scheduler остановлен")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки Whale Scheduler: {e}")
        
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.news_processor.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ News Processor остановлен")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки News Processor: {e}")
    
    async def cleanup(self):
        """Финальная очистка ресурсов"""
        logger.info("\n🧹 [CLEANUP] Финальная очистка ресурсов...")
        
        self._print_final_statistics()
        
        import gc
        gc.collect()
        
        logger.info("✅ [CLEANUP] Очистка завершена")
    
    def _print_startup_banner(self):
        """Вывод startup banner"""
        logger.info("\n" + "="*80)
        logger.info("🚀 INTEGRATED CRYPTO MONITOR v4.5 - STARTING")
        logger.info("="*80)
        
        logger.info("\n📦 LOADED COMPONENTS:")
        logger.info(f"   News Bot:        {'✅ Loaded' if self.news_processor else '❌ Not Available'}")
        logger.info(f"   Whale Monitor:   {'✅ Loaded' if self.whale_scheduler else '❌ Not Available'}")
        trading_status = '✅ Loaded' if self.whale_scheduler and hasattr(self.whale_scheduler, 'trading_enabled') and self.whale_scheduler.trading_enabled else '❌ Disabled'
        logger.info(f"   Trading System:  {trading_status}")
        logger.info(f"   Bot Commands:    {'✅ Loaded (WEBHOOK)' if self.bot_application else '❌ Not Available'}")
        
        logger.info("\n🔧 CONFIGURATION:")
        logger.info(f"   Max Memory:      {self.resource_monitor.max_memory_mb}MB")
        logger.info(f"   Health Checks:   Every {self.health_monitor.check_interval}s")
        logger.info(f"   GC Interval:     Every {self.resource_monitor.gc_interval}s")
        logger.info(f"   Solana Delay:    {self.rate_limiter.chain_delays.get('solana', 0)}s между запросами")
        
        logger.info("\n" + "="*80)
        logger.info(f"⏰ Startup Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("="*80 + "\n")
    
    def _print_final_statistics(self):
        """Вывод финальной статистики"""
        logger.info("\n" + "="*80)
        logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        logger.info("="*80)
        
        uptime = self.health_monitor.get_uptime()
        logger.info(f"\n⏱️ UPTIME: {self.health_monitor._format_duration(uptime.total_seconds())}")
        
        health_stats = self.health_monitor.get_stats()
        
        logger.info("\n💚 HEALTH MONITOR:")
        logger.info(f"   Total Cycles: {health_stats['total_cycles']}")
        logger.info(f"   Total Errors: {health_stats['total_errors']}")
        logger.info(f"   Bot Commands Processed: {health_stats['total_bot_commands']}")
        
        if health_stats['total_cycles'] > 0:
            error_rate = (health_stats['total_errors'] / health_stats['total_cycles']) * 100
            logger.info(f"   Error Rate: {error_rate:.2f}%")
        
        logger.info("\n🔒 RATE LIMITER:")
        rate_stats = self.rate_limiter.get_stats()
        for chain, stats in rate_stats['chains'].items():
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = (stats['successful_requests'] / stats['total_requests']) * 100
            
            logger.info(f"   {chain}:")
            logger.info(f"     Requests: {stats['total_requests']} (Success: {success_rate:.1f}%)")
            logger.info(f"     429 Errors: {stats['total_429_errors']}")
            logger.info(f"     Recovery Attempts: {stats['recovery_attempts']}")
        
        resource_stats = self.resource_monitor.get_stats()
        if resource_stats:
            logger.info("\n💾 RESOURCES:")
            logger.info(f"   Memory: {resource_stats.get('memory_mb', 0):.1f}MB ({resource_stats.get('memory_percent', 0):.1f}%)")
            logger.info(f"   CPU: {resource_stats.get('cpu_percent', 0):.1f}%")
            logger.info(f"   Threads: {resource_stats.get('num_threads', 0)}")
            logger.info(f"   Memory Warnings: {resource_stats.get('memory_warnings', 0)}")
            logger.info(f"   GC Runs: {resource_stats.get('gc_runs', 0)}")
        
        logger.info("\n📊 ОБЩАЯ СТАТИСТИКА:")
        logger.info(f"   Total Publications: {self.stats['total_publications']}")
        logger.info(f"   ├─ News: {self.stats['news_publications']}")
        logger.info(f"   ├─ Whale: {self.stats['whale_publications']}")
        logger.info(f"   └─ Trading: {self.stats['trading_publications']}")
        logger.info(f"   Bot Commands: {self.stats['bot_commands']}")
        logger.info(f"   Errors Caught: {self.stats['errors_caught']}")
        logger.info(f"   System Restarts: {self.stats['restarts']}")
        
        logger.info("\n" + "="*80)


def check_dependencies() -> bool:
    """Проверка установленных зависимостей"""
    logger.info("🔍 Проверка зависимостей...\n")
    
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp',
        'feedparser': 'feedparser',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'sklearn': 'scikit-learn',
        'psutil': 'psutil'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            logger.info(f"   ✅ {package}")
        except ImportError:
            logger.error(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        logger.error(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}")
        logger.info("\nУстановите их командой:")
        logger.info(f"pip install {' '.join(missing)}")
        return False
    
    logger.info("\n✅ Все зависимости установлены")
    return True


def create_directories():
    """Создание необходимых директорий"""
    logger.info("\n📁 Создание директорий...\n")
    
    directories = [
        Path("data"),
        Path("data/history"),
        Path("data/learning"),
        Path("data/wallets"),
        Path("data/positions"),
        Path("data/performance"),
        Path("logs"),
        Path("core"),
    ]
    
    if not Path("/tmp").exists():
        directories.append(Path("/tmp"))
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"   ✅ {directory}")
        except Exception as e:
            logger.warning(f"   ⚠️ {directory}: {e}")
    
    logger.info("")


def print_system_info():
    """Вывод информации о системе"""
    logger.info("="*80)
    logger.info("💎 CRYPTO COMPASS - Integrated Monitoring System v4.5")
    logger.info("="*80)
    logger.info(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"🐍 Python {sys.version.split()[0]}")
    logger.info(f"💻 Platform: {sys.platform}")
    logger.info(f"📂 Working Directory: {os.getcwd()}")
    logger.info("="*80 + "\n")


def main():
    """Главная точка входа"""
    print_system_info()
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    logger.info("🚀 Запуск Integrated Crypto Monitor v4.5...\n")
    
    bot = IntegratedCryptoMonitor()
    
    try:
        if sys.version_info >= (3, 7):
            asyncio.run(bot.run())
        else:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(bot.run())
            finally:
                loop.close()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Остановка по Ctrl+C")
    
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка в main:")
        logger.error("="*80)
        tb.print_exc()
        logger.error("="*80)
        sys.exit(1)
    
    logger.info("\n👋 Goodbye!")


if __name__ == '__main__':
    main()