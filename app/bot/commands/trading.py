# app/bot/commands/trading.py
"""
Trading system commands
"""

import traceback
import aiohttp
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin, send_long_message, format_duration, format_number


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /positions"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.trading_enabled:
            await update.message.reply_text("❌ Trading system отключен")
            return
        
        positions = scheduler.signal_generator.positions.get_open_positions()
        
        if not positions:
            await update.message.reply_text("📊 Нет открытых позиций")
            return
        
        text = "<b>💼 ОТКРЫТЫЕ ПОЗИЦИИ</b>\n\n"
        
        for p in positions:
            pnl_emoji = "🟢" if p.unrealized_pnl_usd and p.unrealized_pnl_usd > 0 else "🔴"
            
            text += f"{pnl_emoji} <b>{p.asset}</b> ({p.position_type.upper()})\n"
            text += f"Entry: ${p.entry_price:,.2f}\n"
            text += f"Current: ${p.current_price:,.2f}\n"
            text += f"P&L: {format_number(p.unrealized_pnl_usd)} ({p.unrealized_pnl_pct:+.2f}%)\n"
            text += f"Size: {format_number(p.amount_usd)}\n"
            text += f"ID: <code>{p.position_id}</code>\n\n"
        
        summary = scheduler.signal_generator.positions.get_summary()
        text += f"<b>📊 ИТОГО</b>\n"
        text += f"Позиций: {summary['total_open']}\n"
        text += f"Unrealized P&L: {format_number(summary['total_unrealized_pnl_usd'])}\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /performance [days]"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.trading_enabled:
            await update.message.reply_text("❌ Trading system отключен")
            return
        
        period_days = 30
        if context.args and len(context.args) > 0:
            try:
                period_days = int(context.args[0])
                period_days = max(1, min(365, period_days))
            except ValueError:
                pass
        
        await update.message.reply_text(f"📊 Рассчитываю за {period_days} дней...")
        
        metrics = await scheduler.signal_generator.performance.calculate_metrics(
            period_days=period_days
        )
        
        summary = scheduler.signal_generator.performance.format_summary(metrics)
        
        text = f"<b>📊 ПРОИЗВОДИТЕЛЬНОСТЬ</b>\n"
        text += f"<i>Период: {period_days} дней</i>\n\n"
        text += f"<pre>{summary}</pre>\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /signal <ASSET>"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.trading_enabled:
            await update.message.reply_text("❌ Trading system отключен")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ Укажите актив\n\nПример: /signal BTC")
            return
        
        asset = context.args[0].upper()
        
        await update.message.reply_text(f"🔄 Генерация сигнала для {asset}...")
        
        async with aiohttp.ClientSession() as session:
            price_data = await scheduler._fetch_ohlcv(asset, session)
            
            if price_data is None or len(price_data) < 50:
                await update.message.reply_text(f"❌ Недостаточно данных для {asset}")
                return
            
            signal = await scheduler.signal_generator.generate_signal(
                asset=asset,
                price_data=price_data,
                session=session
            )
            
            if not signal:
                await update.message.reply_text(f"❌ Не удалось сгенерировать сигнал")
                return
            
            msg = scheduler.signal_generator.format_signal_message(signal)
            await send_long_message(update, msg)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_close_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /close <position_id>"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.trading_enabled:
            await update.message.reply_text("❌ Trading system отключен")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Укажите ID позиции\n\n"
                "Пример: /close BTC_long_20241106\n"
                "Посмотреть ID: /positions"
            )
            return
        
        position_id = context.args[0]
        
        position = scheduler.signal_generator.positions.get_position(position_id)
        
        if not position:
            await update.message.reply_text(f"❌ Позиция не найдена")
            return
        
        await update.message.reply_text(f"🔄 Закрываю позицию...")
        
        exit_price = position.current_price or position.entry_price
        
        closed = await scheduler.signal_generator.positions.close_position(
            position_id,
            exit_price,
            reason="manual"
        )
        
        if closed:
            pnl_emoji = "🟢" if closed.realized_pnl_usd > 0 else "🔴"
            
            text = f"{pnl_emoji} <b>Позиция закрыта</b>\n\n"
            text += f"<b>{closed.asset}</b>\n"
            text += f"P&L: {format_number(closed.realized_pnl_usd)}\n"
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Ошибка закрытия")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /trades [days]"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.trading_enabled:
            await update.message.reply_text("❌ Trading system отключен")
            return
        
        period_days = 7
        if context.args and len(context.args) > 0:
            try:
                period_days = int(context.args[0])
                period_days = max(1, min(90, period_days))
            except ValueError:
                pass
        
        closed_positions = await scheduler.signal_generator.positions.get_closed_positions(
            limit=100
        )
        
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        recent_trades = [p for p in closed_positions if p.closed_at >= cutoff]
        
        if not recent_trades:
            await update.message.reply_text(f"📊 Нет сделок за {period_days} дней")
            return
        
        text = f"<b>📜 ИСТОРИЯ СДЕЛОК ({period_days}д)</b>\n\n"
        
        total_pnl = sum(p.realized_pnl_usd for p in recent_trades)
        winning = [p for p in recent_trades if p.realized_pnl_usd > 0]
        
        text += f"<b>Сделок:</b> {len(recent_trades)}\n"
        text += f"<b>Прибыльных:</b> {len(winning)} ({len(winning)/len(recent_trades)*100:.1f}%)\n"
        text += f"<b>P&L:</b> {format_number(total_pnl)}\n\n"
        
        for i, trade in enumerate(recent_trades[:10], 1):
            pnl_emoji = "🟢" if trade.realized_pnl_usd > 0 else "🔴"
            
            text += f"{pnl_emoji} <b>{trade.asset}</b>\n"
            text += f"P&L: {format_number(trade.realized_pnl_usd)}\n\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


__all__ = [
    'cmd_positions',
    'cmd_performance',
    'cmd_signal',
    'cmd_close_position',
    'cmd_trades'
]