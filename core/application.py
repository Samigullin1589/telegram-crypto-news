# core/application.py
"""
Main Application Module v5.0
Главный модуль приложения с интеграцией Monitor v5.0

Этот модуль является главной точкой входа для всего приложения.
Интегрирован с IntegratedCryptoMonitor v5.0 с двухэтапной инициализацией.

Архитектура v5.0:
------------------
- Синхронизация с Monitor v5.0 (двухэтапная инициализация)
- Правильная последовательность инициализации компонентов
- Production-grade error handling
- Полное разделение ответственности

Компоненты:
-----------
- Config: Конфигурация приложения
- DatabaseManager: Управление БД
- IntegratedCryptoMonitor v5.0: Система мониторинга
- ShutdownManager: Graceful shutdown
- HealthServer: Health check endpoint
- ApplicationLifecycle: Управление жизненным циклом
"""

import sys
import logging
import asyncio
from typing import Optional, Any, Dict

# Импорт модулей инициализации
from .initialization import (
    validate_environment,
    initialize_database,
    initialize_monitor
)

# Импорт компонентов системы
from .shutdown import ShutdownManager
from .health_server import HealthServer

# Импорт lifecycle менеджера
from .app_lifecycle.lifecycle import ApplicationLifecycle

logger = logging.getLogger(__name__)


class ApplicationComponents:
    """
    Контейнер для компонентов приложения
    
    Централизованное хранение всех компонентов для:
    - Упрощенного доступа
    - Валидации готовности
    - Получения статуса
    
    Attributes:
        config: Конфигурация приложения
        db_manager: Database manager
        monitor: IntegratedCryptoMonitor v5.0
        shutdown_manager: Менеджер graceful shutdown
        health_server: HTTP health check сервер
        lifecycle: Lifecycle менеджер
    """
    
    def __init__(self):
        """Инициализация пустого контейнера"""
        self.config: Optional[Any] = None
        self.db_manager: Optional[Any] = None
        self.monitor: Optional[Any] = None
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.health_server: Optional[HealthServer] = None
        self.lifecycle: Optional[ApplicationLifecycle] = None
    
    def is_fully_initialized(self) -> bool:
        """
        Проверка полной инициализации всех компонентов
        
        Returns:
            bool: True если все компоненты инициализированы
        """
        return all([
            self.config is not None,
            self.db_manager is not None,
            self.monitor is not None,
            self.shutdown_manager is not None,
            self.health_server is not None
        ])
    
    def get_missing_components(self) -> list:
        """
        Получить список неинициализированных компонентов
        
        Returns:
            list: Имена компонентов которые не инициализированы
        """
        components = {
            'config': self.config,
            'db_manager': self.db_manager,
            'monitor': self.monitor,
            'shutdown_manager': self.shutdown_manager,
            'health_server': self.health_server
        }
        
        return [name for name, component in components.items() if component is None]
    
    def get_status_dict(self) -> Dict[str, Any]:
        """
        Получить статус всех компонентов
        
        Returns:
            dict: Статус каждого компонента
        """
        return {
            'config': self.config is not None,
            'db_manager': self.db_manager is not None,
            'monitor': self.monitor is not None,
            'shutdown_manager': self.shutdown_manager is not None,
            'health_server': self.health_server is not None,
            'lifecycle': self.lifecycle is not None
        }


