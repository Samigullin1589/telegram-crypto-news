# core/initialization/monitor.py
"""
Monitor Initializer - Production Ready
=======================================

Инициализация системы мониторинга с полным разделением ответственности.

Components:
-----------
- MonitorConfigValidator: Валидация конфигурации
- MonitorDependencyChecker: Проверка зависимостей
- MonitorFactory: Создание монитора
- MonitorValidator: Валидация монитора
- MonitorInitializer: Координация инициализации

Architecture:
-------------
Обеспечивает:
- Корректное создание и настройку IntegratedCryptoMonitor
- Проверку зависимостей перед инициализацией
- Валидацию конфигурации и параметров
- Graceful shutdown с освобождением ресурсов

Production Ready:
-----------------
- Полная обработка ошибок
- Dependency injection
- Валидация всех компонентов
- Детальное логирование
"""

from typing import Optional, Any, Dict, List, TYPE_CHECKING
from core.logging_config import get_logger

# TYPE_CHECKING для избежания циклического импорта
if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor
    from app.config import Config

logger = get_logger(__name__)


class MonitorConfigValidator:
    """
    Валидатор конфигурации монитора
    
    Responsibilities:
    -----------------
    - Проверка наличия config объекта
    - Валидация структуры конфигурации
    - Проверка обязательных параметров
    """
    
    def __init__(self):
        """Инициализация валидатора"""
        logger.debug("[MONITOR-CONFIG] ConfigValidator initialized")
    
    def validate(self, config: Any) -> bool:
        """
        Валидация конфигурации
        
        Args:
            config: Объект конфигурации для валидации
            
        Returns:
            bool: True если конфигурация валидна
        """
        try:
            if config is None:
                logger.error("[MONITOR-CONFIG] Config is None")
                return False
            
            logger.debug("[MONITOR-CONFIG] Validating config object...")
            
            # Проверяем что это объект Config
            if not self._is_config_object(config):
                logger.error("[MONITOR-CONFIG] Invalid config type")
                return False
            
            # Проверяем обязательные атрибуты
            if not self._validate_required_attributes(config):
                return False
            
            logger.info("[MONITOR-CONFIG] ✅ Config validation passed")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-CONFIG] ❌ Validation error: {e}", exc_info=True)
            return False
    
    def _is_config_object(self, config: Any) -> bool:
        """
        Проверка что объект является Config
        
        Args:
            config: Объект для проверки
            
        Returns:
            bool: True если объект Config
        """
        # Проверяем наличие основных атрибутов Config
        required_attrs = ['telegram', 'database', 'features']
        
        for attr in required_attrs:
            if not hasattr(config, attr):
                logger.error(f"[MONITOR-CONFIG] Config missing attribute: {attr}")
                return False
        
        logger.debug("[MONITOR-CONFIG] ✅ Config object type valid")
        return True
    
    def _validate_required_attributes(self, config: Any) -> bool:
        """
        Проверка обязательных атрибутов конфигурации
        
        Args:
            config: Объект конфигурации
            
        Returns:
            bool: True если все атрибуты присутствуют
        """
        try:
            # Проверяем telegram config
            if not hasattr(config.telegram, 'bot_token'):
                logger.error("[MONITOR-CONFIG] Missing telegram.bot_token")
                return False
            
            # Проверяем database config
            if not hasattr(config.database, 'database_url'):
                logger.error("[MONITOR-CONFIG] Missing database.database_url")
                return False
            
            logger.debug("[MONITOR-CONFIG] ✅ All required attributes present")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-CONFIG] ❌ Attribute validation error: {e}")
            return False


