# core/application.py
"""
Main Application Module v5.1
Интеграция с IntegratedCryptoMonitor v5.0

ИСПРАВЛЕНО v5.1:
- Убран отдельный TaskManager (используется monitor.infrastructure.task_manager)
- Упрощенная инициализация
- Правильная интеграция с Monitor v5.0
"""

import sys
import logging
import asyncio
from typing import Optional, Any, Dict

from .initialization import (
    validate_environment,
    initialize_database,
    initialize_monitor
)

from .shutdown import ShutdownManager
from .health_server import HealthServer
from .app_lifecycle.lifecycle import ApplicationLifecycle

logger = logging.getLogger(__name__)


class ApplicationComponents:
    """Контейнер компонентов приложения"""
    
    def __init__(self):
        self.config: Optional[Any] = None
        self.db_manager: Optional[Any] = None
        self.monitor: Optional[Any] = None
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.health_server: Optional[HealthServer] = None
        self.lifecycle: Optional[ApplicationLifecycle] = None
    
    def is_fully_initialized(self) -> bool:
        """Проверка полной инициализации"""
        return all([
            self.config is not None,
            self.db_manager is not None,
            self.monitor is not None,
            self.shutdown_manager is not None,
            self.health_server is not None
        ])
    
    def get_missing_components(self) -> list:
        """Получить список неинициализированных компонентов"""
        components = {
            'config': self.config,
            'db_manager': self.db_manager,
            'monitor': self.monitor,
            'shutdown_manager': self.shutdown_manager,
            'health_server': self.health_server
        }
        return [name for name, comp in components.items() if comp is None]


class ComponentInitializer:
    """Инициализатор компонентов"""
    
    def __init__(self, components: ApplicationComponents):
        self.components = components
        self._step = 0
        self._total = 5
    
    async def initialize_all(self) -> bool:
        """Инициализация всех компонентов"""
        self._print_header()
        
        try:
            if not await self._init_environment():
                return False
            if not await self._init_database():
                return False
            if not await self._init_monitor():
                return False
            if not await self._init_shutdown_manager():
                return False
            if not await self._init_health_server():
                return False
            
            self._print_success()
            return True
        except Exception as e:
            self._print_failure(e)
            return False
    
    async def _init_environment(self) -> bool:
        """Step 1: Environment"""
        self._step = 1
        self._print_step("Environment validation")
        try:
            self.components.config = validate_environment()
            if not self.components.config:
                logger.error("❌ Config validation failed")
                return False
            logger.info("✅ Environment validated")
            logger.info("")
            return True
        except Exception as e:
            logger.error(f"❌ Environment error: {e}", exc_info=True)
            return False
    
    async def _init_database(self) -> bool:
        """Step 2: Database"""
        self._step = 2
        self._print_step("Database initialization")
        try:
            self.components.db_manager = await initialize_database()
            if not self.components.db_manager:
                logger.error("❌ Database init failed")
                return False
            logger.info("✅ Database initialized")
            logger.info("")
            return True
        except Exception as e:
            logger.error(f"❌ Database error: {e}", exc_info=True)
            return False
    
    async def _init_monitor(self) -> bool:
        """Step 3: Monitor"""
        self._step = 3
        self._print_step("Monitor initialization")
        try:
            self.components.monitor = await initialize_monitor(
                self.components.config,
                self.components.db_manager
            )
            if not self.components.monitor:
                logger.error("❌ Monitor init failed")
                return False
            logger.info("✅ Monitor initialized")
            logger.info("")
            return True
        except Exception as e:
            logger.error(f"❌ Monitor error: {e}", exc_info=True)
            return False
    
    async def _init_shutdown_manager(self) -> bool:
        """
        Step 4: Shutdown manager

        ИСПРАВЛЕНО: ShutdownManager требует task_manager, db_initializer, monitor
        Получаем task_manager из monitor.infrastructure
        """
        self._step = 4
        self._print_step("Shutdown manager")
        try:
            # ИСПРАВЛЕНО: Получаем task_manager из monitor
            task_manager = getattr(self.components.monitor, 'task_manager', None)
            if not task_manager:
                # Fallback: используем task_manager из infrastructure
                task_manager = getattr(
                    getattr(self.components.monitor, 'infrastructure', None),
                    'task_manager',
                    None
                )

            if not task_manager:
                logger.warning("⚠️ TaskManager not found, creating new TaskManager")
                # ИСПРАВЛЕНО v2: TaskManager требует (config, monitor)
                from core.tasks.manager import TaskManager
                task_manager = TaskManager(
                    config=self.components.config,
                    monitor=self.components.monitor
                )

            # ИСПРАВЛЕНО: Используем db_manager как db_initializer (duck typing)
            self.components.shutdown_manager = ShutdownManager(
                task_manager=task_manager,
                db_initializer=self.components.db_manager,  # db_manager работает как initializer
                monitor=self.components.monitor
            )
            logger.info("✅ Shutdown manager created")
            logger.info("")
            return True
        except Exception as e:
            logger.error(f"❌ Shutdown manager error: {e}", exc_info=True)
            return False
    
    async def _init_health_server(self) -> bool:
        """Step 5: Health server"""
        self._step = 5
        self._print_step("Health server")
        try:
            self.components.health_server = HealthServer(
                monitor=self.components.monitor,
                config=self.components.config
            )
            logger.info("✅ Health server created")
            logger.info("")
            return True
        except Exception as e:
            logger.error(f"❌ Health server error: {e}", exc_info=True)
            return False
    
    def _print_header(self):
        logger.info("")
        logger.info("="*80)
        logger.info("📋 COMPONENTS INITIALIZATION SEQUENCE")
        logger.info("="*80)
        logger.info("")
    
    def _print_step(self, name: str):
        logger.info(f"Step {self._step}/{self._total}: {name}")
        logger.info("-" * 80)
    
    def _print_success(self):
        logger.info("="*80)
        logger.info("✅ ALL COMPONENTS INITIALIZED")
        logger.info("="*80)
        logger.info("")
    
    def _print_failure(self, error: Exception):
        logger.error("="*80)
        logger.error("❌ INITIALIZATION FAILED")
        logger.error("="*80)
        logger.error(f"Error: {error}", exc_info=True)


