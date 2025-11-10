"""
Main Application Module v4.0
Главный модуль приложения с упрощенной архитектурой
"""

import sys
import logging
import asyncio
from typing import Optional

from .initialization import (
    validate_environment,
    initialize_database,
    initialize_monitor
)
from .shutdown import ShutdownManager
from .tasks.manager import TaskManager
from .health_server import HealthServer
from .application import ApplicationLifecycle

logger = logging.getLogger(__name__)


class Application:
    """
    Главный класс приложения
    
    Упрощенный интерфейс для запуска и управления всем приложением.
    Вся сложная логика вынесена в модули application/*
    
    Версия 4.0:
    - Модульная архитектура
    - Разделение ответственности
    - Упрощенный главный класс
    - Исправлена ошибка с TaskManager.start_all()
    """
    
    def __init__(self):
        """Инициализация приложения"""
        self.config: Optional[Any] = None
        self.db_manager: Optional[Any] = None
        self.monitor: Optional[Any] = None
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.task_manager: Optional[TaskManager] = None
        self.health_server: Optional[HealthServer] = None
        self.lifecycle: Optional[ApplicationLifecycle] = None
    
    def run(self):
        """
        Главная точка входа для запуска приложения
        
        Синхронный метод, который запускает асинхронное приложение
        """
        try:
            asyncio.run(self.async_run())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Critical error in application: {e}", exc_info=True)
            sys.exit(1)
    
    async def async_run(self):
        """
        Асинхронный запуск приложения
        
        Весь lifecycle управляется через ApplicationLifecycle
        """
        try:
            # Инициализация компонентов
            await self._initialize_components()
            
            # Создание lifecycle менеджера
            self.lifecycle = ApplicationLifecycle(
                config=self.config,
                monitor=self.monitor,
                db_manager=self.db_manager,
                shutdown_manager=self.shutdown_manager,
                task_manager=self.task_manager,
                health_server=self.health_server
            )
            
            # Запуск и работа до остановки
            await self.lifecycle.run_until_stopped()
            
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        except Exception as e:
            logger.error(f"❌ Critical error in async_run: {e}", exc_info=True)
            raise
    
    async def _initialize_components(self):
        """
        Инициализация всех компонентов приложения
        
        Следует строгой последовательности инициализации:
        1. Environment validation
        2. Database
        3. Monitor
        4. Shutdown manager
        5. Task manager
        6. Health server
        """
        logger.info("="*80)
        logger.info("📋 INITIALIZATION SEQUENCE")
        logger.info("="*80)
        
        # Step 1: Environment
        logger.info("Step 1/6: Environment validation")
        self.config = validate_environment()
        logger.info("✅ Environment validated")
        
        # Step 2: Database
        logger.info("Step 2/6: Database initialization")
        self.db_manager = await initialize_database()
        logger.info("✅ Database initialized")
        
        # Step 3: Monitor
        logger.info("Step 3/6: Monitor initialization")
        self.monitor = await initialize_monitor(self.config, self.db_manager)
        logger.info("✅ Monitor initialized")
        
        # Step 4: Shutdown manager
        logger.info("Step 4/6: Shutdown manager initialization")
        self.shutdown_manager = ShutdownManager(
            monitor=self.monitor,
            db_manager=self.db_manager
        )
        logger.info("✅ Shutdown manager created")
        
        # Step 5: Task manager
        logger.info("Step 5/6: Task manager initialization")
        self.task_manager = TaskManager(
            config=self.config,
            monitor=self.monitor
        )
        logger.info("✅ Task manager created")
        
        # Step 6: Health server
        logger.info("Step 6/6: Health server initialization")
        self.health_server = HealthServer(
            monitor=self.monitor,
            config=self.config
        )
        logger.info("✅ Health server created")
        
        logger.info("="*80)
        logger.info("✅ INITIALIZATION COMPLETE")
        logger.info("="*80)


def main():
    """Точка входа для запуска приложения"""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()


__all__ = ['Application', 'main']