class MonitorDependencyChecker:
    """
    Проверка зависимостей монитора
    
    Responsibilities:
    -----------------
    - Проверка наличия необходимых модулей
    - Валидация database manager
    - Проверка доступности компонентов
    """
    
    def __init__(self):
        """Инициализация checker"""
        logger.debug("[MONITOR-DEPS] DependencyChecker initialized")
    
    def check_all(self, db_manager: Optional[Any] = None) -> bool:
        """
        Проверка всех зависимостей
        
        Args:
            db_manager: Database manager для проверки (опционально)
            
        Returns:
            bool: True если все зависимости доступны
        """
        try:
            logger.debug("[MONITOR-DEPS] Checking all dependencies...")
            
            # Проверка модулей
            if not self._check_required_modules():
                return False
            
            # Проверка database manager если передан
            if db_manager is not None:
                if not self._validate_db_manager(db_manager):
                    return False
            
            logger.info("[MONITOR-DEPS] ✅ All dependencies available")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-DEPS] ❌ Dependency check error: {e}", exc_info=True)
            return False
    
    def _check_required_modules(self) -> bool:
        """
        Проверка необходимых модулей
        
        Returns:
            bool: True если все модули доступны
        """
        required_modules = [
            'core.monitor',
            'core.logging_config',
            'app.config'
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                logger.debug(f"[MONITOR-DEPS] ✅ Module available: {module_name}")
            except ImportError as e:
                logger.error(f"[MONITOR-DEPS] ❌ Module unavailable: {module_name} - {e}")
                return False
        
        return True
    
    def _validate_db_manager(self, db_manager: Any) -> bool:
        """
        Валидация database manager
        
        Args:
            db_manager: Database manager для проверки
            
        Returns:
            bool: True если db_manager валиден
        """
        if db_manager is None:
            logger.warning("[MONITOR-DEPS] Database manager is None (may be optional)")
            return True
        
        # Проверяем основные методы database manager
        required_methods = ['get_session', 'close']
        
        for method in required_methods:
            if not hasattr(db_manager, method):
                logger.error(f"[MONITOR-DEPS] DB manager missing method: {method}")
                return False
        
        logger.debug("[MONITOR-DEPS] ✅ Database manager valid")
        return True


class MonitorFactory:
    """
    Фабрика для создания монитора
    
    Responsibilities:
    -----------------
    - Создание IntegratedCryptoMonitor
    - Инъекция зависимостей
    - Обработка ошибок создания
    """
    
    def __init__(self, config: Any, db_manager: Optional[Any] = None):
        """
        Инициализация фабрики
        
        Args:
            config: Объект конфигурации
            db_manager: Database manager (опционально)
        """
        self.config = config
        self.db_manager = db_manager
        logger.debug("[MONITOR-FACTORY] Factory initialized")
    
    def create_monitor(self) -> Optional['IntegratedCryptoMonitor']:
        """
        Создание IntegratedCryptoMonitor
        
        Returns:
            IntegratedCryptoMonitor или None при ошибке
        """
        try:
            logger.info("[MONITOR-FACTORY] Creating IntegratedCryptoMonitor...")
            
            # Lazy import для избежания циклического импорта
            from core.monitor import IntegratedCryptoMonitor
            
            # Создаем монитор
            # IntegratedCryptoMonitor не требует аргументов в __init__
            monitor = IntegratedCryptoMonitor()
            
            if monitor is None:
                logger.error("[MONITOR-FACTORY] ❌ Failed to create monitor instance")
                return None
            
            logger.info("[MONITOR-FACTORY] ✅ Monitor instance created successfully")
            return monitor
        
        except ImportError as e:
            logger.error(
                f"[MONITOR-FACTORY] ❌ Failed to import IntegratedCryptoMonitor: {e}",
                exc_info=True
            )
            return None
        
        except Exception as e:
            logger.error(
                f"[MONITOR-FACTORY] ❌ Monitor creation failed: {e}",
                exc_info=True
            )
            return None


class MonitorValidator:
    """
    Валидатор созданного монитора
    
    Responsibilities:
    -----------------
    - Проверка структуры монитора
    - Валидация методов
    - Проверка готовности к работе
    """
    
    def __init__(self):
        """Инициализация валидатора"""
        logger.debug("[MONITOR-VAL] Validator initialized")
    
    def validate(self, monitor: Optional['IntegratedCryptoMonitor']) -> bool:
        """
        Валидация монитора
        
        Args:
            monitor: Монитор для валидации
            
        Returns:
            bool: True если монитор валиден
        """
        try:
            if monitor is None:
                logger.error("[MONITOR-VAL] ❌ Monitor is None")
                return False
            
            logger.debug("[MONITOR-VAL] Validating monitor instance...")
            
            # Проверка обязательных методов
            if not self._validate_methods(monitor):
                return False
            
            # Проверка callable методов
            if not self._validate_callable(monitor):
                return False
            
            logger.info("[MONITOR-VAL] ✅ Monitor validation passed")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-VAL] ❌ Validation error: {e}", exc_info=True)
            return False
    
    def _validate_methods(self, monitor: 'IntegratedCryptoMonitor') -> bool:
        """
        Проверка наличия обязательных методов
        
        Args:
            monitor: Монитор для проверки
            
        Returns:
            bool: True если все методы присутствуют
        """
        # IntegratedCryptoMonitor использует 'run()' и 'stop()'
        required_methods = ['run', 'stop']
        
        for method in required_methods:
            if not hasattr(monitor, method):
                logger.error(f"[MONITOR-VAL] ❌ Monitor missing method: {method}")
                return False
            logger.debug(f"[MONITOR-VAL] ✅ Monitor has method: {method}")
        
        return True
    
    def _validate_callable(self, monitor: 'IntegratedCryptoMonitor') -> bool:
        """
        Проверка что методы callable
        
        Args:
            monitor: Монитор для проверки
            
        Returns:
            bool: True если методы callable
        """
        required_methods = ['run', 'stop']
        
        for method in required_methods:
            if not callable(getattr(monitor, method)):
                logger.error(f"[MONITOR-VAL] ❌ Method not callable: {method}")
                return False
            logger.debug(f"[MONITOR-VAL] ✅ Method callable: {method}")
        
        return True


