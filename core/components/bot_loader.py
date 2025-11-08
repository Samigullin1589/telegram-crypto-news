# core/components/bot_loader.py
"""
Bot Application Loader
Загрузчик Telegram бота
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class BotLoader:
    """Загрузчик Bot Application"""
    
    def __init__(self, utils: Any):
        """
        Инициализация loader
        
        Args:
            utils: Утилиты загрузчика
        """
        self.utils = utils
    
    def load(self) -> Optional[Any]:
        """
        Загрузка Bot Application
        
        Returns:
            Application instance или None
        """
        try:
            logger.info("🤖 [BOT] Loading Bot Application...")
            
            # Загрузка application
            application = self._load_application()
            if not application:
                return None
            
            # Валидация
            if not self._validate_application(application):
                logger.error("❌ [BOT] Application validation failed")
                return None
            
            logger.info("✅ [BOT] Bot Application loaded successfully")
            return application
        
        except Exception as e:
            logger.error(f"❌ [BOT] Loading error: {e}", exc_info=True)
            return None
    
    def _load_application(self) -> Optional[Any]:
        """
        Загрузка application
        
        Returns:
            Application instance или None
        """
        try:
            from app.bot import application
            
            if application is None:
                logger.error("   Application is None in app.bot")
                return None
            
            logger.debug("   ✓ Application loaded from app.bot")
            return application
        
        except ImportError as e:
            logger.error(f"   Import error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"   Loading error: {e}")
            return None
    
    def _validate_application(self, application: Any) -> bool:
        """Валидация application"""
        required_attrs = ['bot', 'updater']
        
        for attr in required_attrs:
            if not hasattr(application, attr):
                logger.debug(f"   Missing attribute: {attr}")
        
        # Проверка что это telegram.ext.Application
        if not hasattr(application, 'run_polling') and not hasattr(application, 'run_webhook'):
            logger.error("   Not a valid telegram.ext.Application")
            return False
        
        return True


__all__ = ['BotLoader']