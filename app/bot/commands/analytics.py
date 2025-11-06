# app/bot/commands/analytics.py
"""
Analytics commands
"""

import traceback
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin, send_long_message, format_number


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /analytics"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.analytics_enabled:
            await update.message.reply_text("❌ Analytics engine не инициализирован")
            return
        
        text = "<b>📊 АНАЛИТИКА ПО АКТИВАМ</b>\n\n"
        
        text += "<b>🔝 ТОП ПО ОБЪЕМУ (24ч)</b>\n"
        try:
            top_by_volume = scheduler.get_top_assets_by_volume(limit=10)
            for i, item in enumerate(top_by_volume, 1):
                text += f"{i}. {item['asset']}: {format_number(item['volume_24h'])}\n"
        except:
            text += "Данные недоступны\n"
        
        text += "\n<b>📈 НАИБОЛЕЕ АКТИВНЫЕ</b>\n"
        try:
            most_active = scheduler.get_most_active_assets(hours=24, limit=10)
            for i, item in enumerate(most_active, 1):
                text += f"{i}. {item['asset']}: {item['event_count']} событий\n"
        except:
            text += "Данные недоступны\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /sentiment <ASSET>"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.analytics_enabled:
            await update.message.reply_text("❌ Analytics engine не инициализирован")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ Укажите актив\n\nПример: /sentiment BTC")
            return
        
        asset = context.args[0].upper()
        
        await update.message.reply_text(f"📊 Анализирую sentiment для {asset}...")
        
        from app.analytics import get_analytics_engine
        
        analytics = get_analytics_engine()
        
        try:
            sentiment_data = await analytics.analyze_sentiment(asset)
            
            text = f"<b>📊 SENTIMENT: {asset}</b>\n\n"
            
            text += f"<b>Sentiment:</b> {sentiment_data.get('overall', 'Neutral')}\n"
            text += f"<b>Score:</b> {sentiment_data.get('score', 0):.2f}/100\n\n"
            
            text += "<b>Источники:</b>\n"
            text += f"• News: {sentiment_data.get('news_sentiment', 'N/A')}\n"
            text += f"• Social: {sentiment_data.get('social_sentiment', 'N/A')}\n"
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            
        except Exception:
            text = f"❌ Не удалось получить sentiment для {asset}\n\n"
            text += "<i>Доступные: BTC, ETH, BNB, SOL</i>"
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


__all__ = ['cmd_analytics', 'cmd_sentiment']