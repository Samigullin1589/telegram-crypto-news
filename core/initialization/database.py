# core/initialization/database.py
"""
Database Initializer - Инициализация базы данных
"""

from typing import Optional
from core.logging_config import get_logger
from app import get_database_manager, DatabaseManager

logger = get_logger(__name__)


class DatabaseInitializer:
    """
    Инициализация и проверка базы данных
    
    Выполняет:
    - Инициализацию DatabaseManager
    - Проверку соединения
    - Создание необходимых таблиц
    - Миграции (если требуются)
    """
    
    def __init__(self):
        """Инициализация"""
        self.db_manager: Optional[DatabaseManager] = None
    
    async def initialize(self) -> bool:
        """
        Инициализация БД
        
        Returns:
            bool: True если успешно
        """
        try:
            # Получаем database manager
            self.db_manager = get_database_manager()
            
            # Инициализируем если нужно
            if not self.db_manager.is_initialized:
                logger.info("Initializing DatabaseManager...")
                self.db_manager.initialize()
            
            logger.info(f"✅ Database path: {self.db_manager.config.db_path}")
            
            # Проверяем соединение
            if not await self._verify_connection():
                return False
            
            logger.info("✅ Database initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}", exc_info=True)
            return False
    
    async def _verify_connection(self) -> bool:
        """
        Проверка соединения с БД
        
        Returns:
            bool: True если соединение работает
        """
        try:
            cursor = self.db_manager.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0] == 1:
                logger.info("✅ Database connection verified")
                return True
            else:
                logger.error("❌ Database connection check failed")
                return False
        
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}", exc_info=True)
            return False
    
    def get_manager(self) -> Optional[DatabaseManager]:
        """
        Получение инициализированного manager
        
        Returns:
            Optional[DatabaseManager]: Database manager или None
        """
        return self.db_manager