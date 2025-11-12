# core/initialization/monitor.py
"""
Monitor Initializer - Production Ready v5.1
============================================

Инициализация системы мониторинга с интеграцией IntegratedCryptoMonitor v5.0.

Components:
-----------
- MonitorConfigValidator: Валидация конфигурации
- MonitorDependencyChecker: Проверка зависимостей
- MonitorFactory: Создание монитора
- MonitorValidator: Валидация монитора
- MonitorInitializer: Координация полной инициализации

Architecture v5.1:
------------------
- Интеграция с двухэтапной инициализацией Monitor v5.0
- MonitorInitializer полностью инициализирует монитор (включая async initialize())
- Production-grade error handling
- Comprehensive validation
- FIXED: Улучшена валидация db_manager (опциональные методы)
"""

from typing import Optional, Any, Dict, TYPE_CHECKING
from core.logging_config import get_logger

if TYPE_CHECKING:
    from core.monitor import IntegratedCryptoMonitor
    from app.config import Config

logger = get_logger(__name__)


class MonitorConfigValidator:
    """
    Валидатор конфигурации монитора
    
    Проверяет:
    - Наличие config объекта
    - Структуру конфигурации
    - Обязательные параметры
    """
    
    def __init__(self):
        """Инициализация валидатора"""
        logger.debug("[MONITOR-CONFIG] ConfigValidator initialized")
    
    def validate(self, config: Any) -> bool:
        """
        Валидация конфигурации
        
        Args:
            config: Объект конфигурации
            
        Returns:
            bool: True если конфигурация валидна
        """
        try:
            if config is None:
                logger.error("[MONITOR-CONFIG] Config is None")
                return False
            
            logger.debug("[MONITOR-CONFIG] Validating config...")
            
            if not self._is_config_object(config):
                logger.error("[MONITOR-CONFIG] Invalid config type")
                return False
            
            if not self._validate_required_attributes(config):
                return False
            
            logger.info("[MONITOR-CONFIG] ✅ Config validation passed")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-CONFIG] ❌ Validation error: {e}", exc_info=True)
            return False
    
    def _is_config_object(self, config: Any) -> bool:
        """Проверка типа config объекта"""
        required_attrs = ['telegram', 'database', 'features']
        
        for attr in required_attrs:
            if not hasattr(config, attr):
                logger.error(f"[MONITOR-CONFIG] Missing attribute: {attr}")
                return False
        
        logger.debug("[MONITOR-CONFIG] ✅ Config type valid")
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
            # Проверяем только telegram config
            # Database НЕ проверяем - он уже инициализирован на шаге 2
            
            if not hasattr(config, 'telegram'):
                logger.error("[MONITOR-CONFIG] Missing telegram config")
                return False
            
            if not hasattr(config.telegram, 'bot_token'):
                logger.error("[MONITOR-CONFIG] Missing telegram.bot_token")
                return False
            
            logger.debug("[MONITOR-CONFIG] ✅ All required attributes present")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-CONFIG] ❌ Attribute validation error: {e}")
            return False


