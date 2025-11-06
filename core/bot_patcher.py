# core/bot_patcher.py
"""
Bot handlers patching for monitoring
"""

import logging
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BotHandlerPatcher:
    """Патчинг обработчиков команд бота"""
    
    def __init__(self, health_monitor: Any, statistics: Any):
        self.health_monitor = health_monitor
        self.statistics = statistics
    
    def patch_handlers(self, bot_app: Any) -> bool:
        """
        Патчит обработчики команд для мониторинга
        
        Returns:
            True если патчинг успешен
        """
        if not bot_app or not hasattr(bot_app, 'handlers'):
            return False
        
        try:
            handlers_dict = bot_app.handlers
            if not handlers_dict or 0 not in handlers_dict:
                return False
            
            handlers_list = handlers_dict[0]
            if not handlers_list:
                return False
            
            patched_count = 0
            
            for handler in handlers_list:
                if not hasattr(handler, 'callback'):
                    continue
                
                original_callback = handler.callback
                handler.callback = self._create_wrapped_callback(original_callback)
                patched_count += 1
            
            if patched_count > 0:
                logger.info(f"   ✓ Патчинг {patched_count} handlers успешен")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"   ⚠️  Ошибка при патчинге handlers: {e}")
            return False
    
    def _create_wrapped_callback(self, original_callback):
        """Создает обернутый callback"""
        health_monitor = self.health_monitor
        statistics = self.statistics
        
        @wraps(original_callback)
        async def wrapped_callback(update, context):
            health_monitor.record_bot_command()
            statistics.increment_bot_commands()
            
            try:
                return await original_callback(update, context)
            except Exception as e:
                health_monitor.record_error('bot')
                statistics.increment_errors()
                logger.error(f"❌ [BOT] Error in command handler: {e}")
                raise
        
        return wrapped_callback