# core/application.py
"""
Main Application Module v4.0
Главный модуль приложения с упрощенной архитектурой

Этот модуль является главной точкой входа для всего приложения.
Вся сложная логика вынесена в подмодули для лучшей организации.

Архитектура:
- application.py - главный класс и точка входа
- application/validators.py - валидация готовности
- application/task_starter.py - запуск фоновых задач
- application/lifecycle.py - управление жизненным циклом
"""

import sys
import logging
import asyncio
from typing import Optional, Any

# Импорт модулей инициализации
from .initialization import (
    validate_environment,
    initialize_database,
    initialize_monitor
)

# Импорт компонентов системы
from .shutdown import ShutdownManager
from .tasks.manager import TaskManager
from .health_server import HealthServer

# Импорт lifecycle менеджера
from .app_lifecycle.lifecycle import ApplicationLifecycle

logger = logging.getLogger(__name__)


class Application:
    """
    Главный класс приложения - CryptoCompass Monitoring System
    
    Responsibilities:
    - Управление жизненным циклом приложения
    - Координация между компонентами
    - Обработка критических ошибок
    - Graceful shutdown
    
    Архитектура v4.0:
    - Модульная структура с разделением ответственности
    - Упрощенный главный класс (только координация)
    - Вся логика в подмодулях application/*
    - Исправлены все ошибки вызовов API
    
    Компоненты:
    - Config: конфигурация приложения
    - DatabaseManager: управление БД
    - Monitor: мониторинг системы и компонентов
    - ShutdownManager: graceful shutdown
    - TaskManager: управление фоновыми задачами
    - HealthServer: HTTP health check endpoint
    - ApplicationLifecycle: управление жизненным циклом
    """
    
    def __init__(self):
        """
        Инициализация контейнера приложения
        
        Создает пустой контейнер для всех компонентов.
        Реальная инициализация происходит в _initialize_components()
        """
        # Конфигурация
        self.config: Optional[Any] = None
        
        # Основные компоненты
        self.db_manager: Optional[Any] = None
        self.monitor: Optional[Any] = None
        
        # Менеджеры
        self.shutdown_manager: Optional[ShutdownManager] = None
        self.task_manager: Optional[TaskManager] = None
        self.health_server: Optional[HealthServer] = None
        
        # Lifecycle менеджер
        self.lifecycle: Optional[ApplicationLifecycle] = None
        
        logger.debug("Application container created")
    
    def run(self):
        """
        Главная точка входа для запуска приложения (синхронная)
        
        Этот метод вызывается из main() и запускает асинхронное
        приложение через asyncio.run()
        
        Обрабатывает:
        - KeyboardInterrupt (Ctrl+C)
        - Критические ошибки
        - Корректный exit code
        
        Exit codes:
        - 0: нормальное завершение
        - 1: критическая ошибка
        """
        logger.info("="*80)
        logger.info("🚀 CRYPTO COMPASS v4.2.0")
        logger.info("   Integrated Cryptocurrency Monitoring System")
        logger.info("="*80)
        
        try:
            # Запуск асинхронного приложения
            asyncio.run(self.async_run())
            
            # Нормальное завершение
            logger.info("Application exited normally")
            sys.exit(0)
            
        except KeyboardInterrupt:
            logger.info("⚠️  Received keyboard interrupt (Ctrl+C)")
            logger.info("Application stopped by user")
            sys.exit(0)
            
        except Exception as e:
            logger.error("="*80)
            logger.error("❌ CRITICAL ERROR IN APPLICATION")
            logger.error("="*80)
            logger.error(f"Error: {e}", exc_info=True)
            logger.error("="*80)
            sys.exit(1)
    
    async def async_run(self):
        """
        Асинхронный запуск приложения
        
        Основной метод работы приложения:
        1. Инициализация всех компонентов
        2. Создание lifecycle менеджера
        3. Запуск и работа до получения сигнала остановки
        4. Graceful shutdown
        
        Весь lifecycle управляется через ApplicationLifecycle,
        что упрощает этот метод и делает его более читаемым.
        
        Raises:
            Exception: Любая критическая ошибка приводит к остановке
        """
        try:
            # Шаг 1: Инициализация всех компонентов системы
            await self._initialize_components()
            
            # Шаг 2: Создание lifecycle менеджера
            self._create_lifecycle_manager()
            
            # Шаг 3: Запуск и работа приложения
            await self.lifecycle.run_until_stopped()
            
        except asyncio.CancelledError:
            logger.info("⚠️  Application task cancelled")
            raise
            
        except Exception as e:
            logger.error("❌ Critical error in async_run", exc_info=True)
            raise
    
    async def _initialize_components(self):
        """
        Инициализация всех компонентов приложения
        
        Критически важный метод! Следует строгой последовательности:
        1. Environment validation (конфигурация)
        2. Database initialization
        3. Monitor initialization (загрузка компонентов)
        4. Shutdown manager creation
        5. Task manager creation
        6. Health server creation
        
        Порядок важен, так как каждый компонент может зависеть от предыдущих.
        
        Raises:
            RuntimeError: Если инициализация любого компонента не удалась
        """
        logger.info("")
        logger.info("="*80)
        logger.info("📋 COMPONENTS INITIALIZATION SEQUENCE")
        logger.info("="*80)
        logger.info("")
        
        try:
            # ========== Step 1: Environment Validation ==========
            logger.info("Step 1/6: Environment validation")
            logger.info("-" * 80)
            
            self.config = validate_environment()
            
            if not self.config:
                raise RuntimeError("Configuration validation failed")
            
            logger.info("✅ Environment validated successfully")
            logger.info("")
            
            # ========== Step 2: Database Initialization ==========
            logger.info("Step 2/6: Database initialization")
            logger.info("-" * 80)
            
            self.db_manager = await initialize_database()
            
            if not self.db_manager:
                raise RuntimeError("Database initialization failed")
            
            logger.info("✅ Database initialized successfully")
            logger.info("")
            
            # ========== Step 3: Monitor Initialization ==========
            logger.info("Step 3/6: Monitor initialization")
            logger.info("-" * 80)
            
            self.monitor = await initialize_monitor(self.config, self.db_manager)
            
            if not self.monitor:
                raise RuntimeError("Monitor initialization failed")
            
            logger.info("✅ Monitor initialized successfully")
            logger.info("")
            
            # ========== Step 4: Shutdown Manager ==========
            logger.info("Step 4/6: Shutdown manager initialization")
            logger.info("-" * 80)
            
            self.shutdown_manager = ShutdownManager(
                monitor=self.monitor,
                db_manager=self.db_manager
            )
            
            if not self.shutdown_manager:
                raise RuntimeError("Shutdown manager creation failed")
            
            logger.info("✅ Shutdown manager created successfully")
            logger.info("")
            
            # ========== Step 5: Task Manager ==========
            logger.info("Step 5/6: Task manager initialization")
            logger.info("-" * 80)
            
            self.task_manager = TaskManager(
                config=self.config,
                monitor=self.monitor
            )
            
            if not self.task_manager:
                raise RuntimeError("Task manager creation failed")
            
            logger.info("✅ Task manager created successfully")
            logger.info("")
            
            # ========== Step 6: Health Server ==========
            logger.info("Step 6/6: Health server initialization")
            logger.info("-" * 80)
            
            self.health_server = HealthServer(
                monitor=self.monitor,
                config=self.config
            )
            
            if not self.health_server:
                raise RuntimeError("Health server creation failed")
            
            logger.info("✅ Health server created successfully")
            logger.info("")
            
            # ========== Initialization Complete ==========
            logger.info("="*80)
            logger.info("✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY")
            logger.info("="*80)
            logger.info("")
            
        except Exception as e:
            logger.error("="*80)
            logger.error("❌ COMPONENT INITIALIZATION FAILED")
            logger.error("="*80)
            logger.error(f"Error during initialization: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize components: {e}") from e
    
    def _create_lifecycle_manager(self):
        """
        Создание lifecycle менеджера
        
        Lifecycle менеджер объединяет все компоненты и управляет
        полным жизненным циклом приложения:
        - Валидация готовности к запуску
        - Запуск фоновых задач
        - Мониторинг работы
        - Graceful shutdown
        
        Этот метод должен вызываться ПОСЛЕ _initialize_components()
        
        Raises:
            RuntimeError: Если не все компоненты инициализированы
        """
        logger.info("Creating application lifecycle manager...")
        
        # Проверка что все компоненты созданы
        required_components = {
            'config': self.config,
            'monitor': self.monitor,
            'db_manager': self.db_manager,
            'shutdown_manager': self.shutdown_manager,
            'task_manager': self.task_manager,
            'health_server': self.health_server
        }
        
        missing_components = [
            name for name, component in required_components.items()
            if component is None
        ]
        
        if missing_components:
            error_msg = f"Cannot create lifecycle manager: missing components: {missing_components}"
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
        # Создание lifecycle менеджера
        try:
            self.lifecycle = ApplicationLifecycle(
                config=self.config,
                monitor=self.monitor,
                db_manager=self.db_manager,
                shutdown_manager=self.shutdown_manager,
                task_manager=self.task_manager,
                health_server=self.health_server
            )
            
            logger.info("✅ Lifecycle manager created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create lifecycle manager: {e}", exc_info=True)
            raise RuntimeError(f"Lifecycle manager creation failed: {e}") from e
    
    def get_status(self) -> dict:
        """
        Получение текущего статуса приложения
        
        Полезно для:
        - Мониторинга состояния
        - Health checks
        - Дебаггинга
        - Метрик
        
        Returns:
            dict: Полный статус всех компонентов
            
        Example:
            >>> app = Application()
            >>> status = app.get_status()
            >>> print(status['running'])
            True
        """
        if self.lifecycle:
            return self.lifecycle.get_status()
        
        return {
            'running': False,
            'initialized': False,
            'error': 'Application not started'
        }
    
    def __repr__(self) -> str:
        """
        Строковое представление приложения
        
        Returns:
            str: Описание состояния приложения
        """
        status = "running" if (self.lifecycle and self.lifecycle.is_running) else "stopped"
        return f"Application(status={status})"


def main():
    """
    Главная точка входа для запуска приложения
    
    Эта функция вызывается из main.py и является единственной
    точкой входа в приложение.
    
    Создает экземпляр Application и запускает его.
    Все ошибки обрабатываются внутри Application.run()
    """
    logger.info("Starting CryptoCompass application...")
    
    try:
        app = Application()
        app.run()
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


# Точка входа при запуске модуля напрямую
if __name__ == "__main__":
    main()


__all__ = ['Application', 'main']