class MonitorInitializer:
    """
    Инициализатор системы мониторинга
    
    Координирует инициализацию IntegratedCryptoMonitor с использованием
    валидаторов, checker'ов и factory.
    
    Responsibilities:
    -----------------
    - Координация процесса инициализации
    - Валидация конфигурации и зависимостей
    - Создание и проверка монитора
    - Управление жизненным циклом
    
    Attributes:
        config: Объект конфигурации
        db_manager: Database manager (опционально)
        monitor: Инстанс IntegratedCryptoMonitor после инициализации
    """
    
    def __init__(self, config: Any, db_manager: Optional[Any] = None):
        """
        Инициализация monitor initializer
        
        Args:
            config: Объект конфигурации приложения
            db_manager: Database manager (опционально)
        """
        self.config = config
        self.db_manager = db_manager
        self.monitor: Optional['IntegratedCryptoMonitor'] = None
        self._initialized: bool = False
        
        # Инициализация компонентов
        self.config_validator = MonitorConfigValidator()
        self.dependency_checker = MonitorDependencyChecker()
        self.monitor_validator = MonitorValidator()
        
        logger.debug("[MONITOR-INIT] MonitorInitializer created")
    
    def initialize(self) -> bool:
        """
        Инициализация системы мониторинга
        
        Выполняет полный цикл инициализации:
        1. Валидация конфигурации
        2. Проверка зависимостей
        3. Создание IntegratedCryptoMonitor
        4. Валидация монитора
        
        Returns:
            bool: True если инициализация успешна
        """
        if self._initialized:
            logger.debug("[MONITOR-INIT] Monitor already initialized")
            return True
        
        try:
            logger.info("[MONITOR-INIT] Starting monitor initialization...")
            
            # Шаг 1: Валидация конфигурации
            if not self._validate_configuration():
                return False
            
            # Шаг 2: Проверка зависимостей
            if not self._check_dependencies():
                return False
            
            # Шаг 3: Создание монитора
            if not self._create_monitor():
                return False
            
            # Шаг 4: Валидация монитора
            if not self._validate_monitor():
                return False
            
            self._initialized = True
            logger.info("[MONITOR-INIT] ✅ Monitor initialized successfully")
            
            return True
        
        except Exception as e:
            logger.error(
                f"[MONITOR-INIT] ❌ Initialization failed: {e}",
                exc_info=True
            )
            return False
    
    def _validate_configuration(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            bool: True если конфигурация валидна
        """
        logger.debug("[MONITOR-INIT] Step 1/4: Validating configuration...")
        
        if not self.config_validator.validate(self.config):
            logger.error("[MONITOR-INIT] ❌ Configuration validation failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Configuration validated")
        return True
    
    def _check_dependencies(self) -> bool:
        """
        Проверка зависимостей
        
        Returns:
            bool: True если все зависимости доступны
        """
        logger.debug("[MONITOR-INIT] Step 2/4: Checking dependencies...")
        
        if not self.dependency_checker.check_all(self.db_manager):
            logger.error("[MONITOR-INIT] ❌ Dependency check failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Dependencies checked")
        return True
    
    def _create_monitor(self) -> bool:
        """
        Создание монитора
        
        Returns:
            bool: True если монитор создан успешно
        """
        logger.debug("[MONITOR-INIT] Step 3/4: Creating monitor...")
        
        factory = MonitorFactory(self.config, self.db_manager)
        self.monitor = factory.create_monitor()
        
        if self.monitor is None:
            logger.error("[MONITOR-INIT] ❌ Monitor creation failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Monitor created")
        return True
    
    def _validate_monitor(self) -> bool:
        """
        Валидация созданного монитора
        
        Returns:
            bool: True если монитор валиден
        """
        logger.debug("[MONITOR-INIT] Step 4/4: Validating monitor...")
        
        if not self.monitor_validator.validate(self.monitor):
            logger.error("[MONITOR-INIT] ❌ Monitor validation failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Monitor validated")
        return True
    
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
            bool: True если инициализация завершена успешно
        """
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса инициализатора
        
        Returns:
            Dict[str, Any]: Информация о состоянии
        """
        return {
            'initialized': self._initialized,
            'has_monitor': self.monitor is not None,
            'monitor_type': type(self.monitor).__name__ if self.monitor else None,
            'has_config': self.config is not None,
            'has_db_manager': self.db_manager is not None
        }
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown монитора
        
        Корректно останавливает и освобождает ресурсы монитора.
        """
        if not self.monitor:
            logger.debug("[MONITOR-INIT] No monitor to shutdown")
            return
        
        try:
            logger.info("[MONITOR-INIT] Shutting down monitor...")
            
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
            
            logger.info("[MONITOR-INIT] ✅ Monitor shut down successfully")
        
        except Exception as e:
            logger.error(f"[MONITOR-INIT] ❌ Shutdown error: {e}", exc_info=True)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"MonitorInitializer("
            f"initialized={self._initialized}, "
            f"has_monitor={self.monitor is not None}, "
            f"has_config={self.config is not None}"
            f")"
        )


__all__ = [
    'MonitorInitializer',
    'MonitorConfigValidator',
    'MonitorDependencyChecker',
    'MonitorFactory',
    'MonitorValidator'
]