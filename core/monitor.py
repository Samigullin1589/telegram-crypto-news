# core/monitor.py
"""
Integrated Crypto Monitor - Production Ready v5.0
==================================================

Главная система мониторинга криптовалют с полным разделением ответственности.

Architecture Changes v5.0:
--------------------------
- Двухэтапная инициализация (sync __init__ + async initialize)
- Полное разделение core и business компонентов
- Устранение всех циклических зависимостей
- Модульная архитектура с четким разделением ответственности
- Production-grade error handling и recovery

Components:
-----------
- Core Layer: Rate limiter, resource monitor, health monitor
- Business Layer: News, whale, trading, bot (lazy-loaded)
- Infrastructure Layer: HTTP server, task manager, statistics

Initialization Flow:
--------------------
1. __init__: Создание core компонентов (без внешних зависимостей)
2. initialize(): Async загрузка business компонентов
3. run(): Запуск всех сервисов и задач
4. stop(): Graceful shutdown

This module coordinates:
- Resource monitoring and rate limiting
- HTTP server for health checks
- Business components lifecycle
- Graceful shutdown protocol
"""

import asyncio
import logging
import os
from typing import Optional, Any, Dict
from datetime import datetime

from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer
from core.bot_patcher import BotHandlerPatcher
from core.statistics import SystemStatistics, StatisticsReporter
from core.tasks import TaskManager

logger = logging.getLogger(__name__)


