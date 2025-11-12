# core/monitor.py
"""
Integrated Crypto Monitor v5.2
===============================

Production-Ready система мониторинга криптовалют.

ИСПРАВЛЕНО v5.2:
- Правильное создание shutdown_task ДО wait()
- Корректная проверка завершенных задач
- Убран двойной cleanup (только через stop())
- Все методы существуют и работают

Architecture v5.2:
------------------
- Core: Rate limiter, resource monitor, health monitor, statistics
- Business: News, whale, trading, bot (lazy-loaded через ComponentManager)
- Infrastructure: HTTP server, direct task launching, shutdown coordination
"""

import asyncio
import logging
from typing import Optional, Any, Dict, List, Set
from datetime import datetime

from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer
from core.bot_patcher import BotHandlerPatcher
from core.statistics import SystemStatistics, StatisticsReporter

logger = logging.getLogger(__name__)


class MonitorCore:
    """
    Core компоненты монитора без внешних зависимостей
    
    Components:
    - Rate limiter: Управление rate limits для blockchain APIs
    - Resource monitor: Мониторинг памяти, CPU, GC
    - Health monitor: Health checks системы
    - Statistics: Сбор и хранение статистики
    """
    
    def __init__(self, max_memory_mb: int = 450):
        """
        Инициализация core компонентов
        
        Args:
            max_memory_mb: Лимит памяти в MB
        """
        logger.debug("[CORE] Initializing MonitorCore...")
        
        self.rate_limiter = ChainRateLimiter()
        self.resource_monitor = ResourceMonitor(max_memory_mb=max_memory_mb)
        self.health_monitor = SystemHealthMonitor()
        self.statistics = SystemStatistics()
        
        logger.debug("[CORE] ✅ MonitorCore initialized")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику всех core компонентов
        
        Returns:
            Dict со статистикой health, resources, rate_limiting
        """
        return {
            'health': self.health_monitor.get_stats(),
            'resources': self.resource_monitor.get_stats(),
            'rate_limiting': self.rate_limiter.get_stats()
        }


class MonitorBusinessLayer:
    """
    Business компоненты с lazy loading
    
    Components (loaded via ComponentManager):
    - News processor: Обработка и публикация новостей
    - Whale scheduler: Мониторинг крупных транзакций
    - Trading system: Генерация торговых сигналов
    - Bot application: Telegram bot интерфейс
    """
    
    def __init__(self):
        """Инициализация business layer (без загрузки компонентов)"""
        self._component_manager: Optional[Any] = None
        self._initialized = False
        logger.debug("[BUSINESS] MonitorBusinessLayer created")
    
    async def initialize(self) -> bool:
        """
        Асинхронная инициализация и загрузка business компонентов
        
        Returns:
            bool: True если успешно
        """
        if self._initialized:
            logger.debug("[BUSINESS] Already initialized")
            return True
        
        try:
            logger.info("[BUSINESS] Initializing business layer...")
            
            # Lazy import ComponentManager для избежания циклических зависимостей
            from core.components import ComponentManager
            
            self._component_manager = ComponentManager()
            self._component_manager.load_all()
            
            status = self._component_manager.get_status_dict()
            active = status.get('total_active', 0)
            
            self._initialized = True
            logger.info(f"[BUSINESS] ✅ Business layer initialized ({active} components active)")
            
            return True
        
        except Exception as e:
            logger.error(f"[BUSINESS] ❌ Init failed: {e}", exc_info=True)
            return False
    
    @property
    def component_manager(self) -> Optional[Any]:
        """Получить component manager (может быть None)"""
        return self._component_manager
    
    @property
    def is_initialized(self) -> bool:
        """Проверить статус инициализации"""
        return self._initialized
    
    def has_component(self, name: str) -> bool:
        """
        Проверить наличие и готовность компонента
        
        Args:
            name: Имя компонента (news, whale, trading, bot)
            
        Returns:
            bool: True если компонент загружен
        """
        if not self._component_manager:
            return False
        
        checks = {
            'news': lambda: self._component_manager.news_processor is not None,
            'whale': lambda: self._component_manager.whale_scheduler is not None,
            'trading': lambda: self._component_manager.has_trading(),
            'bot': lambda: self._component_manager.bot_application is not None
        }
        
        checker = checks.get(name)
        if not checker:
            return False
        
        try:
            return checker()
        except Exception:
            return False
    
    async def stop_all(self) -> None:
        """Остановить все business компоненты"""
        if self._component_manager:
            try:
                await self._component_manager.stop_all()
                logger.info("[BUSINESS] ✅ All components stopped")
            except Exception as e:
                logger.error(f"[BUSINESS] ❌ Stop error: {e}", exc_info=True)
    
    async def cleanup(self) -> None:
        """Очистить ресурсы business компонентов"""
        if self._component_manager:
            try:
                await self._component_manager.cleanup()
                logger.info("[BUSINESS] ✅ Cleanup complete")
            except Exception as e:
                logger.error(f"[BUSINESS] ❌ Cleanup error: {e}", exc_info=True)


class MonitorInfrastructure:
    """
    Infrastructure компоненты v5.2
    
    Responsibilities:
    - HTTP server management
    - Direct business task launching
    - Shutdown coordination
    - Task lifecycle management
    """
    
    def __init__(self, core: MonitorCore, business: MonitorBusinessLayer):
        """
        Инициализация infrastructure
        
        Args:
            core: Core компоненты
            business: Business layer
        """
        self.core = core
        self.business = business
        
        # HTTP server
        self.http_server: Optional[HTTPServer] = None
        
        # Shutdown coordination
        self.shutdown_event = asyncio.Event()
        
        # Running tasks storage
        self._running_tasks: List[asyncio.Task] = []
        
        logger.debug("[INFRA] MonitorInfrastructure created")
    
    async def initialize_http_server(self) -> bool:
        """
        Инициализация HTTP сервера
        
        Returns:
            bool: True если успешно
        """
        try:
            logger.info("[INFRA] Initializing HTTP server...")
            
            # Получаем bot app если доступен
            bot_app = None
            if self.business.component_manager:
                try:
                    bot_app = self.business.component_manager.bot_application
                except Exception:
                    pass
            
            # Создаем HTTP server
            self.http_server = HTTPServer(
                health_monitor=self.core.health_monitor,
                resource_monitor=self.core.resource_monitor,
                rate_limiter=self.core.rate_limiter,
                bot_application=bot_app
            )
            
            logger.info("[INFRA] ✅ HTTP server initialized")
            return True
        
        except Exception as e:
            logger.error(f"[INFRA] ❌ HTTP init failed: {e}", exc_info=True)
            return False
    
    async def start_http_server(self) -> bool:
        """
        Запуск HTTP сервера
        
        Returns:
            bool: True если успешно
        """
        if not self.http_server:
            logger.error("[INFRA] HTTP server not initialized")
            return False
        
        try:
            logger.info("[INFRA] Starting HTTP server...")
            await self.http_server.start()
            logger.info("[INFRA] ✅ HTTP server started")
            return True
        
        except Exception as e:
            logger.error(f"[INFRA] ❌ HTTP start failed: {e}", exc_info=True)
            return False
    
    async def stop_http_server(self) -> None:
        """Остановка HTTP сервера"""
        if self.http_server:
            try:
                await self.http_server.stop()
                logger.info("[INFRA] ✅ HTTP server stopped")
            except Exception as e:
                logger.error(f"[INFRA] ❌ HTTP stop error: {e}", exc_info=True)
    
    async def start_business_tasks(self) -> bool:
        """
        Запуск всех business задач напрямую
        
        Запускает как asyncio.Task:
        - News processor
        - Whale scheduler
        - Trading system
        - Bot application
        
        Returns:
            bool: True если хотя бы одна задача запущена
        """
        if not self.business.component_manager:
            logger.error("[INFRA] Component manager not available")
            return False
        
        try:
            logger.info("="*80)
            logger.info("[INFRA] 🎯 STARTING BUSINESS TASKS")
            logger.info("="*80)
            
            cm = self.business.component_manager
            started = []
            
            # News processor
            if cm.news_processor:
                try:
                    task = asyncio.create_task(
                        self._run_news_processor(cm.news_processor),
                        name="NewsProcessor"
                    )
                    self._running_tasks.append(task)
                    started.append('news')
                    logger.info("[INFRA] ✅ News task started")
                except Exception as e:
                    logger.error(f"[INFRA] ❌ News start error: {e}", exc_info=True)
            
            # Whale scheduler
            if cm.whale_scheduler:
                try:
                    task = asyncio.create_task(
                        self._run_whale_scheduler(cm.whale_scheduler),
                        name="WhaleScheduler"
                    )
                    self._running_tasks.append(task)
                    started.append('whale')
                    logger.info("[INFRA] ✅ Whale task started")
                except Exception as e:
                    logger.error(f"[INFRA] ❌ Whale start error: {e}", exc_info=True)
            
            # Trading system
            if cm.has_trading():
                try:
                    task = asyncio.create_task(
                        self._run_trading_system(cm.trading_system),
                        name="TradingSystem"
                    )
                    self._running_tasks.append(task)
                    started.append('trading')
                    logger.info("[INFRA] ✅ Trading task started")
                except Exception as e:
                    logger.error(f"[INFRA] ❌ Trading start error: {e}", exc_info=True)
            
            # Bot application
            if cm.bot_application:
                try:
                    task = asyncio.create_task(
                        self._run_bot_application(cm.bot_application),
                        name="BotApplication"
                    )
                    self._running_tasks.append(task)
                    started.append('bot')
                    logger.info("[INFRA] ✅ Bot task started")
                except Exception as e:
                    logger.error(f"[INFRA] ❌ Bot start error: {e}", exc_info=True)
            
            logger.info("="*80)
            logger.info(f"[INFRA] 📊 Started {len(started)} tasks: {', '.join(started)}")
            logger.info("="*80)
            
            return len(started) > 0
        
        except Exception as e:
            logger.error(f"[INFRA] ❌ Task start failed: {e}", exc_info=True)
            return False
    
    async def _run_news_processor(self, processor: Any) -> None:
        """
        Wrapper для запуска news processor
        
        Args:
            processor: News processor instance
        """
        try:
            logger.info("[NEWS] Starting processor...")
            
            if hasattr(processor, 'run'):
                await processor.run()
            elif hasattr(processor, 'start'):
                await processor.start()
            else:
                logger.warning("[NEWS] No run/start method found")
        
        except asyncio.CancelledError:
            logger.info("[NEWS] Task cancelled")
            raise
        except Exception as e:
            logger.error(f"[NEWS] Task error: {e}", exc_info=True)
            self.core.statistics.increment_errors()
    
    async def _run_whale_scheduler(self, scheduler: Any) -> None:
        """
        Wrapper для запуска whale scheduler
        
        Args:
            scheduler: Whale scheduler instance
        """
        try:
            logger.info("[WHALE] Starting scheduler...")
            
            if hasattr(scheduler, 'run'):
                await scheduler.run()
            elif hasattr(scheduler, 'start'):
                await scheduler.start()
            else:
                logger.warning("[WHALE] No run/start method found")
        
        except asyncio.CancelledError:
            logger.info("[WHALE] Task cancelled")
            raise
        except Exception as e:
            logger.error(f"[WHALE] Task error: {e}", exc_info=True)
            self.core.statistics.increment_errors()
    
    async def _run_trading_system(self, system: Any) -> None:
        """
        Wrapper для запуска trading system
        
        Args:
            system: Trading system instance
        """
        try:
            logger.info("[TRADING] Starting system...")
            
            if hasattr(system, 'run'):
                await system.run()
            elif hasattr(system, 'start'):
                await system.start()
            else:
                logger.warning("[TRADING] No run/start method found")
        
        except asyncio.CancelledError:
            logger.info("[TRADING] Task cancelled")
            raise
        except Exception as e:
            logger.error(f"[TRADING] Task error: {e}", exc_info=True)
            self.core.statistics.increment_errors()
    
    async def _run_bot_application(self, bot_app: Any) -> None:
        """
        Wrapper для запуска bot application
        
        Args:
            bot_app: Bot application instance
        """
        try:
            logger.info("[BOT] Starting application...")
            
            if hasattr(bot_app, 'run_polling'):
                await bot_app.run_polling()
            elif hasattr(bot_app, 'run'):
                await bot_app.run()
            else:
                logger.warning("[BOT] No run_polling/run method found")
        
        except asyncio.CancelledError:
            logger.info("[BOT] Task cancelled")
            raise
        except Exception as e:
            logger.error(f"[BOT] Task error: {e}", exc_info=True)
            self.core.statistics.increment_errors()
    
    async def stop_business_tasks(self) -> None:
        """Остановка всех business задач"""
        logger.info("[INFRA] Stopping business tasks...")
        
        # Отменяем все задачи
        for task in self._running_tasks:
            if not task.done():
                task.cancel()
        
        # Ждем завершения с обработкой исключений
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        self._running_tasks.clear()
        logger.info("[INFRA] ✅ Business tasks stopped")
    
    async def wait_for_completion(self) -> None:
        """
        Ожидание завершения задач или shutdown signal
        
        ИСПРАВЛЕНО v5.2:
        - Создаем shutdown_task ДО wait()
        - Правильная проверка завершенных задач
        - Корректная отмена pending задач
        """
        logger.info("[INFRA] Waiting for completion or shutdown signal...")
        
        try:
            if not self._running_tasks:
                # Нет задач - просто ждем shutdown
                logger.info("[INFRA] No tasks running, waiting for shutdown event...")
                await self.shutdown_event.wait()
                return
            
            # Создаем shutdown task ДО wait() чтобы иметь на него ссылку
            shutdown_task = asyncio.create_task(
                self.shutdown_event.wait(),
                name="ShutdownWaiter"
            )
            
            # Ждем пока завершится ЛЮБАЯ задача или shutdown
            all_tasks = self._running_tasks + [shutdown_task]
            
            done, pending = await asyncio.wait(
                all_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Проверяем что завершилось
            shutdown_triggered = False
            
            for task in done:
                task_name = task.get_name()
                
                if task_name == "ShutdownWaiter":
                    # Shutdown event был установлен
                    logger.info("[INFRA] ⏹️ Shutdown signal received")
                    shutdown_triggered = True
                else:
                    # Business задача завершилась
                    logger.warning(f"[INFRA] ⚠️ Task {task_name} completed unexpectedly")
                    
                    # Проверяем exception
                    try:
                        exc = task.exception()
                        if exc:
                            logger.error(f"[INFRA] Task {task_name} failed: {exc}")
                    except asyncio.CancelledError:
                        pass
                    
                    # Устанавливаем shutdown
                    shutdown_triggered = True
            
            # Если shutdown триггернулся - устанавливаем event
            if shutdown_triggered and not self.shutdown_event.is_set():
                self.shutdown_event.set()
            
            # Отменяем pending задачи
            for task in pending:
                if not task.done():
                    task.cancel()
        
        except Exception as e:
            logger.error(f"[INFRA] ❌ Wait error: {e}", exc_info=True)
            self.shutdown_event.set()
    
    def request_shutdown(self) -> None:
        """Запрос на graceful shutdown"""
        logger.info("[INFRA] Shutdown requested")
        self.shutdown_event.set()


class IntegratedCryptoMonitor:
    """
    Production-Ready Integrated Crypto Monitor v5.2
    
    Main monitoring system coordinator.
    
    ИСПРАВЛЕНО v5.2:
    - Правильный wait_for_completion
    - Убран двойной cleanup (только через stop())
    - Все методы существуют
    
    Architecture:
    - Core: Rate limiter, monitors, statistics
    - Business: News, whale, trading, bot
    - Infrastructure: HTTP, tasks, shutdown
    
    Lifecycle:
    1. __init__: Core initialization
    2. initialize(): Business components loading
    3. run(): Start services and wait
    4. stop(): Graceful shutdown
    """
    
    VERSION = "5.2.0"
    
    def __init__(self, max_memory_mb: int = 450):
        """
        Инициализация integrated crypto monitor
        
        Args:
            max_memory_mb: Лимит памяти в MB
        """
        self._print_init_banner()
        
        # Core layer (без зависимостей)
        self.core = MonitorCore(max_memory_mb=max_memory_mb)
        
        # Business layer (lazy loading)
        self.business = MonitorBusinessLayer()
        
        # Infrastructure layer
        self.infrastructure = MonitorInfrastructure(self.core, self.business)
        
        # State
        self.running = False
        self.start_time: Optional[datetime] = None
        self._fully_initialized = False
        
        logger.info("✅ IntegratedCryptoMonitor core initialized")
    
    async def initialize(self) -> bool:
        """
        Async инициализация business компонентов и infrastructure
        
        Returns:
            bool: True если успешно
        """
        if self._fully_initialized:
            logger.debug("Monitor already fully initialized")
            return True
        
        try:
            logger.info("="*80)
            logger.info(f"🔄 Initializing Monitor v{self.VERSION}...")
            logger.info("="*80)
            
            # Business layer
            if not await self.business.initialize():
                logger.error("❌ Business layer init failed")
                return False
            
            # Connections
            self._connect_rate_limiter()
            self._patch_bot_handlers()
            
            # HTTP server
            if not await self.infrastructure.initialize_http_server():
                logger.error("❌ HTTP server init failed")
                return False
            
            self._fully_initialized = True
            
            logger.info("="*80)
            logger.info("✅ Monitor fully initialized")
            logger.info("="*80)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    def _connect_rate_limiter(self) -> None:
        """Подключение rate limiter к whale scheduler"""
        if not self.business.component_manager:
            return
        
        try:
            whale = self.business.component_manager.whale_scheduler
            
            if whale and hasattr(whale, 'set_rate_limiter'):
                whale.set_rate_limiter(self.core.rate_limiter)
                logger.info("✅ Rate limiter connected to whale scheduler")
        
        except Exception as e:
            logger.debug(f"Rate limiter connection: {e}")
    
    def _patch_bot_handlers(self) -> None:
        """Патчинг bot handlers для мониторинга"""
        if not self.business.component_manager:
            return
        
        try:
            bot_app = self.business.component_manager.bot_application
            
            if bot_app:
                patcher = BotHandlerPatcher(
                    self.core.health_monitor,
                    self.core.statistics
                )
                
                if patcher.patch_handlers(bot_app):
                    logger.info("✅ Bot handlers patched")
        
        except Exception as e:
            logger.debug(f"Bot handler patching: {e}")
    
    async def run(self) -> None:
        """
        Главный цикл монитора v5.2
        
        ИСПРАВЛЕНО v5.2:
        - Убран _cleanup() из finally (только stop())
        - stop() сам делает полный cleanup
        
        Sequence:
        1. Start HTTP server
        2. Start business tasks
        3. Wait for completion
        4. Cleanup через stop()
        """
        if not self._fully_initialized:
            logger.error("Monitor not fully initialized. Call initialize() first.")
            return
        
        self._print_startup_banner()
        self.running = True
        self.start_time = datetime.now()
        
        try:
            # Start HTTP server
            if not await self.infrastructure.start_http_server():
                raise RuntimeError("HTTP server start failed")
            
            # Start business tasks
            if not await self.infrastructure.start_business_tasks():
                raise RuntimeError("Business tasks start failed")
            
            # Wait for completion
            await self.infrastructure.wait_for_completion()
        
        except asyncio.CancelledError:
            logger.info("\n⏹️ Monitor cancelled")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ KeyboardInterrupt received")
        
        except Exception as e:
            logger.error(f"\n❌ Critical error in monitor: {e}", exc_info=True)
            self.core.statistics.increment_errors()
        
        finally:
            self.running = False
    
    async def stop(self) -> None:
        """
        Graceful shutdown v5.2
        
        ИСПРАВЛЕНО v5.2:
        - Включает полный cleanup
        - Вызывается один раз
        
        Sequence:
        1. Request shutdown
        2. Stop business tasks
        3. Stop HTTP server
        4. Stop business components
        5. Final statistics
        6. Cleanup
        """
        logger.info("="*80)
        logger.info("🛑 Stopping IntegratedCryptoMonitor...")
        logger.info("="*80)
        
        try:
            # Request shutdown
            self.infrastructure.request_shutdown()
            
            # Stop tasks
            await self.infrastructure.stop_business_tasks()
            
            # Stop HTTP
            await self.infrastructure.stop_http_server()
            
            # Stop business
            await self.business.stop_all()
            
            # Statistics
            self._print_final_statistics()
            
            # Cleanup
            await self.business.cleanup()
            
            logger.info("="*80)
            logger.info("✅ Monitor stopped successfully")
            logger.info("="*80)
        
        except Exception as e:
            logger.error(f"❌ Stop error: {e}", exc_info=True)
    
    def _print_init_banner(self) -> None:
        """Вывод init banner"""
        logger.info("\n" + "="*80)
        logger.info(f"🚀 INITIALIZING MONITOR v{self.VERSION}")
        logger.info("="*80 + "\n")
    
    def _print_startup_banner(self) -> None:
        """Вывод startup banner"""
        try:
            reporter = StatisticsReporter(self.core.statistics)
            
            reporter.print_startup_banner(
                has_news=self.business.has_component('news'),
                has_whale=self.business.has_component('whale'),
                has_trading=self.business.has_component('trading'),
                has_bot=self.business.has_component('bot'),
                max_memory_mb=self.core.resource_monitor.max_memory_mb,
                health_check_interval=self.core.health_monitor.check_interval,
                gc_interval=self.core.resource_monitor.gc_interval,
                solana_delay=self.core.rate_limiter.chain_delays.get('solana', 0)
            )
        
        except Exception as e:
            logger.error(f"❌ Banner error: {e}", exc_info=True)
    
    def _print_final_statistics(self) -> None:
        """Вывод финальной статистики"""
        logger.info("="*80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*80)
        
        try:
            reporter = StatisticsReporter(self.core.statistics)
            stats = self.core.get_stats()
            
            reporter.print_final_statistics(
                health_stats=stats['health'],
                rate_stats=stats['rate_limiting'],
                resource_stats=stats['resources']
            )
        
        except Exception as e:
            logger.error(f"❌ Statistics error: {e}", exc_info=True)
        
        logger.info("="*80)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получить статус монитора
        
        Returns:
            Dict со статусом всех компонентов
        """
        try:
            uptime = None
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                'version': self.VERSION,
                'running': self.running,
                'fully_initialized': self._fully_initialized,
                'uptime_seconds': uptime,
                'shutdown_requested': self.infrastructure.shutdown_event.is_set(),
                'components': {
                    'news': self.business.has_component('news'),
                    'whale': self.business.has_component('whale'),
                    'trading': self.business.has_component('trading'),
                    'bot': self.business.has_component('bot')
                },
                'core': self.core.get_stats()
            }
        
        except Exception as e:
            logger.error(f"❌ Status error: {e}", exc_info=True)
            return {
                'version': self.VERSION,
                'running': self.running,
                'error': str(e)
            }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"IntegratedCryptoMonitor("
            f"v{self.VERSION}, "
            f"running={self.running}, "
            f"initialized={self._fully_initialized}"
            f")"
        )


__all__ = ['IntegratedCryptoMonitor']