# app/bot/__init__.py
"""
Telegram Bot - Main Entry Point
"""

from telegram.ext import Application
from app.config import config

_application = None
_bot = None
_handlers_registered = False


def get_application() -> Application:
    """Получить единственный экземпляр application"""
    global _application, _bot
    
    if _application is None:
        token = config.telegram.token
        _application = Application.builder().token(token).build()
        _bot = _application.bot
        print("✅ [BOT] Telegram bot initialized")
    
    return _application


def get_bot():
    """Получить bot instance"""
    global _bot
    if _bot is None:
        get_application()
    return _bot


def register_all_handlers():
    """Регистрация всех обработчиков"""
    global _handlers_registered
    
    if _handlers_registered:
        print("⚠️  [BOT] Handlers already registered")
        return
    
    from app.bot.handlers import register_handlers
    register_handlers()
    
    _handlers_registered = True
    print("✅ [BOT] All handlers registered")


application = get_application()
bot = get_bot()

__all__ = ['application', 'bot', 'get_application', 'get_bot', 'register_all_handlers']