class MonitorCore:
    """
    Core компоненты монитора (без внешних зависимостей)
    
    Отвечает за:
    - Rate limiting
    - Resource monitoring
    - Health checks
    - Statistics collection
    
    Эти компоненты безопасны для создания в __init__
    так как не имеют циклических зависимостей.
    """
    
    def __init__(self, max_memory_mb: int = 450):
        """
        Инициализация core компонентов
        
        Args:
            max_memory_mb: Максимальный объем памяти в MB
        """
        logger.debug("Initializing MonitorCore...")
        
        self.rate_limiter = ChainRateLimiter()
        self.resource_monitor = ResourceMonitor(max_memory_mb=max_memory_mb)
        self.health_monitor = SystemHealthMonitor()
        self.statistics = SystemStatistics()
        
        logger.debug("✅ MonitorCore initialized")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику core компонентов"""
        return {
            'health': self.health_monitor.get_stats(),
            'resources': self.resource_monitor.get_stats(),
            'rate_limiting': self.rate_limiter.get_stats()
        }


class MonitorBusinessLayer:
    """
    Business компоненты монитора (с lazy loading)
    
    Отвечает за:
    - News processing
    - Whale monitoring
    - Trading system
    - Telegram bot
    
    Компоненты загружаются асинхронно через initialize()
    для предотвращения циклических зависимостей.
    """
    
    def __init__(self):
        """Инициализация business layer"""
        self._component_manager: Optional[Any] = None
        self._initialized = False
        logger.debug("MonitorBusinessLayer created (not initialized)")
    
    async def initialize(self) -> bool:
        """
        Асинхронная инициализация business компонентов
        
        Returns:
            bool: True если инициализация успешна
        """
        if self._initialized:
            logger.debug("Business layer already initialized")
            return True
        
        try:
            logger.info("Initializing business layer...")
            
            # Lazy import ComponentManager
            from core.components import ComponentManager
            
            self._component_manager = ComponentManager()
            
            # Загружаем компоненты
            self._component_manager.load_all()
            
            # Проверяем что загрузилось
            status = self._component_manager.get_status_dict()
            active_count = status.get('total_active', 0)
            
            self._initialized = True
            logger.info(f"✅ Business layer initialized ({active_count} components active)")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize business layer: {e}", exc_info=True)
            return False
    
    @property
    def component_manager(self) -> Optional[Any]:
        """Получить component manager (может быть None если не инициализирован)"""
        return self._component_manager
    
    @property
    def is_initialized(self) -> bool:
        """Проверить статус инициализации"""
        return self._initialized
    
    def has_component(self, name: str) -> bool:
        """
        Проверить наличие компонента
        
        Args:
            name: Имя компонента (news, whale, trading, bot)
        """
        if not self._component_manager:
            return False
        
        component_map = {
            'news': lambda: self._component_manager.news_processor is not None,
            'whale': lambda: self._component_manager.whale_scheduler is not None,
            'trading': lambda: self._component_manager.has_trading(),
            'bot': lambda: self._component_manager.bot_application is not None
        }
        
        checker = component_map.get(name)
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
                logger.info("✅ Business components stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping business components: {e}", exc_info=True)
    
    async def cleanup(self) -> None:
        """Очистить ресурсы business компонентов"""
        if self._component_manager:
            try:
                await self._component_manager.cleanup()
                logger.info("✅ Business layer cleaned up")
            except Exception as e:
                logger.error(f"❌ Error cleaning up business layer: {e}", exc_info=True)


class MonitorInfrastructure:
    """
    Infrastructure компоненты монитора
    
    Отвечает за:
    - HTTP server (health checks, metrics, webhooks)
    - Task manager (координация async задач)
    - Shutdown coordination
    """
    
    def __init__(
        self,
        core: MonitorCore,
        business: MonitorBusinessLayer
    ):
        """
        Инициализация infrastructure
        
        Args:
            core: Core компоненты
            business: Business layer
        """
        self.core = core
        self.business = business
        
        # HTTP server (создается сразу)
        self.http_server: Optional[HTTPServer] = None
        
        # Task manager (создается при запуске)
        self.task_manager: Optional[TaskManager] = None
        
        # Shutdown coordination
        self.shutdown_event = asyncio.Event()
        
        logger.debug("MonitorInfrastructure created")
    
    async def initialize_http_server(self) -> bool:
        """
        Инициализация HTTP сервера
        
        Returns:
            bool: True если успешно
        """
        try:
            logger.info("Initializing HTTP server...")
            
            # Получаем bot application если доступен
            bot_app = None
            if self.business.component_manager:
                try:
                    bot_app = self.business.component_manager.bot_application
                except Exception as e:
                    logger.debug(f"Bot application not available: {e}")
            
            # Создаем HTTP сервер
            self.http_server = HTTPServer(
                health_monitor=self.core.health_monitor,
                resource_monitor=self.core.resource_monitor,
                rate_limiter=self.core.rate_limiter,
                bot_application=bot_app
            )
            
            logger.info("✅ HTTP server initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize HTTP server: {e}", exc_info=True)
            return False
    
    async def start_http_server(self) -> bool:
        """
        Запуск HTTP сервера
        
        Returns:
            bool: True если успешно
        """
        if not self.http_server:
            logger.error("HTTP server not initialized")
            return False
        
        try:
            logger.info("Starting HTTP server...")
            await self.http_server.start()
            logger.info("✅ HTTP server started")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to start HTTP server: {e}", exc_info=True)
            return False
    
    async def stop_http_server(self) -> None:
        """Остановка HTTP сервера"""
        if self.http_server:
            try:
                await self.http_server.stop()
                logger.info("✅ HTTP server stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping HTTP server: {e}", exc_info=True)
    
    async def initialize_task_manager(self) -> bool:
        """
        Инициализация task manager
        
        Returns:
            bool: True если успешно
        """
        if not self.business.component_manager:
            logger.error("Cannot initialize task manager: business layer not initialized")
            return False
        
        try:
            logger.info("Initializing task manager...")
            
            self.task_manager = TaskManager(
                components=self.business.component_manager,
                health_monitor=self.core.health_monitor,
                resource_monitor=self.core.resource_monitor,
                statistics=self.core.statistics,
                shutdown_event=self.shutdown_event
            )
            
            logger.info("✅ Task manager initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize task manager: {e}", exc_info=True)
            return False
    
    async def start_tasks(self) -> bool:
        """
        Запуск всех задач
        
        Returns:
            bool: True если успешно
        """
        if not self.task_manager:
            logger.error("Task manager not initialized")
            return False
        
        try:
            logger.info("Starting all tasks...")
            await self.task_manager.start_all_tasks()
            logger.info("✅ All tasks started")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to start tasks: {e}", exc_info=True)
            return False
    
    async def stop_tasks(self) -> None:
        """Остановка всех задач"""
        if self.task_manager:
            try:
                await self.task_manager.stop_all_tasks()
                logger.info("✅ Tasks stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping tasks: {e}", exc_info=True)
    
    async def wait_for_completion(self) -> None:
        """Ожидание завершения задач или shutdown signal"""
        if not self.task_manager:
            logger.warning("Task manager not initialized, waiting for shutdown event...")
            await self.shutdown_event.wait()
            return
        
        try:
            logger.info("Waiting for task completion or shutdown signal...")
            
            done = await self.task_manager.wait_for_completion()
            
            if done:
                self.task_manager.handle_completed_tasks(done)
                logger.info("Tasks completed, initiating shutdown...")
                self.shutdown_event.set()
        
        except Exception as e:
            logger.error(f"❌ Error waiting for completion: {e}", exc_info=True)
            self.shutdown_event.set()
    
    def request_shutdown(self) -> None:
        """Запрос на остановку"""
        self.shutdown_event.set()


class IntegratedCryptoMonitor:
    """
    Production-ready интегрированная система мониторинга v5.0
    
    Архитектура:
    ------------
    - MonitorCore: Rate limiting, resource monitoring, health checks
    - MonitorBusinessLayer: News, whale, trading, bot (lazy-loaded)
    - MonitorInfrastructure: HTTP server, task manager
    
    Инициализация:
    --------------
    1. __init__: Создание core компонентов
    2. initialize(): Async загрузка business компонентов
    3. run(): Запуск сервисов
    
    Attributes:
        core: Core компоненты (rate limiter, monitors, statistics)
        business: Business компоненты (news, whale, trading, bot)
        infrastructure: Infrastructure (HTTP, tasks, shutdown)
        running: Флаг работы системы
        start_time: Время запуска
    """
    
    VERSION = "5.0.0"
    
    def __init__(self, max_memory_mb: int = 450):
        """
        Инициализация integrated crypto monitor
        
        Создает только core компоненты без внешних зависимостей.
        Business компоненты загружаются через initialize().
        
        Args:
            max_memory_mb: Максимальный объем памяти
        """
        self._print_init_banner()
        
        # Core компоненты (без внешних зависимостей)
        self.core = MonitorCore(max_memory_mb=max_memory_mb)
        
        # Business layer (будет инициализирован в initialize())
        self.business = MonitorBusinessLayer()
        
        # Infrastructure (зависит от core и business)
        self.infrastructure = MonitorInfrastructure(self.core, self.business)
        
        # Состояние
        self.running = False
        self.start_time: Optional[datetime] = None
        self._fully_initialized = False
        
        logger.info("✅ IntegratedCryptoMonitor core initialized")
    
    async def initialize(self) -> bool:
        """
        Async инициализация business компонентов и infrastructure
        
        Вызывается перед run() для загрузки компонентов с
        возможными циклическими зависимостями.
        
        Returns:
            bool: True если инициализация успешна
        """
        if self._fully_initialized:
            logger.debug("Monitor already fully initialized")
            return True
        
        try:
            logger.info("="*80)
            logger.info("🔄 Initializing IntegratedCryptoMonitor v5.0...")
            logger.info("="*80)
            
            # Инициализируем business layer
            if not await self.business.initialize():
                logger.error("❌ Business layer initialization failed")
                return False
            
            # Подключаем rate limiter к whale scheduler
            self._connect_rate_limiter()
            
            # Патчим bot handlers
            self._patch_bot_handlers()
            
            # Инициализируем HTTP server
            if not await self.infrastructure.initialize_http_server():
                logger.error("❌ HTTP server initialization failed")
                return False
            
            self._fully_initialized = True
            
            logger.info("="*80)
            logger.info("✅ IntegratedCryptoMonitor fully initialized")
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
            whale_scheduler = self.business.component_manager.whale_scheduler
            
            if whale_scheduler and hasattr(whale_scheduler, 'set_rate_limiter'):
                whale_scheduler.set_rate_limiter(self.core.rate_limiter)
                logger.info("✅ Rate limiter connected to whale scheduler")
        
        except Exception as e:
            logger.debug(f"Could not connect rate limiter: {e}")
    
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
                else:
                    logger.warning("⚠️ Bot handlers patching failed")
        
        except Exception as e:
            logger.debug(f"Could not patch bot handlers: {e}")
    
    async def run(self) -> None:
        """
        Главный цикл выполнения монитора
        
        Последовательность:
        1. Проверка инициализации
        2. Запуск HTTP сервера
        3. Запуск task manager
        4. Ожидание completion
        5. Cleanup
        """
        if not self._fully_initialized:
            logger.error("Monitor not fully initialized. Call initialize() first.")
            return
        
        self._print_startup_banner()
        self.running = True
        self.start_time = datetime.now()
        
        try:
            # Запускаем HTTP сервер
            if not await self.infrastructure.start_http_server():
                raise RuntimeError("Failed to start HTTP server")
            
            # Инициализируем и запускаем task manager
            if not await self.infrastructure.initialize_task_manager():
                raise RuntimeError("Failed to initialize task manager")
            
            if not await self.infrastructure.start_tasks():
                raise RuntimeError("Failed to start tasks")
            
            # Ожидаем completion
            await self.infrastructure.wait_for_completion()
        
        except asyncio.CancelledError:
            logger.info("\n⏹️ Monitor tasks cancelled")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ Received KeyboardInterrupt")
        
        except Exception as e:
            logger.error(f"\n❌ Critical error in monitor: {e}", exc_info=True)
            self.core.statistics.increment_errors()
        
        finally:
            self.running = False
            await self._cleanup()
    
    async def stop(self) -> None:
        """
        Graceful остановка монитора
        
        Последовательность:
        1. Request shutdown
        2. Stop tasks
        3. Stop HTTP server
        4. Stop business components
        """
        logger.info("="*80)
        logger.info("🛑 Stopping IntegratedCryptoMonitor...")
        logger.info("="*80)
        
        try:
            # Request shutdown
            self.infrastructure.request_shutdown()
            
            # Stop tasks
            await self.infrastructure.stop_tasks()
            
            # Stop HTTP server
            await self.infrastructure.stop_http_server()
            
            # Stop business components
            await self.business.stop_all()
            
            logger.info("="*80)
            logger.info("✅ Monitor stopped successfully")
            logger.info("="*80)
        
        except Exception as e:
            logger.error(f"❌ Error during stop: {e}", exc_info=True)
    
    async def _cleanup(self) -> None:
        """Финальная очистка ресурсов"""
        logger.info("Performing final cleanup...")
        
        try:
            # Выводим статистику
            self._print_final_statistics()
            
            # Очищаем business layer
            await self.business.cleanup()
            
            logger.info("✅ Cleanup completed")
        
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}", exc_info=True)
    
    def _print_init_banner(self) -> None:
        """Вывод init banner"""
        logger.info("\n" + "="*80)
        logger.info(f"🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v{self.VERSION}")
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
            logger.error(f"❌ Error printing startup banner: {e}", exc_info=True)
    
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
            logger.error(f"❌ Error printing statistics: {e}", exc_info=True)
        
        logger.info("="*80)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса монитора
        
        Returns:
            Словарь со статусом всех компонентов
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
                'core': self.core.get_stats(),
                'http_server': {
                    'running': self.infrastructure.http_server.is_running() 
                    if self.infrastructure.http_server and hasattr(self.infrastructure.http_server, 'is_running')
                    else None
                }
            }
        
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}", exc_info=True)
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