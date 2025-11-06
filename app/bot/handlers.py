# app/bot/handlers.py
"""
Handler registration and callback processing
"""

import traceback
from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from app.bot import get_application
from app.bot.commands.basic import cmd_start, cmd_help, cmd_menu
from app.bot.commands.monitoring import cmd_status, cmd_wallets, cmd_whales, cmd_discover
from app.bot.commands.trading import (
    cmd_positions,
    cmd_performance,
    cmd_signal,
    cmd_close_position,
    cmd_trades
)
from app.bot.commands.settings import cmd_config, cmd_thresholds, cmd_regime
from app.bot.commands.control import cmd_pause, cmd_resume, cmd_logs, cmd_admin
from app.bot.commands.analytics import cmd_analytics, cmd_sentiment


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline кнопок"""
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    fake_update = Update(update.update_id)
    fake_update._message = query.message
    fake_update._effective_user = query.from_user
    fake_update._effective_chat = query.message.chat
    
    try:
        if data == "status":
            await cmd_status(fake_update, context)
        
        elif data == "positions":
            await cmd_positions(fake_update, context)
        
        elif data == "performance":
            await cmd_performance(fake_update, context)
        
        elif data == "wallets":
            await cmd_wallets(fake_update, context)
        
        elif data == "config":
            await cmd_config(fake_update, context)
        
        elif data == "thresholds":
            await cmd_thresholds(fake_update, context)
        
        elif data == "regime":
            await cmd_regime(fake_update, context)
        
        elif data == "discover":
            await cmd_discover(fake_update, context)
        
        elif data == "admin_panel":
            await cmd_admin(fake_update, context)
        
        elif data == "menu":
            await cmd_menu(fake_update, context)
        
        elif data == "help":
            await cmd_help(fake_update, context)
        
        else:
            await query.edit_message_text(f"Unknown action: {data}")
    
    except Exception as e:
        error_text = f"❌ Ошибка: {e}"
        try:
            await query.edit_message_text(error_text)
        except:
            await query.message.reply_text(error_text)
        traceback.print_exc()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    
    print(f"❌ [BOT] Exception while handling update {update}:")
    traceback.print_exc()
    
    if context.error:
        print(f"Error: {context.error}")
    
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке команды."
            )
        except:
            pass


def register_handlers():
    """Регистрация всех обработчиков команд"""
    
    app = get_application()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("wallets", cmd_wallets))
    app.add_handler(CommandHandler("whales", cmd_whales))
    app.add_handler(CommandHandler("discover", cmd_discover))
    
    app.add_handler(CommandHandler("positions", cmd_positions))
    app.add_handler(CommandHandler("performance", cmd_performance))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("close", cmd_close_position))
    app.add_handler(CommandHandler("trades", cmd_trades))
    
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("thresholds", cmd_thresholds))
    app.add_handler(CommandHandler("regime", cmd_regime))
    
    app.add_handler(CommandHandler("analytics", cmd_analytics))
    app.add_handler(CommandHandler("sentiment", cmd_sentiment))
    
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("logs", cmd_logs))
    
    app.add_handler(CommandHandler("admin", cmd_admin))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    app.add_error_handler(error_handler)
    
    print("✅ [BOT] Handlers registered")


__all__ = ['register_handlers', 'callback_handler', 'error_handler']