class MonitorDependencyChecker:
    """
    Проверка зависимостей монитора
    
    Проверяет:
    - Наличие необходимых модулей
    - Валидность database manager (опционально)
    - Доступность компонентов
    """
    
    def __init__(self):
        """Инициализация checker"""
        logger.debug("[MONITOR-DEPS] DependencyChecker initialized")
    
    def check_all(self, db_manager: Optional[Any] = None) -> bool:
        """
        Проверка всех зависимостей
        
        Args:
            db_manager: Database manager (опционально)
            
        Returns:
            bool: True если все зависимости доступны
        """
        try:
            logger.debug("[MONITOR-DEPS] Checking dependencies...")
            
            if not self._check_required_modules():
                return False
            
            if db_manager is not None:
                if not self._validate_db_manager(db_manager):
                    return False
            else:
                logger.debug("[MONITOR-DEPS] No db_manager provided (optional)")
            
            logger.info("[MONITOR-DEPS] ✅ All dependencies available")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-DEPS] ❌ Check error: {e}", exc_info=True)
            return False
    
    def _check_required_modules(self) -> bool:
        """Проверка наличия модулей"""
        required_modules = [
            'core.monitor',
            'core.logging_config',
            'app.config'
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                logger.debug(f"[MONITOR-DEPS] ✅ Module: {module_name}")
            except ImportError as e:
                logger.error(f"[MONITOR-DEPS] ❌ Missing: {module_name} - {e}")
                return False
        
        return True
    
    def _validate_db_manager(self, db_manager: Any) -> bool:
        """
        Валидация database manager
        
        Args:
            db_manager: Database manager для проверки
            
        Returns:
            bool: True если валиден
        """
        if db_manager is None:
            logger.warning("[MONITOR-DEPS] DB manager is None")
            return True  # Опционально
        
        # Проверяем основные методы (хотя бы один должен быть)
        # get_session или close или shutdown
        has_get_session = hasattr(db_manager, 'get_session') and callable(getattr(db_manager, 'get_session'))
        has_close = hasattr(db_manager, 'close') and callable(getattr(db_manager, 'close'))
        has_shutdown = hasattr(db_manager, 'shutdown') and callable(getattr(db_manager, 'shutdown'))
        
        if not (has_get_session or has_close or has_shutdown):
            logger.error(
                "[MONITOR-DEPS] DB manager missing required methods "
                "(get_session, close, or shutdown)"
            )
            return False
        
        # Логируем какие методы доступны
        methods_available = []
        if has_get_session:
            methods_available.append('get_session')
        if has_close:
            methods_available.append('close')
        if has_shutdown:
            methods_available.append('shutdown')
        
        logger.debug(f"[MONITOR-DEPS] ✅ DB manager valid, methods: {', '.join(methods_available)}")
        return True


class MonitorFactory:
    """
    Фабрика для создания монитора
    
    Создаёт IntegratedCryptoMonitor через __init__
    (без async инициализации)
    """
    
    def __init__(self, config: Any, db_manager: Optional[Any] = None):
        """
        Инициализация фабрики
        
        Args:
            config: Конфигурация
            db_manager: Database manager
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
            
            # Lazy import
            from core.monitor import IntegratedCryptoMonitor
            
            # Получаем max_memory из конфигурации если есть
            max_memory = 450  # default
            if hasattr(self.config, 'MAX_MEMORY_MB'):
                max_memory = self.config.MAX_MEMORY_MB
            
            # Создаём монитор (только __init__, без async initialize)
            monitor = IntegratedCryptoMonitor(max_memory_mb=max_memory)
            
            if monitor is None:
                logger.error("[MONITOR-FACTORY] ❌ Failed to create monitor")
                return None
            
            logger.info("[MONITOR-FACTORY] ✅ Monitor instance created")
            return monitor
        
        except ImportError as e:
            logger.error(f"[MONITOR-FACTORY] ❌ Import failed: {e}", exc_info=True)
            return None
        
        except Exception as e:
            logger.error(f"[MONITOR-FACTORY] ❌ Creation failed: {e}", exc_info=True)
            return None


class MonitorValidator:
    """
    Валидатор созданного монитора
    
    Проверяет:
    - Структуру монитора
    - Наличие методов
    - Callable методов
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
            bool: True если валиден
        """
        try:
            if monitor is None:
                logger.error("[MONITOR-VAL] ❌ Monitor is None")
                return False
            
            logger.debug("[MONITOR-VAL] Validating monitor...")
            
            if not self._validate_methods(monitor):
                return False
            
            if not self._validate_callable(monitor):
                return False
            
            logger.info("[MONITOR-VAL] ✅ Monitor validation passed")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-VAL] ❌ Validation error: {e}", exc_info=True)
            return False
    
    def _validate_methods(self, monitor: 'IntegratedCryptoMonitor') -> bool:
        """Проверка наличия методов"""
        required_methods = ['initialize', 'run', 'stop', 'get_status']
        
        for method in required_methods:
            if not hasattr(monitor, method):
                logger.error(f"[MONITOR-VAL] ❌ Missing method: {method}")
                return False
            logger.debug(f"[MONITOR-VAL] ✅ Has method: {method}")
        
        return True
    
    def _validate_callable(self, monitor: 'IntegratedCryptoMonitor') -> bool:
        """Проверка callable методов"""
        required_methods = ['initialize', 'run', 'stop', 'get_status']
        
        for method in required_methods:
            if not callable(getattr(monitor, method)):
                logger.error(f"[MONITOR-VAL] ❌ Not callable: {method}")
                return False
            logger.debug(f"[MONITOR-VAL] ✅ Callable: {method}")
        
        return True


class MonitorInitializer:
    """
    Инициализатор системы мониторинга v5.1
    
    Полностью инициализирует IntegratedCryptoMonitor:
    1. Валидация конфигурации
    2. Проверка зависимостей
    3. Создание монитора (__init__)
    4. Async инициализация (monitor.initialize())
    5. Валидация готовности
    
    Attributes:
        config: Конфигурация
        db_manager: Database manager (опционально)
        monitor: Инстанс IntegratedCryptoMonitor
    """
    
    def __init__(self, config: Any, db_manager: Optional[Any] = None):
        """
        Инициализация initializer
        
        Args:
            config: Конфигурация приложения
            db_manager: Database manager (опционально)
        """
        self.config = config
        self.db_manager = db_manager
        self.monitor: Optional['IntegratedCryptoMonitor'] = None
        self._initialized = False
        
        # Компоненты инициализации
        self.config_validator = MonitorConfigValidator()
        self.dependency_checker = MonitorDependencyChecker()
        self.monitor_validator = MonitorValidator()
        
        logger.debug("[MONITOR-INIT] MonitorInitializer created")
    
    async def initialize(self) -> Optional['IntegratedCryptoMonitor']:
        """
        Полная инициализация монитора
        
        Выполняет все шаги:
        1. Валидация конфигурации
        2. Проверка зависимостей
        3. Создание монитора
        4. Async инициализация монитора
        5. Валидация монитора
        
        Returns:
            IntegratedCryptoMonitor или None при ошибке
        """
        if self._initialized and self.monitor is not None:
            logger.debug("[MONITOR-INIT] Already initialized")
            return self.monitor
        
        try:
            logger.info("[MONITOR-INIT] Starting monitor initialization...")
            
            # Шаг 1: Валидация конфигурации
            if not self._validate_configuration():
                return None
            
            # Шаг 2: Проверка зависимостей
            if not self._check_dependencies():
                return None
            
            # Шаг 3: Создание монитора (sync __init__)
            if not self._create_monitor():
                return None
            
            # Шаг 4: Async инициализация монитора
            if not await self._initialize_monitor_async():
                return None
            
            # Шаг 5: Валидация монитора
            if not self._validate_monitor():
                return None
            
            self._initialized = True
            logger.info("[MONITOR-INIT] ✅ Monitor fully initialized")
            
            return self.monitor
        
        except Exception as e:
            logger.error(f"[MONITOR-INIT] ❌ Initialization failed: {e}", exc_info=True)
            return None
    
    def _validate_configuration(self) -> bool:
        """Step 1: Валидация конфигурации"""
        logger.debug("[MONITOR-INIT] Step 1/5: Validating configuration...")
        
        if not self.config_validator.validate(self.config):
            logger.error("[MONITOR-INIT] ❌ Configuration invalid")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Configuration validated")
        return True
    
    def _check_dependencies(self) -> bool:
        """Step 2: Проверка зависимостей"""
        logger.debug("[MONITOR-INIT] Step 2/5: Checking dependencies...")
        
        if not self.dependency_checker.check_all(self.db_manager):
            logger.error("[MONITOR-INIT] ❌ Dependencies check failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Dependencies checked")
        return True
    
    def _create_monitor(self) -> bool:
        """Step 3: Создание монитора (sync __init__)"""
        logger.debug("[MONITOR-INIT] Step 3/5: Creating monitor...")
        
        factory = MonitorFactory(self.config, self.db_manager)
        self.monitor = factory.create_monitor()
        
        if self.monitor is None:
            logger.error("[MONITOR-INIT] ❌ Monitor creation failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Monitor created")
        return True
    
    async def _initialize_monitor_async(self) -> bool:
        """Step 4: Async инициализация монитора"""
        logger.debug("[MONITOR-INIT] Step 4/5: Async initializing monitor...")
        
        if self.monitor is None:
            logger.error("[MONITOR-INIT] ❌ Monitor is None")
            return False
        
        try:
            # Вызываем monitor.initialize() для загрузки business компонентов
            success = await self.monitor.initialize()
            
            if not success:
                logger.error("[MONITOR-INIT] ❌ Monitor async initialization failed")
                return False
            
            logger.info("[MONITOR-INIT] ✅ Monitor async initialized")
            return True
        
        except Exception as e:
            logger.error(f"[MONITOR-INIT] ❌ Async init error: {e}", exc_info=True)
            return False
    
    def _validate_monitor(self) -> bool:
        """Step 5: Валидация монитора"""
        logger.debug("[MONITOR-INIT] Step 5/5: Validating monitor...")
        
        if not self.monitor_validator.validate(self.monitor):
            logger.error("[MONITOR-INIT] ❌ Monitor validation failed")
            return False
        
        logger.info("[MONITOR-INIT] ✅ Monitor validated")
        return True
    
    def get_monitor(self) -> Optional['IntegratedCryptoMonitor']:
        """Получить инициализированный монитор"""
        return self.monitor
    
    def is_initialized(self) -> bool:
        """Проверить статус инициализации"""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус initializer"""
        return {
            'initialized': self._initialized,
            'has_monitor': self.monitor is not None,
            'monitor_type': type(self.monitor).__name__ if self.monitor else None,
            'has_config': self.config is not None,
            'has_db_manager': self.db_manager is not None
        }
    
    async def shutdown(self) -> None:
        """Graceful shutdown монитора"""
        if not self.monitor:
            logger.debug("[MONITOR-INIT] No monitor to shutdown")
            return
        
        try:
            logger.info("[MONITOR-INIT] Shutting down monitor...")
            
            if hasattr(self.monitor, 'stop'):
                import asyncio
                if asyncio.iscoroutinefunction(self.monitor.stop):
                    await self.monitor.stop()
                else:
                    self.monitor.stop()
            
            self._initialized = False
            self.monitor = None
            
            logger.info("[MONITOR-INIT] ✅ Monitor shut down")
        
        except Exception as e:
            logger.error(f"[MONITOR-INIT] ❌ Shutdown error: {e}", exc_info=True)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"MonitorInitializer("
            f"initialized={self._initialized}, "
            f"has_monitor={self.monitor is not None}"
            f")"
        )


__all__ = [
    'MonitorInitializer',
    'MonitorConfigValidator',
    'MonitorDependencyChecker',
    'MonitorFactory',
    'MonitorValidator'
]