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

ИСПРАВЛЕНО v4.6:
- Lazy import ComponentManager для разрыва циклических зависимостей
- Улучшенная архитектура инициализации
- Proper error handling во всех методах
- Comprehensive logging
"""

import asyncio
import logging
import os
from typing import Optional, Any

# ИСПРАВЛЕНО: Убран импорт ComponentManager с уровня модуля
# from core.components import ComponentManager  ← УДАЛЕНО!

from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor
from core.http_server import HTTPServer
from core.bot_patcher import BotHandlerPatcher
from core.statistics import SystemStatistics, StatisticsReporter
from core.tasks import TaskManager

logger = logging.getLogger(__name__)


class IntegratedCryptoMonitor:
    """
    Production-ready интегрированная система мониторинга криптовалют v4.6
    
    ИСПРАВЛЕНИЯ v4.6:
    - Lazy import ComponentManager для предотвращения циклических зависимостей
    - Улучшенная архитектура с разделением инициализации на этапы
    - Comprehensive error handling
    - Better resource management
    
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
        http_server: HTTP сервер для health checks
        task_manager: Управление фоновыми задачами
        shutdown_event: Event для координации остановки
        running: Флаг работы системы
        _component_manager: Lazy-loaded manager компонентов
    """
    
    def __init__(self):
        """
        Инициализация integrated crypto monitor
        
        КРИТИЧЕСКИ ВАЖНО: ComponentManager не импортируется на уровне модуля,
        а создается лениво при первом обращении через property.
        Это предотвращает циклические зависимости.
        """
        logger.info("\n" + "=" * 80)
        logger.info("🚀 INITIALIZING INTEGRATED CRYPTO MONITOR v4.6")
        logger.info("=" * 80 + "\n")
        
        # ИСПРАВЛЕНО: ComponentManager будет создан лениво
        self._component_manager: Optional[Any] = None
        
        try:
            self._initialize_core_components()
            self._initialize_business_components()
            self._initialize_http_server()
            self._connect_rate_limiter()
            self._patch_bot_handlers()
            self._initialize_state()
            
            logger.info("\n✅ Integrated Crypto Monitor v4.6 инициализирован")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitor: {e}", exc_info=True)
            raise
    
    @property
    def component_manager(self):
        """
        Ленивая загрузка ComponentManager
        
        Импортирует и создает ComponentManager только при первом обращении.
        Это критически важно для разрыва циклических зависимостей между
        core.monitor и core.components.
        
        Returns:
            ComponentManager instance
        """
        if self._component_manager is None:
            # ИСПРАВЛЕНО: Импорт только когда нужен
            logger.debug("Lazy-loading ComponentManager...")
            
            try:
                from core.components import ComponentManager
                self._component_manager = ComponentManager()
                logger.debug("✅ ComponentManager lazy-loaded successfully")
            
            except Exception as e:
                logger.error(f"❌ Failed to lazy-load ComponentManager: {e}", exc_info=True)
                raise
        
        return self._component_manager
    
    def _initialize_core_components(self) -> None:
        """
        Инициализация core компонентов системы
        
        Создает базовые компоненты для мониторинга и управления ресурсами.
        Эти компоненты не имеют внешних зависимостей и безопасны для
        раннего создания.
        
        Raises:
            Exception: При критических ошибках инициализации
        """
        logger.debug("Initializing core components...")
        
        try:
            # Rate limiter для управления API запросами
            self.rate_limiter = ChainRateLimiter()
            logger.debug("   ✓ ChainRateLimiter created")
            
            # Resource monitor для отслеживания использования памяти/CPU
            max_memory = int(os.getenv('MAX_MEMORY_MB', '450'))
            self.resource_monitor = ResourceMonitor(max_memory_mb=max_memory)
            logger.debug(f"   ✓ ResourceMonitor created (max_memory={max_memory}MB)")
            
            # Health monitor для проверки состояния системы
            self.health_monitor = SystemHealthMonitor()
            logger.debug("   ✓ SystemHealthMonitor created")
            
            # Statistics для сбора метрик
            self.statistics = SystemStatistics()
            logger.debug("   ✓ SystemStatistics created")
            
            logger.debug("✅ Core components initialized")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize core components: {e}", exc_info=True)
            raise
    
    def _initialize_business_components(self) -> None:
        """
        Инициализация бизнес-компонентов
        
        ИСПРАВЛЕНО: Использует lazy property component_manager для загрузки
        компонентов. Это предотвращает циклические зависимости при импорте.
        
        Загружает компоненты для:
        - News processing (RSS feeds + AI analysis)
        - Whale tracking (blockchain monitoring)
        - Trading system (signal generation)
        - Telegram bot (user interface)
        
        Raises:
            Exception: При критических ошибках загрузки компонентов
        """
        logger.debug("Loading business components...")
        
        try:
            # ИСПРАВЛЕНО: Используем property для lazy loading
            self.component_manager.load_all()
            
            # Логируем статус загруженных компонентов
            status = self.component_manager.get_status_dict()
            active_count = status.get('total_active', 0)
            
            logger.debug(f"✅ Business components loaded ({active_count} active)")
        
        except Exception as e:
            logger.error(f"❌ Failed to load business components: {e}", exc_info=True)
            # Не raise - система может работать с частично загруженными компонентами
            logger.warning("⚠️ Continuing with partial component initialization")
    
    def _initialize_http_server(self) -> None:
        """
        Инициализация HTTP сервера
        
        Создает HTTP сервер для:
        - Health checks (readiness/liveness probes)
        - Metrics endpoint
        - Bot webhook (optional)
        
        HTTP сервер критически важен для production deployment и должен
        быть инициализирован даже если бизнес-компоненты не загружены.
        
        Raises:
            Exception: При критических ошибках создания сервера
        """
        logger.debug("Initializing HTTP server...")
        
        try:
            # Получаем bot application если доступен
            bot_app = None
            try:
                bot_app = self.component_manager.bot_application
            except Exception as e:
                logger.debug(f"Bot application not available: {e}")
            
            # Создаем HTTP сервер
            self.http_server = HTTPServer(
                health_monitor=self.health_monitor,
                resource_monitor=self.resource_monitor,
                rate_limiter=self.rate_limiter,
                bot_application=bot_app
            )
            
            logger.debug("✅ HTTP server initialized")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize HTTP server: {e}", exc_info=True)
            raise
    
    def _connect_rate_limiter(self) -> None:
        """
        Подключение rate limiter к whale scheduler
        
        Интегрирует rate limiter с whale monitoring для управления
        частотой запросов к blockchain APIs. Это критически важно для
        предотвращения rate limiting со стороны API providers.
        
        Whale scheduler может быть не загружен, поэтому обрабатываем
        все возможные ошибки gracefully.
        """
        try:
            whale_scheduler = self.component_manager.whale_scheduler
            
            if whale_scheduler and hasattr(whale_scheduler, 'set_rate_limiter'):
                whale_scheduler.set_rate_limiter(self.rate_limiter)
                logger.info("✅ Rate Limiter v2.1 подключен к Whale Scheduler")
            else:
                logger.debug("ℹ️ Whale Scheduler not available for rate limiter connection")
        
        except Exception as e:
            logger.debug(f"Could not connect rate limiter to whale scheduler: {e}")
    
    def _patch_bot_handlers(self) -> None:
        """
        Патчинг обработчиков Telegram бота
        
        Добавляет мониторинг и статистику к bot handlers для:
        - Tracking обработанных команд
        - Error monitoring
        - Performance metrics
        
        Bot может быть не загружен, поэтому обрабатываем gracefully.
        """
        try:
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
        
        except Exception as e:
            logger.debug(f"Could not patch bot handlers: {e}")
    
    def _initialize_state(self) -> None:
        """
        Инициализация состояния системы
        
        Создает events и флаги для управления жизненным циклом:
        - shutdown_event: Координирует graceful shutdown
        - running: Флаг активности системы
        - task_manager: Будет создан при запуске
        
        Raises:
            Exception: При критических ошибках инициализации состояния
        """
        logger.debug("Initializing system state...")
        
        try:
            # Event для координации shutdown
            self.shutdown_event = asyncio.Event()
            
            # Флаг работы системы
            self.running = False
            
            # Task manager будет создан в run()
            self.task_manager: Optional[TaskManager] = None
            
            logger.debug("✅ System state initialized")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize system state: {e}", exc_info=True)
            raise
    
    async def run(self) -> None:
        """
        Главный цикл выполнения монитора
        
        Последовательность запуска:
        1. Вывод startup banner
        2. Запуск HTTP сервера (для health checks)
        3. Создание и запуск task manager (координатор задач)
        4. Ожидание completion или shutdown signal
        5. Cleanup
        
        Обрабатывает все возможные исключения:
        - CancelledError: Graceful cancellation
        - KeyboardInterrupt: Manual stop
        - Exception: Unexpected errors
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
        """
        Запуск HTTP сервера
        
        HTTP сервер предоставляет endpoints для:
        - /health: Health check
        - /metrics: Prometheus metrics (optional)
        - /webhook: Telegram webhook (optional)
        
        Raises:
            Exception: При критических ошибках запуска
        """
        try:
            logger.info("Starting HTTP server...")
            await self.http_server.start()
            logger.info("✅ HTTP server started")
        
        except Exception as e:
            logger.error(f"❌ Failed to start HTTP server: {e}", exc_info=True)
            # HTTP сервер критичен для production, re-raise
            raise
    
    async def _start_task_manager(self) -> None:
        """
        Создание и запуск task manager
        
        Task manager координирует выполнение:
        - News processing task
        - Whale monitoring task
        - Trading system task
        - Bot commands task
        - Health monitoring task
        - Coordinator task
        
        Raises:
            Exception: При критических ошибках запуска задач
        """
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
        
        Мониторит выполнение всех задач и реагирует на:
        - Успешное завершение задачи
        - Ошибку в задаче (crash)
        - Внешний shutdown signal
        
        При завершении любой критической задачи инициирует
        graceful shutdown всей системы.
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
        
        Последовательность остановки:
        1. Установка shutdown event
        2. Остановка task manager (отмена задач)
        3. Остановка HTTP сервера
        4. Остановка компонентов (news, whale, trading, bot)
        
        Каждый шаг обрабатывается gracefully с proper error handling.
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
                try:
                    await self.task_manager.stop_all_tasks()
                    logger.info("✅ Task manager stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping task manager: {e}", exc_info=True)
            
            # Останавливаем HTTP сервер
            if self.http_server:
                logger.info("Stopping HTTP server...")
                try:
                    await self.http_server.stop()
                    logger.info("✅ HTTP server stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping HTTP server: {e}", exc_info=True)
            
            # Останавливаем компоненты
            if self._component_manager:
                logger.info("Stopping components...")
                try:
                    await self._component_manager.stop_all()
                    logger.info("✅ Components stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping components: {e}", exc_info=True)
            
            logger.info("="*80)
            logger.info("✅ Monitor stopped successfully")
            logger.info("="*80)
        
        except Exception as e:
            logger.error(f"❌ Error during monitor stop: {e}", exc_info=True)
    
    async def _cleanup(self) -> None:
        """
        Финальная очистка ресурсов
        
        Выполняет окончательную очистку:
        - Вывод финальной статистики
        - Освобождение ресурсов компонентов
        - Garbage collection
        
        Все ошибки обрабатываются gracefully.
        """
        logger.info("Performing final cleanup...")
        
        try:
            # Выводим финальную статистику
            self._print_final_statistics()
            
            # Очищаем ресурсы компонентов
            if self._component_manager:
                try:
                    await self._component_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error during component cleanup: {e}", exc_info=True)
            
            logger.info("✅ Cleanup completed")
        
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
    
    def _print_startup_banner(self) -> None:
        """
        Вывод startup banner с информацией о системе
        
        Показывает:
        - Статус всех компонентов
        - Конфигурация ресурсов
        - Health check settings
        - Rate limiting settings
        """
        try:
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
        
        except Exception as e:
            logger.error(f"❌ Error printing startup banner: {e}", exc_info=True)
    
    def _print_final_statistics(self) -> None:
        """
        Вывод финальной статистики работы системы
        
        Показывает собранные метрики:
        - Uptime
        - Обработанные события
        - Ошибки
        - Использование ресурсов
        - Rate limiting статистика
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
            Словарь с информацией о состоянии всех компонентов:
            - running: Флаг работы системы
            - shutdown_requested: Флаг запроса на остановку
            - components: Статус бизнес-компонентов
            - http_server: Статус HTTP сервера
            - resources: Использование ресурсов
            - health: Health check статус
            - rate_limiting: Rate limiting статистика
        """
        try:
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
        
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}", exc_info=True)
            return {
                'running': self.running,
                'error': str(e)
            }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"IntegratedCryptoMonitor("
            f"v4.6, "
            f"running={self.running}, "
            f"shutdown_requested={self.shutdown_event.is_set()}"
            f")"
        )


__all__ = ['IntegratedCryptoMonitor']