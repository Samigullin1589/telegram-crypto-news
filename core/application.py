# core/application.py
"""
Application Core - Главный класс приложения
Управляет жизненным циклом и координацией компонентов
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
from core.tasks.manager import get_task_manager
from app import config, __version__

logger = get_logger(__name__)


class ApplicationState:
    """Состояние приложения"""
    
    def __init__(self):
        """Инициализация состояния"""
        self.initialized: bool = False
        self.running: bool = False
        self.shutdown_requested: bool = False
        self.components: Dict[str, Any] = {}


class Application:
    """
    Главный класс приложения
    
    Отвечает за:
    - Инициализацию всех компонентов
    - Координацию жизненного цикла
    - Graceful shutdown
    - Health checks
    """
    
    def __init__(self):
        """Инициализация приложения"""
        self.state = ApplicationState()
        self.task_manager = get_task_manager()
        self.signal_handler = SignalHandler(self._request_shutdown)
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.health_server: Optional[HealthCheckServer] = None
        
        logger.info("=" * 80)
        logger.info(f"🚀 CRYPTO MONITOR v{__version__}")
        logger.info("=" * 80)
    
    def run(self) -> None:
        """
        Синхронная точка входа
        Создает event loop и запускает async_run
        """
        try:
            asyncio.run(self.async_run())
        
        except KeyboardInterrupt:
            logger.info("⏹️ Interrupted by user")
        
        except Exception as e:
            logger.error(f"❌ Critical error: {e}", exc_info=True)
            sys.exit(1)
    
    async def async_run(self) -> None:
        """Асинхронный main loop"""
        try:
            # Установка signal handlers
            self.signal_handler.setup()
            
            # Инициализация
            if not await self._initialize_application():
                logger.error("❌ Initialization failed")
                sys.exit(1)
            
            # Запуск health check server
            await self._start_health_server()
            
            # Запуск задач
            await self._start_tasks()
            
            # Главный loop
            await self._main_loop()
        
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        
        except Exception as e:
            logger.error(f"❌ Critical error in async_run: {e}", exc_info=True)
            raise
        
        finally:
            # Graceful shutdown
            await self._shutdown()
    
    async def _initialize_application(self) -> bool:
        """
        Полная инициализация приложения
        
        Returns:
            bool: True если успешно
        """
        logger.info("=" * 80)
        logger.info("📋 INITIALIZATION")
        logger.info("=" * 80)
        
        try:
            # Шаг 1: Валидация окружения
            logger.info("Step 1/4: Environment validation")
            env_initializer = EnvironmentInitializer()
            if not env_initializer.validate():
                return False
            self.state.components['environment'] = env_initializer
            
            # Шаг 2: Инициализация БД
            logger.info("Step 2/4: Database initialization")
            db_initializer = DatabaseInitializer()
            if not await db_initializer.initialize():
                return False
            self.state.components['database'] = db_initializer
            
            # Шаг 3: Инициализация мониторинга
            logger.info("Step 3/4: Monitor initialization")
            monitor_initializer = MonitorInitializer()
            if not monitor_initializer.initialize():
                return False
            self.state.components['monitor'] = monitor_initializer
            
            # Шаг 4: Создание shutdown manager
            logger.info("Step 4/4: Shutdown manager")
            self.shutdown_manager = ShutdownManager(
                task_manager=self.task_manager,
                db_initializer=db_initializer,
                monitor=monitor_initializer.monitor
            )
            
            self.state.initialized = True
            logger.info("=" * 80)
            logger.info("✅ INITIALIZATION COMPLETE")
            logger.info("=" * 80)
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}", exc_info=True)
            return False
    
    async def _start_health_server(self) -> None:
        """Запуск health check server для Render"""
        try:
            self.health_server = HealthCheckServer(
                port=int(config.get('HEALTH_CHECK_PORT', 8080))
            )
            await self.health_server.start()
            logger.info("✅ Health check server started")
        
        except Exception as e:
            logger.warning(f"Cannot start health server: {e}")
    
    async def _start_tasks(self) -> None:
        """Запуск всех задач мониторинга"""
        logger.info("=" * 80)
        logger.info("🎯 STARTING TASKS")
        logger.info("=" * 80)
        
        task_results = await self.task_manager.start_all(
            enable_database_optimization=True,
            enable_news_monitoring=config.is_feature_enabled('news'),
            enable_whale_tracking=config.is_feature_enabled('whale'),
            enable_trading_signals=config.is_feature_enabled('trading')
        )
        
        # Вывод статуса задач
        for task_name, result in task_results.items():
            status = result.get('status', 'unknown')
            emoji = '✅' if status == 'started' else '❌'
            logger.info(f"  {emoji} {task_name}: {status}")
        
        self.state.running = True
        
        logger.info("=" * 80)
        logger.info("✅ ALL TASKS STARTED")
        logger.info("=" * 80)
    
    async def _main_loop(self) -> None:
        """
        Главный event loop
        Ожидает до получения сигнала shutdown
        """
        logger.info("🚀 Application running. Press Ctrl+C to stop")
        
        try:
            # Запускаем мониторинг
            monitor_initializer = self.state.components.get('monitor')
            if monitor_initializer and monitor_initializer.monitor:
                await monitor_initializer.monitor.run()
            else:
                # Если мониторинга нет - просто ждем
                while not self.state.shutdown_requested:
                    await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
            raise
    
    def _request_shutdown(self) -> None:
        """
        Запрос shutdown (вызывается signal handler)
        Устанавливает флаг для graceful остановки
        """
        if not self.state.shutdown_requested:
            self.state.shutdown_requested = True
            logger.info("⏹️ Shutdown requested")
    
    async def _shutdown(self) -> None:
        """Graceful shutdown всех компонентов"""
        if not self.shutdown_manager:
            return
        
        logger.info("=" * 80)
        logger.info("⏹️ GRACEFUL SHUTDOWN")
        logger.info("=" * 80)
        
        try:
            await self.shutdown_manager.shutdown()
            
            # Останавливаем health server
            if self.health_server:
                await self.health_server.stop()
            
            logger.info("=" * 80)
            logger.info("✅ SHUTDOWN COMPLETE")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)