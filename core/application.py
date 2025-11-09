# core/application.py
"""
Application Core
Главный класс приложения

Управляет:
- Жизненным циклом приложения
- Координацией всех компонентов
- Инициализацией и shutdown
- Health checks и мониторингом
"""

import sys
import asyncio
import signal
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from core.logging_config import get_logger
from core.signal_handlers import SignalHandler
from core.initialization import (
    EnvironmentInitializer,
    DatabaseInitializer,
    MonitorInitializer
)
from core.shutdown import ShutdownManager
from core.health_server import HealthCheckServer
from core.tasks.manager import TaskManager
from app import config, __version__

logger = get_logger(__name__)


class ApplicationState:
    """
    Состояние приложения
    
    Отслеживает текущее состояние жизненного цикла приложения
    и хранит ссылки на ключевые компоненты.
    
    Attributes:
        initialized: Флаг успешной инициализации
        running: Флаг активного состояния
        shutdown_requested: Флаг запроса на остановку
        components: Словарь инициализированных компонентов
    """
    
    def __init__(self):
        """Инициализация состояния приложения"""
        self.initialized: bool = False
        self.running: bool = False
        self.shutdown_requested: bool = False
        self.components: Dict[str, Any] = {}
        self.startup_time: Optional[float] = None
        self.shutdown_time: Optional[float] = None
    
    def mark_initialized(self) -> None:
        """Отметить приложение как инициализированное"""
        self.initialized = True
        import time
        self.startup_time = time.time()
    
    def mark_running(self) -> None:
        """Отметить приложение как запущенное"""
        self.running = True
    
    def mark_shutdown(self) -> None:
        """Отметить начало shutdown"""
        self.shutdown_requested = True
        import time
        self.shutdown_time = time.time()
    
    def get_uptime(self) -> Optional[float]:
        """
        Получить время работы приложения
        
        Returns:
            Время в секундах или None если не запущено
        """
        if not self.startup_time:
            return None
        
        import time
        end_time = self.shutdown_time or time.time()
        return end_time - self.startup_time


