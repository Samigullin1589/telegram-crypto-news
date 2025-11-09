# core/monitor.py
"""
Integrated Crypto Monitor
Главная система мониторинга криптовалют

Координирует:
- Загрузку и управление компонентами
- Мониторинг ресурсов и здоровья системы
- Rate limiting для API запросов
- HTTP сервер для health checks
- Graceful shutdown
"""

import asyncio
import logging
import os
import signal
from typing import Optional

from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer
from core.components import ComponentManager
from core.bot_patcher import BotHandlerPatcher
from core.statistics import SystemStatistics, StatisticsReporter
from core.tasks import TaskManager

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
    
    Attributes:
        rate_limiter: Управление rate limiting для API
        resource_monitor: Мониторинг использования ресурсов
        health_monitor: Мониторинг здоровья системы
        statistics: Сбор статистики работы
        component_manager: Управление бизнес-компонентами
        http_server: HTTP сервер для health checks
        task_manager: Управление фоновыми задачами
        shutdown_event: Event для координации остановки
        running: Флаг работы системы
    """
    
    def __init__(self):
        """Инициализация integrated crypto monitor"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.5")
        logger.info("=" * 80 + "\n")
        
        # ИСПРАВЛЕНО: Убрана инициализация ShutdownManager
        # Shutdown управляется на уровне Application, не Monitor
        
        self._initialize_core_components()
        self._initialize_business_components()
        self._initialize_http_server()
        self._connect_rate_limiter()
        self._patch_bot_handlers()
        self._initialize_state()
        
        logger.info("\n✅ Integrated Crypto Monitor v4.5 инициализирован")
    
    def _initialize_core_components(self) -> None:
        """
        Инициализация core компонентов системы
        
        Создает базовые компоненты для мониторинга и управления ресурсами
        """
        logger.debug("Initializing core components...")
        
        # Rate limiter для управления API запросами
        self.rate_limiter = ChainRateLimiter()
        
        # Resource monitor для отслеживания использования памяти/CPU
        max_memory = int(os.getenv('MAX_MEMORY_MB', '450'))
        self.resource_monitor = ResourceMonitor(max_memory_mb=max_memory)
        
        # Health monitor для проверки состояния системы
        self.health_monitor = SystemHealthMonitor()
        
        # Statistics для сбора метрик
        self.statistics = SystemStatistics()
        
        logger.debug("✅ Core components initialized")
    
    def _initialize_business_components(self) -> None:
        """
        Инициализация бизнес-компонентов
        
        Загружает компоненты для новостей, whale tracking, trading и bot
        """
        logger.debug("Loading business components...")
        
        self.component_manager = ComponentManager()
        self.component_manager.load_all()
        
        logger.debug("✅ Business components loaded")
    
    def _initialize_http_server(self) -> None:
        """
        Инициализация HTTP сервера
        
        Создает HTTP сервер для health checks и метрик
        """
        logger.debug("Initializing HTTP server...")
        
        self.http_server = HTTPServer(
            health_monitor=self.health_monitor,
            resource_monitor=self.resource_monitor,
            rate_limiter=self.rate_limiter,
            bot_application=self.component_manager.bot_application
        )
        
        logger.debug("✅ HTTP server initialized")
    
    def _connect_rate_limiter(self) -> None:
        """
        Подключение rate limiter к whale scheduler
        
        Интегрирует rate limiter с whale monitoring для управления
        частотой запросов к blockchain APIs
        """
        whale_scheduler = self.component_manager.whale_scheduler
        
        if whale_scheduler and hasattr(whale_scheduler, 'set_rate_limiter'):
            whale_scheduler.set_rate_limiter(self.rate_limiter)
            logger.info("✅ Rate Limiter v2.1 подключен к Whale Scheduler")
        else:
            logger.debug("ℹ️ Whale Scheduler not available for rate limiter connection")
    
    def _patch_bot_handlers(self) -> None:
        """
        Патчинг обработчиков Telegram бота
        
        Добавляет мониторинг и статистику к bot handlers
        """
        bot_app = self.component_manager.bot_application
        
        if bot_app:
            logger.debug("Patching bot handlers...")
            
            patcher = BotHandlerPatcher(self.health_monitor, self.statistics)
            
            if patcher.patch_handlers(bot_app):
                logger.info("✅ Bot handlers патчинг успешен")
            else:
                logger.warning("⚠️ Bot handlers патчинг не удался")
        else:
            logger.debug("ℹ️ Bot application not available for patching")
    
    def _initialize_state(self) -> None:
        """
        Инициализация состояния системы
        
        Создает events и флаги для управления жизненным циклом
        """
        logger.debug("Initializing system state...")
        
        # Event для координации shutdown
        self.shutdown_event = asyncio.Event()
        
        # Флаг работы системы
        self.running = False
        
        # Task manager будет создан в run()
        self.task_manager: Optional[TaskManager] = None
        
        logger.debug("✅ System state initialized")
    
    async def run(self) -> None:
        """
        Главный цикл выполнения монитора
        
        Запускает все компоненты и координирует их работу до получения
        сигнала на остановку.
        """
        self._print_startup_banner()
        self.running = True
        
        try:
            # Запускаем HTTP сервер
            await self._start_http_server()
            
            # Создаем и запускаем task manager
            await self._start_task_manager()
            
            # Ожидаем completion или shutdown signal
            await self._wait_for_completion()
        
        except asyncio.CancelledError:
            logger.info("\n⏹️ Monitor tasks cancelled")
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ Received KeyboardInterrupt")
        
        except Exception as e:
            logger.error(f"\n❌ Critical error in monitor main loop: {e}", exc_info=True)
            self.statistics.increment_errors()
        
        finally:
            self.running = False
            await self._cleanup()
    
    async def _start_http_server(self) -> None:
        """Запуск HTTP сервера"""
        try:
            await self.http_server.start()
            logger.info("✅ HTTP server started")
        except Exception as e:
            logger.error(f"❌ Failed to start HTTP server: {e}", exc_info=True)
    
    async def _start_task_manager(self) -> None:
        """Создание и запуск task manager"""
        try:
            logger.info("Starting task manager...")
            
            self.task_manager = TaskManager(
                components=self.component_manager,
                health_monitor=self.health_monitor,
                resource_monitor=self.resource_monitor,
                statistics=self.statistics,
                shutdown_event=self.shutdown_event
            )
            
            await self.task_manager.start_all_tasks()
            
            logger.info("✅ All tasks started")
        
        except Exception as e:
            logger.error(f"❌ Failed to start tasks: {e}", exc_info=True)
            raise
    
    async def _wait_for_completion(self) -> None:
        """
        Ожидание completion задач или shutdown signal
        
        Мониторит выполнение задач и реагирует на их завершение
        """
        if not self.task_manager:
            logger.warning("⚠️ Task manager not initialized, cannot wait for completion")
            # Просто ждем shutdown event
            await self.shutdown_event.wait()
            return
        
        try:
            logger.info("Waiting for task completion or shutdown signal...")
            
            # Ожидаем completion задач
            done = await self.task_manager.wait_for_completion()
            
            # Обрабатываем завершенные задачи
            if done:
                self.task_manager.handle_completed_tasks(done)
                logger.info("ℹ️ Some tasks completed, initiating shutdown...")
                self.shutdown_event.set()
        
        except Exception as e:
            logger.error(f"❌ Error waiting for completion: {e}", exc_info=True)
            self.shutdown_event.set()
    
    async def stop(self) -> None:
        """
        Graceful остановка монитора
        
        Останавливает все компоненты в правильном порядке:
        1. Устанавливает shutdown event
        2. Останавливает task manager
        3. Останавливает HTTP сервер
        4. Останавливает компоненты
        """
        logger.info("="*80)
        logger.info("🛑 Stopping Integrated Crypto Monitor...")
        logger.info("="*80)
        
        try:
            # Устанавливаем shutdown event
            self.shutdown_event.set()
            
            # Останавливаем task manager
            if self.task_manager:
                logger.info("Stopping task manager...")
                await self.task_manager.stop_all_tasks()
                logger.info("✅ Task manager stopped")
            
            # Останавливаем HTTP сервер
            if self.http_server:
                logger.info("Stopping HTTP server...")
                await self.http_server.stop()
                logger.info("✅ HTTP server stopped")
            
            # Останавливаем компоненты
            if self.component_manager:
                logger.info("Stopping components...")
                await self.component_manager.stop_all()
                logger.info("✅ Components stopped")
            
            logger.info("="*80)
            logger.info("✅ Monitor stopped successfully")
            logger.info("="*80)
        
        except Exception as e:
            logger.error(f"❌ Error during monitor stop: {e}", exc_info=True)
    
    async def _cleanup(self) -> None:
        """
        Финальная очистка ресурсов
        
        Выполняет окончательную очистку и вывод статистики
        """
        logger.info("Performing final cleanup...")
        
        try:
            # Выводим финальную статистику
            self._print_final_statistics()
            
            # Очищаем ресурсы компонентов
            if self.component_manager:
                await self.component_manager.cleanup()
            
            logger.info("✅ Cleanup completed")
        
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
    
    def _print_startup_banner(self) -> None:
        """
        Вывод startup banner с информацией о системе
        
        Показывает статус всех компонентов и конфигурацию
        """
        # Проверяем наличие компонентов
        has_news = self.component_manager.news_processor is not None
        has_whale = self.component_manager.whale_scheduler is not None
        has_trading = self.component_manager.has_trading()
        has_bot = self.component_manager.bot_application is not None
        
        # Создаем reporter для вывода
        reporter = StatisticsReporter(self.statistics)
        
        # Выводим banner
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
    
    def _print_final_statistics(self) -> None:
        """
        Вывод финальной статистики работы системы
        
        Показывает собранные метрики за время работы
        """
        logger.info("="*80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*80)
        
        try:
            reporter = StatisticsReporter(self.statistics)
            
            # Собираем статистику от всех компонентов
            health_stats = self.health_monitor.get_stats()
            rate_stats = self.rate_limiter.get_stats()
            resource_stats = self.resource_monitor.get_stats()
            
            # Выводим финальную статистику
            reporter.print_final_statistics(
                health_stats=health_stats,
                rate_stats=rate_stats,
                resource_stats=resource_stats
            )
        
        except Exception as e:
            logger.error(f"❌ Error printing final statistics: {e}", exc_info=True)
        
        logger.info("="*80)
    
    def get_status(self) -> dict:
        """
        Получение текущего статуса монитора
        
        Returns:
            Словарь с информацией о состоянии всех компонентов
        """
        return {
            'running': self.running,
            'shutdown_requested': self.shutdown_event.is_set(),
            'components': {
                'news': self.component_manager.news_processor is not None,
                'whale': self.component_manager.whale_scheduler is not None,
                'trading': self.component_manager.has_trading(),
                'bot': self.component_manager.bot_application is not None
            },
            'http_server': {
                'running': self.http_server.is_running() if hasattr(self.http_server, 'is_running') else None
            },
            'resources': self.resource_monitor.get_stats(),
            'health': self.health_monitor.get_stats(),
            'rate_limiting': self.rate_limiter.get_stats()
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"IntegratedCryptoMonitor("
            f"running={self.running}, "
            f"shutdown_requested={self.shutdown_event.is_set()}"
            f")"
        )