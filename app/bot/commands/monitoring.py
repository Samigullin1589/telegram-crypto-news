# app/bot/commands/monitoring.py
"""
Whale monitoring commands
"""

import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin, send_long_message, format_duration, format_number


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    
    try:
        from app.scheduler import scheduler
        
        stats = scheduler.stats
        now = datetime.utcnow()
        
        text = "<b>📊 СТАТУС СИСТЕМЫ</b>\n"
        text += f"<i>{now.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>\n\n"
        
        uptime = (now - stats['start_time']).total_seconds()
        text += f"⏱️  <b>Uptime:</b> {format_duration(uptime)}\n\n"
        
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"• События собрано: {stats['events_collected']}\n"
        text += f"• Прошло фильтры: {stats['events_qualified']}\n"
        text += f"• Опубликовано: {stats['events_published']}\n"
        
        if scheduler.trading_enabled:
            text += f"\n<b>📈 TRADING SYSTEM</b>\n"
            text += f"• Сигналов сгенерировано: {stats.get('trading_signals_generated', 0)}\n"
            
            try:
                positions_summary = scheduler.signal_generator.positions.get_summary()
                text += f"• Открытых позиций: {positions_summary['total_open']}\n"
                text += f"• Unrealized P&L: {format_number(positions_summary['total_unrealized_pnl_usd'])}\n"
            except:
                pass
        else:
            text += f"\n<b>📈 TRADING SYSTEM</b>\n• Status: ❌ Отключен\n"
        
        text += f"\n<b>💚 HEALTH</b>\n"
        text += f"• Ошибок: {stats['errors']}\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /wallets"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.wallet_db:
            await update.message.reply_text("❌ Wallet database не инициализирована")
            return
        
        active_wallets = scheduler.wallet_db.get_active_wallets()
        
        if not active_wallets:
            await update.message.reply_text("📊 Нет активных кошельков")
            return
        
        sorted_wallets = sorted(
            active_wallets,
            key=lambda w: w.get('score', 50),
            reverse=True
        )
        
        text = f"<b>💰 ОТСЛЕЖИВАЕМЫЕ КОШЕЛЬКИ</b>\n\n"
        text += f"Всего активных: {len(active_wallets)}\n\n"
        
        for i, wallet in enumerate(sorted_wallets[:20], 1):
            score = wallet.get('score', 50)
            roi_30d = wallet.get('roi_30d', 0)
            win_rate = wallet.get('win_rate', 0)
            
            score_emoji = "🏆" if score >= 80 else "⭐" if score >= 60 else "📊"
            
            text += f"{score_emoji} <b>#{i}</b>\n"
            text += f"<code>{wallet['address'][:10]}...{wallet['address'][-6:]}</code>\n"
            text += f"Chain: {wallet['chain']} | Score: {score}\n"
            text += f"ROI 30d: {roi_30d:+.1%} | Win Rate: {win_rate:.1%}\n\n"
        
        if len(active_wallets) > 20:
            text += f"<i>... и ещё {len(active_wallets) - 20} кошельков</i>\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /whales"""
    
    try:
        from app.scheduler import scheduler
        
        text = f"<b>🐋 ПОСЛЕДНИЕ КРУПНЫЕ ПЕРЕМЕЩЕНИЯ</b>\n\n"
        
        if scheduler.publication_queue:
            text += f"В очереди: {len(scheduler.publication_queue)}\n\n"
            
            for i, item in enumerate(scheduler.publication_queue[:5], 1):
                event = item['event']
                verdict = item['verdict']
                confidence = item['confidence']
                
                text += f"<b>#{i} {event.asset}</b>\n"
                text += f"Amount: {format_number(event.amount_usd)}\n"
                text += f"Verdict: {verdict.upper()} ({confidence}%)\n\n"
        else:
            text += "📊 Очередь пуста\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /discover"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.smart_discovery:
            await update.message.reply_text("❌ Smart Discovery не инициализирован")
            return
        
        await update.message.reply_text("🔍 Запускаю поиск...")
        
        start_time = datetime.utcnow()
        
        async with scheduler.smart_discovery:
            wallets = await scheduler.smart_discovery.discover_new_wallets()
        
        added_count = 0
        for wallet_stats in wallets:
            if scheduler.wallet_db.add_wallet(wallet_stats):
                added_count += 1
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        text = f"✅ <b>Поиск завершён за {elapsed:.1f}с</b>\n\n"
        text += f"Найдено: {len(wallets)}\n"
        text += f"Добавлено новых: {added_count}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


__all__ = ['cmd_status', 'cmd_wallets', 'cmd_whales', 'cmd_discover']