class Application:
    """
    Главный класс приложения
    
    Координирует весь жизненный цикл приложения от инициализации
    до graceful shutdown. Управляет всеми основными компонентами
    и обеспечивает их корректное взаимодействие.
    
    Компоненты:
    - EnvironmentInitializer: Валидация окружения
    - DatabaseInitializer: Инициализация БД
    - MonitorInitializer: Инициализация мониторинга
    - TaskManager: Управление фоновыми задачами
    - ShutdownManager: Graceful остановка
    - HealthCheckServer: Health checks для Render
    - SignalHandler: Обработка системных сигналов
    
    Attributes:
        state: Текущее состояние приложения
        task_manager: Менеджер фоновых задач
        signal_handler: Обработчик системных сигналов
        shutdown_manager: Менеджер graceful shutdown
        health_server: Сервер health checks
    """
    
    def __init__(self):
        """Инициализация главного класса приложения"""
        # Состояние приложения
        self.state = ApplicationState()
        
        # ИСПРАВЛЕНО: Создаем TaskManager напрямую, без get_task_manager()
        self.task_manager = TaskManager()
        
        # Signal handler для graceful shutdown
        self.signal_handler = SignalHandler(self._request_shutdown)
        
        # Компоненты, инициализируемые позже
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.health_server: Optional[HealthCheckServer] = None
        
        # Вывод баннера запуска
        self._print_startup_banner()
    
    def _print_startup_banner(self) -> None:
        """Вывод красивого баннера при запуске"""
        logger.info("=" * 80)
        logger.info(f"🚀 CRYPTO COMPASS v{__version__}")
        logger.info(f"   Environment: {config.base.ENVIRONMENT}")
        logger.info(f"   Debug Mode: {config.base.DEBUG_MODE}")
        logger.info("=" * 80)
    
    def run(self) -> None:
        """
        Синхронная точка входа приложения
        
        Создает event loop и запускает асинхронный main.
        Обрабатывает KeyboardInterrupt и критические ошибки.
        """
        try:
            asyncio.run(self.async_run())
        
        except KeyboardInterrupt:
            logger.info("⏹️ Interrupted by user (Ctrl+C)")
        
        except Exception as e:
            logger.error(f"❌ Critical error in application: {e}", exc_info=True)
            sys.exit(1)
    
    async def async_run(self) -> None:
        """
        Асинхронный главный цикл приложения
        
        Выполняет полный жизненный цикл:
        1. Установка signal handlers
        2. Инициализация всех компонентов
        3. Запуск health check сервера
        4. Запуск фоновых задач
        5. Главный event loop
        6. Graceful shutdown при завершении
        """
        try:
            # Шаг 1: Установка signal handlers
            self._setup_signal_handlers()
            
            # Шаг 2: Инициализация приложения
            if not await self._initialize_application():
                logger.error("❌ Application initialization failed")
                sys.exit(1)
            
            # Шаг 3: Запуск health check server
            await self._start_health_server()
            
            # Шаг 4: Запуск фоновых задач
            await self._start_background_tasks()
            
            # Шаг 5: Главный event loop
            await self._run_main_loop()
        
        except asyncio.CancelledError:
            logger.info("ℹ️ Application cancelled")
        
        except Exception as e:
            logger.error(f"❌ Critical error in async_run: {e}", exc_info=True)
            raise
        
        finally:
            # Шаг 6: Graceful shutdown
            await self._perform_shutdown()
    
    def _setup_signal_handlers(self) -> None:
        """Установка обработчиков системных сигналов"""
        try:
            self.signal_handler.setup()
            logger.debug("✅ Signal handlers configured")
        except Exception as e:
            logger.warning(f"⚠️ Cannot setup signal handlers: {e}")
    
    async def _initialize_application(self) -> bool:
        """
        Полная инициализация всех компонентов приложения
        
        Выполняет последовательную инициализацию:
        1. Валидацию окружения
        2. Инициализацию базы данных
        3. Инициализацию системы мониторинга
        4. Создание shutdown manager
        
        Returns:
            True если все компоненты инициализированы успешно
        """
        logger.info("=" * 80)
        logger.info("📋 INITIALIZATION SEQUENCE")
        logger.info("=" * 80)
        
        try:
            # Шаг 1/4: Валидация окружения
            if not await self._initialize_environment():
                return False
            
            # Шаг 2/4: Инициализация БД
            if not await self._initialize_database():
                return False
            
            # Шаг 3/4: Инициализация мониторинга
            if not await self._initialize_monitor():
                return False
            
            # Шаг 4/4: Создание shutdown manager
            if not self._initialize_shutdown_manager():
                return False
            
            self.state.mark_initialized()
            
            logger.info("=" * 80)
            logger.info("✅ INITIALIZATION COMPLETE")
            logger.info("=" * 80)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}", exc_info=True)
            return False
    
    async def _initialize_environment(self) -> bool:
        """
        Инициализация и валидация окружения
        
        Returns:
            True если окружение валидно
        """
        logger.info("Step 1/4: Environment validation")
        
        try:
            env_initializer = EnvironmentInitializer()
            
            if not env_initializer.validate():
                logger.error("❌ Environment validation failed")
                return False
            
            self.state.components['environment'] = env_initializer
            logger.info("✅ Environment validated")
            return True
        
        except Exception as e:
            logger.error(f"❌ Environment initialization error: {e}", exc_info=True)
            return False
    
    async def _initialize_database(self) -> bool:
        """
        Инициализация базы данных
        
        Returns:
            True если БД инициализирована успешно
        """
        logger.info("Step 2/4: Database initialization")
        
        try:
            db_initializer = DatabaseInitializer()
            
            if not await db_initializer.initialize():
                logger.error("❌ Database initialization failed")
                return False
            
            self.state.components['database'] = db_initializer
            logger.info("✅ Database initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}", exc_info=True)
            return False
    
    async def _initialize_monitor(self) -> bool:
        """
        Инициализация системы мониторинга
        
        Returns:
            True если мониторинг инициализирован успешно
        """
        logger.info("Step 3/4: Monitor initialization")
        
        try:
            monitor_initializer = MonitorInitializer()
            
            if not monitor_initializer.initialize():
                logger.error("❌ Monitor initialization failed")
                return False
            
            self.state.components['monitor'] = monitor_initializer
            logger.info("✅ Monitor initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Monitor initialization error: {e}", exc_info=True)
            return False
    
    def _initialize_shutdown_manager(self) -> bool:
        """
        Создание shutdown manager
        
        Returns:
            True если shutdown manager создан успешно
        """
        logger.info("Step 4/4: Shutdown manager initialization")
        
        try:
            db_initializer = self.state.components.get('database')
            monitor_initializer = self.state.components.get('monitor')
            
            if not db_initializer:
                logger.error("❌ Database initializer not found")
                return False
            
            self.shutdown_manager = ShutdownManager(
                task_manager=self.task_manager,
                db_initializer=db_initializer,
                monitor=monitor_initializer.monitor if monitor_initializer else None
            )
            
            logger.info("✅ Shutdown manager created")
            return True
        
        except Exception as e:
            logger.error(f"❌ Shutdown manager initialization error: {e}", exc_info=True)
            return False
    
    async def _start_health_server(self) -> None:
        """
        Запуск health check сервера
        
        Health check сервер необходим для Render.com для мониторинга
        состояния приложения.
        """
        try:
            health_port = int(config.base.PORT)
            
            logger.info(f"Starting health check server on port {health_port}...")
            
            self.health_server = HealthCheckServer(port=health_port)
            await self.health_server.start()
            
            logger.info(f"✅ Health check server started on port {health_port}")
        
        except Exception as e:
            logger.warning(f"⚠️ Cannot start health check server: {e}")
            logger.warning("Application will continue without health checks")
    
    async def _start_background_tasks(self) -> None:
        """
        Запуск всех фоновых задач
        
        Запускает задачи мониторинга в зависимости от конфигурации:
        - Database optimization (всегда включена)
        - News monitoring (если включен модуль news)
        - Whale tracking (если включен модуль whale_alerts)
        - Trading signals (если включен модуль trading)
        """
        logger.info("=" * 80)
        logger.info("🎯 STARTING BACKGROUND TASKS")
        logger.info("=" * 80)
        
        try:
            # Определяем какие модули включены
            enable_news = config.features.is_enabled('news')
            enable_whale = config.features.is_enabled('whale_alerts')
            enable_trading = config.features.is_enabled('trading')
            
            # Запускаем задачи
            task_results = await self.task_manager.start_all(
                enable_database_optimization=True,
                enable_news_monitoring=enable_news,
                enable_whale_tracking=enable_whale,
                enable_trading_signals=enable_trading
            )
            
            # Выводим результаты
            for task_name, result in task_results.items():
                status = result.get('status', 'unknown')
                emoji = '✅' if status == 'started' else '❌'
                logger.info(f"  {emoji} {task_name}: {status}")
                
                if status == 'failed' and 'error' in result:
                    logger.error(f"     Error: {result['error']}")
            
            self.state.mark_running()
            
            logger.info("=" * 80)
            logger.info("✅ ALL BACKGROUND TASKS STARTED")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"❌ Error starting background tasks: {e}", exc_info=True)
            raise
    
    async def _run_main_loop(self) -> None:
        """
        Главный event loop приложения
        
        Запускает систему мониторинга и ожидает до получения
        сигнала shutdown.
        """
        logger.info("=" * 80)
        logger.info("🚀 APPLICATION RUNNING")
        logger.info("=" * 80)
        logger.info("Press Ctrl+C to stop")
        
        try:
            # Получаем monitor initializer
            monitor_initializer = self.state.components.get('monitor')
            
            if monitor_initializer and monitor_initializer.monitor:
                # Если есть монитор - запускаем его
                logger.debug("Starting monitor main loop...")
                await monitor_initializer.monitor.run()
            else:
                # Если монитора нет - просто ждем shutdown сигнала
                logger.warning("⚠️ Monitor not available, entering wait mode")
                
                while not self.state.shutdown_requested:
                    await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("ℹ️ Main loop cancelled")
            raise
        
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}", exc_info=True)
            raise
    
    def _request_shutdown(self) -> None:
        """
        Запрос graceful shutdown
        
        Вызывается signal handler при получении SIGINT/SIGTERM.
        Устанавливает флаг для инициации процесса остановки.
        """
        if not self.state.shutdown_requested:
            self.state.mark_shutdown()
            logger.info("⏹️ Shutdown requested - initiating graceful shutdown")
        else:
            logger.warning("⚠️ Shutdown already requested")
    
    async def _perform_shutdown(self) -> None:
        """
        Выполнение graceful shutdown всех компонентов
        
        Останавливает все компоненты в правильном порядке:
        1. Фоновые задачи
        2. Система мониторинга
        3. База данных
        4. Health check сервер
        """
        if not self.shutdown_manager:
            logger.warning("⚠️ Shutdown manager not initialized, skipping graceful shutdown")
            return
        
        logger.info("=" * 80)
        logger.info("⏹️ GRACEFUL SHUTDOWN")
        logger.info("=" * 80)
        
        try:
            # Выполняем shutdown всех основных компонентов
            success = await self.shutdown_manager.shutdown()
            
            # Останавливаем health check server
            if self.health_server:
                try:
                    await self.health_server.stop()
                    logger.info("✅ Health check server stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping health server: {e}")
            
            # Выводим статистику
            uptime = self.state.get_uptime()
            if uptime:
                logger.info(f"📊 Application uptime: {uptime:.2f} seconds")
            
            logger.info("=" * 80)
            if success:
                logger.info("✅ SHUTDOWN COMPLETE")
            else:
                logger.warning("⚠️ SHUTDOWN COMPLETED WITH ERRORS")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}", exc_info=True)