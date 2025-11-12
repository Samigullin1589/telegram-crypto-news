"""
Database Initializer
Инициализация и проверка базы данных

Выполняет:
- Получение и инициализацию DatabaseManager
- Проверку соединения с БД
- Валидацию структуры БД
- Подготовку к работе
"""

import asyncio
from typing import Optional
from core.logging_config import get_logger
from app.config.database import get_db_manager, DatabaseManager

logger = get_logger(__name__)


class DatabaseInitializer:
    """
    Инициализатор базы данных
    
    Отвечает за корректную инициализацию DatabaseManager,
    проверку соединения и подготовку БД к работе.
    
    Attributes:
        db_manager: Инстанс DatabaseManager после инициализации
    """
    
    def __init__(self):
        """Инициализация database initializer"""
        self.db_manager: Optional[DatabaseManager] = None
        self._initialized: bool = False
    
    async def initialize(self) -> bool:
        """
        Инициализация базы данных
        
        Выполняет полный цикл инициализации:
        1. Получение DatabaseManager
        2. Инициализация менеджера
        3. Проверка соединения (опционально)
        4. Валидация структуры (опционально)
        
        Returns:
            True если инициализация успешна
        """
        if self._initialized:
            logger.debug("Database already initialized")
            return True
        
        try:
            logger.info("Starting database initialization...")
            
            # Получаем database manager
            if not await self._get_manager():
                return False
            
            # Инициализируем manager если необходимо
            if not await self._initialize_manager():
                return False
            
            # Проверяем соединение (опционально)
            await self._verify_connection()
            
            # Валидируем структуру (опционально)
            await self._validate_structure()
            
            self._initialized = True
            logger.info("✅ Database initialized successfully")
            
            return True
        
        except Exception as e:
            logger.error(
                f"❌ Database initialization failed: {e}",
                exc_info=True
            )
            return False
    
    async def _get_manager(self) -> bool:
        """
        Получение DatabaseManager
        
        Returns:
            True если успешно получен
        """
        try:
            logger.debug("Getting DatabaseManager instance...")
            self.db_manager = get_db_manager()
            
            if self.db_manager is None:
                logger.error("❌ Failed to get DatabaseManager instance")
                return False
            
            logger.debug("✅ DatabaseManager instance obtained")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error getting DatabaseManager: {e}", exc_info=True)
            return False
    
    async def _initialize_manager(self) -> bool:
        """
        Инициализация DatabaseManager
        
        Returns:
            True если успешно инициализирован
        """
        try:
            if not self.db_manager:
                logger.error("❌ DatabaseManager is None")
                return False
            
            # Проверяем состояние инициализации
            if hasattr(self.db_manager, '_initialized') and self.db_manager._initialized:
                logger.debug("DatabaseManager already initialized")
                return True
            
            logger.info("Initializing DatabaseManager...")
            
            # Инициализируем manager
            if asyncio.iscoroutinefunction(self.db_manager.initialize):
                result = await self.db_manager.initialize()
            else:
                result = self.db_manager.initialize()
            
            if result:
                logger.info("✅ DatabaseManager initialized")
                return True
            else:
                logger.error("❌ DatabaseManager initialization returned False/None")
                return False
        
        except Exception as e:
            logger.error(
                f"❌ DatabaseManager initialization error: {e}",
                exc_info=True
            )
            return False
    
    async def _verify_connection(self) -> bool:
        """
        Проверка соединения с базой данных (опционально)
        
        Выполняет простой SELECT запрос для проверки работоспособности.
        Не является критичным - если метода нет, просто пропускаем.
        
        Returns:
            True если соединение работает или проверка недоступна
        """
        try:
            logger.debug("Verifying database connection...")
            
            if not self.db_manager:
                logger.error("❌ DatabaseManager is None")
                return False
            
            # Пытаемся использовать get_session если доступен
            if hasattr(self.db_manager, 'get_session') and callable(self.db_manager.get_session):
                try:
                    async with self.db_manager.get_session() as session:
                        # Успешно получили сессию
                        logger.info("✅ Database connection verified (via get_session)")
                        return True
                except Exception as session_error:
                    logger.warning(f"⚠️ Session check failed: {session_error}")
                    return True  # Не критично
            
            # Проверяем health check если доступен
            elif hasattr(self.db_manager, 'health_check') and callable(self.db_manager.health_check):
                try:
                    health_result = await self.db_manager.health_check()
                    
                    if health_result.get('healthy'):
                        logger.info("✅ Database connection verified via health check")
                        return True
                    else:
                        logger.warning(
                            f"⚠️ Database health check degraded: "
                            f"{health_result.get('status', 'Unknown')}"
                        )
                        return True  # Не критично
                except Exception as health_error:
                    logger.warning(f"⚠️ Health check failed: {health_error}")
                    return True  # Не критично
            
            else:
                logger.warning("⚠️ Cannot verify connection - no suitable method available")
                return True  # Предполагаем что всё ОК
        
        except Exception as e:
            logger.warning(
                f"⚠️ Database connection verification error: {e}",
                exc_info=True
            )
            return True  # Не критично для инициализации
    
    async def _validate_structure(self) -> bool:
        """
        Валидация структуры базы данных (опционально)
        
        Проверяет наличие необходимых таблиц и индексов.
        Не является критичным - если метода нет, просто пропускаем.
        
        Returns:
            True если структура валидна, создана, или проверка недоступна
        """
        try:
            logger.debug("Validating database structure...")
            
            if not self.db_manager:
                logger.error("❌ DatabaseManager is None")
                return False
            
            # Если есть метод проверки схемы - используем его
            if hasattr(self.db_manager, 'validate_schema') and callable(self.db_manager.validate_schema):
                try:
                    result = await self.db_manager.validate_schema()
                    
                    if result:
                        logger.info("✅ Database structure validated")
                        return True
                    else:
                        logger.warning("⚠️ Database structure validation failed")
                        return True  # Не критично
                except Exception as schema_error:
                    logger.warning(f"⚠️ Schema validation error: {schema_error}")
                    return True  # Не критично
            
            # Иначе просто логируем что пропустили проверку
            logger.debug("ℹ️ Schema validation not available - skipping")
            return True
        
        except Exception as e:
            logger.warning(
                f"⚠️ Database structure validation error: {e}",
                exc_info=True
            )
            return True  # Не критично для инициализации
    
    def get_manager(self) -> Optional[DatabaseManager]:
        """
        Получение инициализированного DatabaseManager
        
        Returns:
            DatabaseManager или None если не инициализирован
        """
        return self.db_manager
    
    def is_initialized(self) -> bool:
        """
        Проверка состояния инициализации
        
        Returns:
            True если инициализация завершена успешно
        """
        return self._initialized
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown базы данных
        
        Корректно закрывает все соединения и освобождает ресурсы
        """
        if not self.db_manager:
            logger.debug("No DatabaseManager to shutdown")
            return
        
        try:
            logger.info("Shutting down database...")
            
            if hasattr(self.db_manager, 'shutdown') and callable(self.db_manager.shutdown):
                if asyncio.iscoroutinefunction(self.db_manager.shutdown):
                    await self.db_manager.shutdown()
                else:
                    self.db_manager.shutdown()
            
            elif hasattr(self.db_manager, 'close') and callable(self.db_manager.close):
                if asyncio.iscoroutinefunction(self.db_manager.close):
                    await self.db_manager.close()
                else:
                    self.db_manager.close()
            
            self._initialized = False
            logger.info("✅ Database shut down successfully")
        
        except Exception as e:
            logger.error(f"❌ Database shutdown error: {e}", exc_info=True)
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (
            f"DatabaseInitializer("
            f"initialized={self._initialized}, "
            f"has_manager={self.db_manager is not None}"
            f")"
        )


__all__ = ['DatabaseInitializer']