class ComponentInitializer:
    """
    Инициализатор компонентов приложения
    
    Отвечает за последовательную инициализацию всех компонентов
    с proper error handling и логированием.
    
    Последовательность инициализации:
    1. Environment validation (config)
    2. Database initialization
    3. Monitor creation (v5.0 - только __init__)
    4. Monitor async initialization
    5. Shutdown manager
    6. Health server
    """
    
    def __init__(self, components: ApplicationComponents):
        """
        Инициализация initializer
        
        Args:
            components: Контейнер компонентов для заполнения
        """
        self.components = components
        self._initialization_step = 0
        self._total_steps = 6
    
    async def initialize_all(self) -> bool:
        """
        Инициализация всех компонентов
        
        Returns:
            bool: True если все компоненты успешно инициализированы
        """
        self._print_initialization_header()
        
        try:
            # Step 1: Environment validation
            if not await self._initialize_environment():
                return False
            
            # Step 2: Database initialization
            if not await self._initialize_database():
                return False
            
            # Step 3: Monitor creation
            if not await self._initialize_monitor():
                return False
            
            # Step 4: Monitor async initialization
            if not await self._initialize_monitor_async():
                return False
            
            # Step 5: Shutdown manager
            if not await self._initialize_shutdown_manager():
                return False
            
            # Step 6: Health server
            if not await self._initialize_health_server():
                return False
            
            self._print_initialization_success()
            return True
        
        except Exception as e:
            self._print_initialization_failure(e)
            return False
    
    async def _initialize_environment(self) -> bool:
        """
        Step 1: Валидация окружения и загрузка конфигурации
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 1
        self._print_step_header("Environment validation")
        
        try:
            self.components.config = validate_environment()
            
            if not self.components.config:
                logger.error("❌ Configuration validation failed")
                return False
            
            logger.info("✅ Environment validated successfully")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Environment validation failed: {e}", exc_info=True)
            return False
    
    async def _initialize_database(self) -> bool:
        """
        Step 2: Инициализация базы данных
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 2
        self._print_step_header("Database initialization")
        
        try:
            self.components.db_manager = await initialize_database()
            
            if not self.components.db_manager:
                logger.error("❌ Database initialization failed")
                return False
            
            logger.info("✅ Database initialized successfully")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_monitor(self) -> bool:
        """
        Step 3: Создание IntegratedCryptoMonitor
        
        ВАЖНО: Это только создание объекта (__init__), 
        без async инициализации компонентов.
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 3
        self._print_step_header("Monitor creation")
        
        try:
            # Вызываем функцию из initialization/__init__.py
            # которая создаст MonitorInitializer и вызовет await initialize()
            self.components.monitor = await initialize_monitor(
                self.components.config,
                self.components.db_manager
            )
            
            if not self.components.monitor:
                logger.error("❌ Monitor creation failed")
                return False
            
            logger.info("✅ Monitor created successfully")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Monitor creation failed: {e}", exc_info=True)
            return False
    
    async def _initialize_monitor_async(self) -> bool:
        """
        Step 4: Async инициализация монитора
        
        Вызывает monitor.initialize() для загрузки:
        - Business компонентов (news, whale, trading, bot)
        - HTTP server
        - Rate limiter connections
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 4
        self._print_step_header("Monitor async initialization")
        
        try:
            # Monitor уже создан и инициализирован через initialize_monitor()
            # который внутри вызывает MonitorInitializer.initialize()
            # Проверяем что монитор полностью готов
            
            if not hasattr(self.components.monitor, 'get_status'):
                logger.error("❌ Monitor missing get_status method")
                return False
            
            # Получаем статус монитора
            status = self.components.monitor.get_status()
            
            if not status.get('fully_initialized', False):
                logger.error("❌ Monitor not fully initialized")
                logger.error(f"Monitor status: {status}")
                return False
            
            logger.info("✅ Monitor fully initialized")
            logger.info(f"   Active components: {status.get('components', {})}")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Monitor async initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_shutdown_manager(self) -> bool:
        """
        Step 5: Создание shutdown manager
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 5
        self._print_step_header("Shutdown manager initialization")
        
        try:
            self.components.shutdown_manager = ShutdownManager(
                monitor=self.components.monitor,
                db_manager=self.components.db_manager
            )
            
            if not self.components.shutdown_manager:
                logger.error("❌ Shutdown manager creation failed")
                return False
            
            logger.info("✅ Shutdown manager created successfully")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Shutdown manager creation failed: {e}", exc_info=True)
            return False
    
    async def _initialize_health_server(self) -> bool:
        """
        Step 6: Создание health server
        
        Returns:
            bool: True если успешно
        """
        self._initialization_step = 6
        self._print_step_header("Health server initialization")
        
        try:
            self.components.health_server = HealthServer(
                monitor=self.components.monitor,
                config=self.components.config
            )
            
            if not self.components.health_server:
                logger.error("❌ Health server creation failed")
                return False
            
            logger.info("✅ Health server created successfully")
            logger.info("")
            return True
        
        except Exception as e:
            logger.error(f"❌ Health server creation failed: {e}", exc_info=True)
            return False
    
    def _print_initialization_header(self) -> None:
        """Вывод заголовка инициализации"""
        logger.info("")
        logger.info("="*80)
        logger.info("📋 COMPONENTS INITIALIZATION SEQUENCE")
        logger.info("="*80)
        logger.info("")
    
    def _print_step_header(self, step_name: str) -> None:
        """Вывод заголовка шага"""
        logger.info(f"Step {self._initialization_step}/{self._total_steps}: {step_name}")
        logger.info("-" * 80)
    
    def _print_initialization_success(self) -> None:
        """Вывод сообщения об успешной инициализации"""
        logger.info("="*80)
        logger.info("✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY")
        logger.info("="*80)
        logger.info("")
    
    def _print_initialization_failure(self, error: Exception) -> None:
        """Вывод сообщения об ошибке инициализации"""
        logger.error("="*80)
        logger.error("❌ COMPONENT INITIALIZATION FAILED")
        logger.error("="*80)
        logger.error(f"Error: {error}", exc_info=True)


class Application:
    """
    Главный класс приложения - CryptoCompass Monitoring System v5.0
    
    Интегрирован с IntegratedCryptoMonitor v5.0 с двухэтапной инициализацией.
    
    Responsibilities:
    -----------------
    - Управление жизненным циклом приложения
    - Координация между компонентами
    - Обработка критических ошибок
    - Graceful shutdown
    
    Архитектура v5.0:
    -----------------
    - Синхронизация с Monitor v5.0
    - Модульная структура с четким разделением
    - Production-grade error handling
    - Comprehensive logging
    
    Компоненты:
    -----------
    - Config: Конфигурация приложения
    - DatabaseManager: Управление БД
    - IntegratedCryptoMonitor v5.0: Система мониторинга
    - ShutdownManager: Graceful shutdown
    - HealthServer: HTTP health check endpoint
    - ApplicationLifecycle: Управление жизненным циклом
    """
    
    VERSION = "5.0.0"
    
    def __init__(self):
        """
        Инициализация контейнера приложения
        
        Создает контейнер для компонентов.
        Реальная инициализация в _initialize_components().
        """
        self.components = ApplicationComponents()
        logger.debug("Application container created")
    
    def run(self) -> None:
        """
        Главная точка входа для запуска приложения (синхронная)
        
        Запускает асинхронное приложение через asyncio.run()
        
        Exit codes:
        - 0: нормальное завершение
        - 1: критическая ошибка
        """
        self._print_application_header()
        
        try:
            asyncio.run(self.async_run())
            
            logger.info("Application exited normally")
            sys.exit(0)
        
        except KeyboardInterrupt:
            logger.info("⚠️  Received keyboard interrupt (Ctrl+C)")
            logger.info("Application stopped by user")
            sys.exit(0)
        
        except Exception as e:
            self._print_critical_error(e)
            sys.exit(1)
    
    async def async_run(self) -> None:
        """
        Асинхронный запуск приложения
        
        Последовательность:
        1. Инициализация компонентов
        2. Создание lifecycle менеджера
        3. Запуск приложения
        4. Graceful shutdown
        """
        try:
            # Инициализация компонентов
            if not await self._initialize_components():
                raise RuntimeError("Component initialization failed")
            
            # Создание lifecycle менеджера
            self._create_lifecycle_manager()
            
            # Запуск приложения
            await self.components.lifecycle.run_until_stopped()
        
        except asyncio.CancelledError:
            logger.info("⚠️  Application task cancelled")
            raise
        
        except Exception as e:
            logger.error("❌ Critical error in async_run", exc_info=True)
            raise
    
    async def _initialize_components(self) -> bool:
        """
        Инициализация всех компонентов приложения
        
        Использует ComponentInitializer для последовательной
        инициализации с proper error handling.
        
        Returns:
            bool: True если все компоненты инициализированы
        """
        initializer = ComponentInitializer(self.components)
        
        success = await initializer.initialize_all()
        
        if not success:
            missing = self.components.get_missing_components()
            logger.error(f"❌ Initialization failed. Missing components: {missing}")
            return False
        
        return True
    
    def _create_lifecycle_manager(self) -> None:
        """
        Создание lifecycle менеджера
        
        Lifecycle менеджер управляет полным жизненным циклом:
        - Валидация готовности
        - Запуск фоновых задач
        - Мониторинг работы
        - Graceful shutdown
        
        Raises:
            RuntimeError: Если не все компоненты инициализированы
        """
        logger.info("Creating application lifecycle manager...")
        
        if not self.components.is_fully_initialized():
            missing = self.components.get_missing_components()
            error_msg = f"Cannot create lifecycle manager: missing components: {missing}"
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
        try:
            self.components.lifecycle = ApplicationLifecycle(
                config=self.components.config,
                monitor=self.components.monitor,
                db_manager=self.components.db_manager,
                shutdown_manager=self.components.shutdown_manager,
                health_server=self.components.health_server
            )
            
            logger.info("✅ Lifecycle manager created successfully")
        
        except Exception as e:
            logger.error(f"❌ Failed to create lifecycle manager: {e}", exc_info=True)
            raise RuntimeError(f"Lifecycle manager creation failed: {e}") from e
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса приложения
        
        Returns:
            dict: Статус всех компонентов
        """
        if self.components.lifecycle:
            return self.components.lifecycle.get_status()
        
        return {
            'version': self.VERSION,
            'running': False,
            'initialized': False,
            'components': self.components.get_status_dict(),
            'error': 'Application not started'
        }
    
    def _print_application_header(self) -> None:
        """Вывод заголовка приложения"""
        logger.info("="*80)
        logger.info(f"🚀 CRYPTO COMPASS v{self.VERSION}")
        logger.info("   Integrated Cryptocurrency Monitoring System")
        logger.info("="*80)
    
    def _print_critical_error(self, error: Exception) -> None:
        """Вывод критической ошибки"""
        logger.error("="*80)
        logger.error("❌ CRITICAL ERROR IN APPLICATION")
        logger.error("="*80)
        logger.error(f"Error: {error}", exc_info=True)
        logger.error("="*80)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        status = "running" if (
            self.components.lifecycle and 
            self.components.lifecycle.is_running
        ) else "stopped"
        return f"Application(v{self.VERSION}, status={status})"


def main() -> None:
    """
    Главная точка входа для запуска приложения
    
    Создает и запускает Application.
    Все ошибки обрабатываются внутри Application.run()
    """
    logger.info("Starting CryptoCompass application...")
    
    try:
        app = Application()
        app.run()
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = ['Application', 'main']