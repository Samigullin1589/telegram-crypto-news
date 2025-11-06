# app/bot/commands/control.py
"""
System control commands
"""

import traceback
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin, send_long_message
from app.bot.keyboards import get_admin_panel_keyboard


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /pause"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not hasattr(scheduler, 'paused'):
            scheduler.paused = False
        
        if scheduler.paused:
            await update.message.reply_text("⚠️  Система уже приостановлена")
            return
        
        scheduler.paused = True
        
        text = "⏸️  <b>СИСТЕМА ПРИОСТАНОВЛЕНА</b>\n\n"
        text += "• Публикация: ⏸️  Остановлена\n"
        text += "• Мониторинг: ✅ Продолжается\n\n"
        text += "<i>Используйте /resume для возобновления</i>"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /resume"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not hasattr(scheduler, 'paused'):
            scheduler.paused = False
        
        if not scheduler.paused:
            await update.message.reply_text("✅ Система уже работает")
            return
        
        scheduler.paused = False
        
        text = "▶️  <b>СИСТЕМА ВОЗОБНОВЛЕНА</b>\n\n"
        text += "• Публикация: ✅ Активна\n"
        text += "• Мониторинг: ✅ Активен\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /logs [lines]"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        lines_count = 50
        
        if context.args and len(context.args) > 0:
            try:
                lines_count = int(context.args[0])
                lines_count = min(max(lines_count, 10), 200)
            except:
                pass
        
        log_file = Path("logs/main.log")
        
        if not log_file.exists():
            log_file = Path("/tmp/crypto-compass.log")
        
        if not log_file.exists():
            await update.message.reply_text("📋 Лог-файл не найден")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines_count:]
                log_text = ''.join(recent_lines)
        except Exception:
            log_text = "Ошибка чтения лог-файла"
        
        text = f"<b>📋 ПОСЛЕДНИЕ {len(recent_lines)} СТРОК</b>\n\n"
        text += f"<code>{log_text[-3500:]}</code>"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    keyboard = get_admin_panel_keyboard()
    
    text = "<b>🔧 АДМИН ПАНЕЛЬ</b>\n\nВыберите действие:"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


__all__ = ['cmd_pause', 'cmd_resume', 'cmd_logs', 'cmd_admin']