# core/monitor.py
"""
Main integrated crypto monitor
"""

import asyncio
import logging
import os
from typing import Optional

from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer
from core.components import ComponentManager
from core.bot_patcher import BotHandlerPatcher
from core.statistics import SystemStatistics, StatisticsReporter
from core.tasks import TaskManager
from core.shutdown import ShutdownManager

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
        logger.info("\n" + "=" * 80)
        logger.info("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.5")
        logger.info("=" * 80 + "\n")
        
        self._initialize_core_components()
        self._initialize_business_components()
        self._initialize_http_server()
        self._connect_rate_limiter()
        self._patch_bot_handlers()
        self._initialize_state()
        
        logger.info("\n✅ Integrated Crypto Monitor v4.5 инициализирован")
    
    def _initialize_core_components(self):
        """Инициализирует core компоненты"""
        self.rate_limiter = ChainRateLimiter()
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450'))
        )
        self.health_monitor = SystemHealthMonitor()
        self.statistics = SystemStatistics()
    
    def _initialize_business_components(self):
        """Инициализирует business logic компоненты"""
        self.component_manager = ComponentManager()
        self.component_manager.load_all()
    
    def _initialize_http_server(self):
        """Инициализирует HTTP сервер"""
        self.http_server = HTTPServer(
            health_monitor=self.health_monitor,
            resource_monitor=self.resource_monitor,
            rate_limiter=self.rate_limiter,
            bot_application=self.component_manager.bot_application
        )
    
    def _connect_rate_limiter(self):
        """Подключает rate limiter к whale scheduler"""
        whale_scheduler = self.component_manager.whale_scheduler
        
        if whale_scheduler and hasattr(whale_scheduler, 'set_rate_limiter'):
            whale_scheduler.set_rate_limiter(self.rate_limiter)
            logger.info("✅ Rate Limiter v2.1 подключен к Whale Scheduler")
    
    def _patch_bot_handlers(self):
        """Патчит обработчики бота"""
        bot_app = self.component_manager.bot_application
        
        if bot_app:
            patcher = BotHandlerPatcher(self.health_monitor, self.statistics)
            if patcher.patch_handlers(bot_app):
                logger.info("   ✓ Bot handlers патчинг успешен")
    
    def _initialize_state(self):
        """Инициализирует состояние системы"""
        self.shutdown_event = asyncio.Event()
        self.shutdown_manager = ShutdownManager(self.shutdown_event)
    
    async def run(self):
        """Главный цикл выполнения"""
        self._print_startup_banner()
        self.shutdown_manager.setup_signal_handlers()
        
        try:
            await self.http_server.start()
            
            task_manager = TaskManager(
                components=self.component_manager,
                health_monitor=self.health_monitor,
                resource_monitor=self.resource_monitor,
                statistics=self.statistics,
                shutdown_event=self.shutdown_event
            )
            
            await task_manager.start_all_tasks()
            
            done = await task_manager.wait_for_completion()
            
            task_manager.handle_completed_tasks(done)
            
            if not self.shutdown_manager._shutdown_in_progress:
                logger.info("\n⚠️  Инициируется shutdown из-за завершения задачи...")
                await self.shutdown_manager.shutdown(
                    self.http_server,
                    task_manager,
                    self.component_manager
                )
        
        except asyncio.CancelledError:
            logger.info("\n⏹️  [INFO] Задачи отменены")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  [STOP] Получен Ctrl+C")
            await self.shutdown_manager.shutdown(
                self.http_server,
                task_manager,
                self.component_manager
            )
        
        except Exception as e:
            logger.error(f"\n❌ [FATAL] Критическая ошибка в main loop:")
            logger.exception(e)
            self.statistics.increment_errors()
        
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Финальная очистка"""
        await self.shutdown_manager.cleanup()
        self._print_final_statistics()
    
    def _print_startup_banner(self):
        """Выводит startup banner"""
        has_news = self.component_manager.news_processor is not None
        has_whale = self.component_manager.whale_scheduler is not None
        has_trading = self.component_manager.has_trading()
        has_bot = self.component_manager.bot_application is not None
        
        reporter = StatisticsReporter(self.statistics)
        reporter.print_startup_banner(
            has_news=has_news,
            has_whale=has_whale,
            has_trading=has_trading,
            has_bot=has_bot,
            max_memory_mb=self.resource_monitor.max_memory_mb,
            health_check_interval=self.health_monitor.check_interval,
            gc_interval=self.resource_monitor.gc_interval,
            solana_delay=self.rate_limiter.chain_delays.get('solana', 0)
        )
    
    def _print_final_statistics(self):
        """Выводит финальную статистику"""
        reporter = StatisticsReporter(self.statistics)
        reporter.print_final_statistics(
            health_stats=self.health_monitor.get_stats(),
            rate_stats=self.rate_limiter.get_stats(),
            resource_stats=self.resource_monitor.get_stats()
        )