class Application:
    """
    Главный класс приложения v5.1
    
    ИСПРАВЛЕНО v5.1:
    - Убран дублирующий TaskManager
    - Monitor полностью управляет задачами
    - Упрощенная архитектура
    """
    
    VERSION = "5.1.0"
    
    def __init__(self):
        self.components = ApplicationComponents()
        logger.debug("Application container created")
    
    def run(self) -> None:
        """Главная точка входа"""
        self._print_header()
        
        try:
            asyncio.run(self.async_run())
            logger.info("Application exited normally")
            sys.exit(0)
        except KeyboardInterrupt:
            logger.info("⚠️ Keyboard interrupt")
            sys.exit(0)
        except Exception as e:
            self._print_critical_error(e)
            sys.exit(1)
    
    async def async_run(self) -> None:
        """Асинхронный запуск"""
        try:
            if not await self._initialize_components():
                raise RuntimeError("Component initialization failed")
            
            self._create_lifecycle_manager()
            
            await self.components.lifecycle.run_until_stopped()
        except asyncio.CancelledError:
            logger.info("⚠️ Cancelled")
            raise
        except Exception as e:
            logger.error("❌ Critical error", exc_info=True)
            raise
    
    async def _initialize_components(self) -> bool:
        """Инициализация компонентов"""
        initializer = ComponentInitializer(self.components)
        success = await initializer.initialize_all()
        
        if not success:
            missing = self.components.get_missing_components()
            logger.error(f"❌ Missing: {missing}")
            return False
        
        return True
    
    def _create_lifecycle_manager(self) -> None:
        """Создание lifecycle manager"""
        logger.info("Creating lifecycle manager...")
        
        if not self.components.is_fully_initialized():
            missing = self.components.get_missing_components()
            raise RuntimeError(f"Missing components: {missing}")
        
        try:
            self.components.lifecycle = ApplicationLifecycle(
                config=self.components.config,
                monitor=self.components.monitor,
                db_manager=self.components.db_manager,
                shutdown_manager=self.components.shutdown_manager,
                health_server=self.components.health_server
            )
            logger.info("✅ Lifecycle manager created")
        except Exception as e:
            logger.error(f"❌ Lifecycle creation failed: {e}", exc_info=True)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус"""
        if self.components.lifecycle:
            return self.components.lifecycle.get_status()
        return {
            'version': self.VERSION,
            'running': False,
            'error': 'Not started'
        }
    
    def _print_header(self):
        logger.info("="*80)
        logger.info(f"🚀 CRYPTO COMPASS v{self.VERSION}")
        logger.info("="*80)
    
    def _print_critical_error(self, error: Exception):
        logger.error("="*80)
        logger.error("❌ CRITICAL ERROR")
        logger.error("="*80)
        logger.error(f"Error: {error}", exc_info=True)
        logger.error("="*80)
    
    def __repr__(self) -> str:
        status = "running" if (
            self.components.lifecycle and 
            self.components.lifecycle.is_running
        ) else "stopped"
        return f"Application(v{self.VERSION}, {status})"


def main() -> None:
    """Точка входа"""
    logger.info("Starting application...")
    try:
        app = Application()
        app.run()
    except Exception as e:
        logger.critical(f"Failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = ['Application', 'main']