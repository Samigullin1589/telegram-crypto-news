"""
Database Configuration Lifecycle Management
Управление жизненным циклом конфигурации БД (инициализация, shutdown)
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .database_config_core import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseConfigLifecycle:
    """Миксин для управления жизненным циклом конфигурации"""
    
    async def initialize(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Инициализация конфигурации и менеджера
        
        Returns:
            Результаты инициализации
        """
        if self._initialized:
            logger.warning("DatabaseConfig already initialized")
            return {'status': 'already_initialized'}
        
        logger.info("Initializing DatabaseConfig")
        
        results = {
            'status': 'initializing',
            'config': {
                'engine': self.engine.value,
                'host': self.host,
                'database': self.database
            }
        }
        
        try:
            # Инициализация менеджера если включен
            if self.enable_manager:
                manager_results = await self.manager.initialize()
                results['manager'] = manager_results
            
            self._initialized = True
            results['status'] = 'initialized'
            
            logger.info("DatabaseConfig initialized successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseConfig initialization failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['error'] = str(e)
            raise
    
    async def shutdown(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Graceful shutdown конфигурации и менеджера
        
        Returns:
            Результаты завершения
        """
        if not self._initialized:
            logger.warning("DatabaseConfig not initialized, nothing to shutdown")
            return {'status': 'not_initialized'}
        
        logger.info("Starting DatabaseConfig shutdown")
        
        results = {
            'status': 'shutting_down'
        }
        
        try:
            # Shutdown менеджера если есть
            if self._manager is not None:
                manager_results = await self.manager.shutdown()
                results['manager'] = manager_results
            
            self._initialized = False
            results['status'] = 'shutdown_complete'
            
            logger.info("DatabaseConfig shutdown complete")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseConfig shutdown error: {e}", exc_info=True)
            results['status'] = 'shutdown_error'
            results['error'] = str(e)
            return results
    
    async def restart(self: 'DatabaseConfig') -> Dict[str, Any]:
        """
        Перезапуск конфигурации (shutdown + initialize)
        
        Returns:
            Результаты перезапуска
        """
        logger.info("Restarting DatabaseConfig")
        
        results = {
            'status': 'restarting',
            'shutdown': None,
            'initialize': None
        }
        
        try:
            # Shutdown
            shutdown_results = await self.shutdown()
            results['shutdown'] = shutdown_results
            
            # Initialize
            init_results = await self.initialize()
            results['initialize'] = init_results
            
            results['status'] = 'restarted'
            logger.info("DatabaseConfig restarted successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"DatabaseConfig restart failed: {e}", exc_info=True)
            results['status'] = 'restart_failed'
            results['error'] = str(e)
            raise


__all__ = ['DatabaseConfigLifecycle']