# core/initialization/monitor.py
"""
Monitor Initializer
Инициализация системы мониторинга

Выполняет:
- Создание и настройку IntegratedCryptoMonitor
- Проверку зависимостей
- Подготовку к запуску мониторинга
"""

from typing import Optional, TYPE_CHECKING
from core.logging_config import get_logger

# ИСПРАВЛЕНО: TYPE_CHECKING для избежания циклического импорта
if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor

logger = get_logger(__name__)


class MonitorInitializer:
    """
    Инициализатор системы мониторинга
    
    Отвечает за корректное создание и настройку IntegratedCryptoMonitor,
    проверку всех необходимых зависимостей и подготовку к работе.
    
    Attributes:
        monitor: Инстанс IntegratedCryptoMonitor после инициализации
    """
    
    def __init__(self):
        """Инициализация monitor initializer"""
        self.monitor: Optional['IntegratedCryptoMonitor'] = None
        self._initialized: bool = False
    
    def initialize(self) -> bool:
        """
        Инициализация системы мониторинга
        
        Выполняет полный цикл инициализации:
        1. Проверка зависимостей
        2. Создание IntegratedCryptoMonitor
        3. Настройка компонентов
        4. Валидация готовности
        
        Returns:
            True если инициализация успешна
        """
        if self._initialized:
            logger.debug("Monitor already initialized")
            return True
        
        try:
            logger.info("Starting monitor initialization...")
            
            # ИСПРАВЛЕНО: Lazy import для избежания циклического импорта
            from core.monitor import IntegratedCryptoMonitor
            
            # Проверка зависимостей
            if not self._check_dependencies():
                return False
            
            # Создание монитора
            logger.debug("Creating IntegratedCryptoMonitor instance...")
            self.monitor = IntegratedCryptoMonitor()
            
            if self.monitor is None:
                logger.error("❌ Failed to create IntegratedCryptoMonitor instance")
                return False
            
            logger.debug("✅ IntegratedCryptoMonitor instance created")
            
            # Валидация готовности
            if not self._validate_monitor():
                return False
            
            self._initialized = True
            logger.info("✅ Monitor initialized successfully")
            
            return True
        
        except ImportError as e:
            logger.error(
                f"❌ Failed to import IntegratedCryptoMonitor: {e}",
                exc_info=True
            )
            return False
        
        except Exception as e:
            logger.error(
                f"❌ Monitor initialization failed: {e}",
                exc_info=True
            )
            return False
    
    def _check_dependencies(self) -> bool:
        """
        Проверка необходимых зависимостей
        
        Проверяет наличие всех компонентов, необходимых для работы монитора
        
        Returns:
            True если все зависимости доступны
        """
        try:
            logger.debug("Checking monitor dependencies...")
            
            # Проверяем импорт конфигурации
            try:
                from app.config import config
                if config is None:
                    logger.error("❌ Config is not available")
                    return False
                logger.debug("✅ Config available")
            except ImportError as e:
                logger.error(f"❌ Failed to import config: {e}")
                return False
            
            # Проверяем доступность необходимых модулей
            required_modules = [
                'core.monitor',
                'core.logging_config',
                'app.config'
            ]
            
            for module_name in required_modules:
                try:
                    __import__(module_name)
                    logger.debug(f"✅ Module available: {module_name}")
                except ImportError as e:
                    logger.error(f"❌ Required module not available: {module_name} - {e}")
                    return False
            
            logger.info("✅ All monitor dependencies checked")
            return True
        
        except Exception as e:
            logger.error(
                f"❌ Dependency check failed: {e}",
                exc_info=True
            )
            return False
    
    def _validate_monitor(self) -> bool:
        """
        Валидация созданного монитора
        
        Проверяет что монитор корректно создан и готов к работе
        
        Returns:
            True если монитор валиден
        """
        try:
            if self.monitor is None:
                logger.error("❌ Monitor is None")
                return False
            
            logger.debug("Validating monitor instance...")
            
            # ИСПРАВЛЕНО: Проверяем наличие методов 'run' и 'stop'
            # IntegratedCryptoMonitor использует 'run', а не 'start'
            required_attrs = ['run', 'stop']
            
            for attr in required_attrs:
                if not hasattr(self.monitor, attr):
                    logger.error(f"❌ Monitor missing required attribute: {attr}")
                    return False
                logger.debug(f"✅ Monitor has attribute: {attr}")
            
            # Проверяем что методы callable
            for attr in required_attrs:
                if not callable(getattr(self.monitor, attr)):
                    logger.error(f"❌ Monitor attribute not callable: {attr}")
                    return False
                logger.debug(f"✅ Monitor attribute callable: {attr}")
            
            logger.info("✅ Monitor validation passed")
            return True
        
        except Exception as e:
            logger.error(
                f"❌ Monitor validation failed: {e}",
                exc_info=True
            )
            return False
    
    def get_monitor(self) -> Optional['IntegratedCryptoMonitor']:
        """
        Получение инициализированного монитора
        
        Returns:
            IntegratedCryptoMonitor или None если не инициализирован
        """
        return self.monitor
    
    def is_initialized(self) -> bool:
        """
        Проверка состояния инициализации
        
        Returns:
            True если инициализация завершена успешно
        """
        return self._initialized
    
    def get_status(self) -> dict:
        """
        Получение статуса инициализатора
        
        Returns:
            Словарь с информацией о состоянии
        """
        return {
            'initialized': self._initialized,
            'has_monitor': self.monitor is not None,
            'monitor_type': type(self.monitor).__name__ if self.monitor else None
        }
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown монитора
        
        Корректно останавливает и освобождает ресурсы монитора
        """
        if not self.monitor:
            logger.debug("No monitor to shutdown")
            return
        
        try:
            logger.info("Shutting down monitor...")
            
            # Проверяем наличие метода stop
            if hasattr(self.monitor, 'stop'):
                # Проверяем является ли метод async
                import asyncio
                if asyncio.iscoroutinefunction(self.monitor.stop):
                    await self.monitor.stop()
                else:
                    self.monitor.stop()
            
            self._initialized = False
            self.monitor = None
            
            logger.info("✅ Monitor shut down successfully")
        
        except Exception as e:
            logger.error(f"❌ Monitor shutdown error: {e}", exc_info=True)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"MonitorInitializer("
            f"initialized={self._initialized}, "
            f"has_monitor={self.monitor is not None}"
            f")"
        )