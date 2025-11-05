"""
TELEGRAM BOT - Production-Ready Integration Layer
Команды управления для Whale Monitoring и Trading System

PRODUCTION FEATURES:
✅ Whale Monitoring Commands
✅ Trading System Commands  
✅ Position Management
✅ Performance Analytics
✅ Manual Signal Generation
✅ System Control
✅ Configuration Management
✅ Real-time Status Updates
✅ Multi-level Help System
✅ Admin Access Control
✅ Error Recovery
✅ Rate Limiting
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

from app import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_CHAT_ID,
    TELEGRAM_CHANNEL_ID,
    config
)

_application = None
_bot = None
_handlers_registered = False

def get_application():
    """Получить или создать единственный экземпляр application"""
    global _application, _bot
    if _application is None:
        _application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _bot = _application.bot
        print("✅ [BOT] Telegram bot initialized")
    return _application

def get_bot():
    """Получить bot instance"""
    global _bot
    if _bot is None:
        get_application()
    return _bot

application = get_application()
bot = get_bot()

__all__ = [
    'application',
    'bot', 
    'get_application',
    'get_bot',
    'register_handlers',
    'cmd_start',
    'cmd_help',
    'cmd_menu',
    'cmd_status',
    'cmd_positions',
    'cmd_performance',
    'cmd_signal',
    'cmd_close_position',
    'cmd_trades',
    'cmd_wallets',
    'cmd_whales',
    'cmd_discover',
    'cmd_config',
    'cmd_thresholds',
    'cmd_regime',
    'cmd_analytics',
    'cmd_sentiment',
    'cmd_pause',
    'cmd_resume',
    'cmd_logs',
    'cmd_admin'
]


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    try:
        admin_id = int(ADMIN_CHAT_ID) if isinstance(ADMIN_CHAT_ID, str) else ADMIN_CHAT_ID
        return user_id == admin_id
    except (ValueError, TypeError):
        return False


async def send_long_message(update: Update, text: str, parse_mode: str = 'HTML'):
    """
    Отправка длинного сообщения с автоматическим разбиением
    Telegram лимит: 4096 символов
    """
    
    if len(text) <= 4000:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return
    
    parts = []
    current_part = ""
    
    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 > 4000:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    
    if current_part:
        parts.append(current_part)
    
    for i, part in enumerate(parts):
        if i == 0:
            await update.message.reply_text(f"{part}\n\n<i>... продолжение {i+1}/{len(parts)}</i>", parse_mode=parse_mode)
        else:
            await update.message.reply_text(f"<i>Часть {i+1}/{len(parts)}</i>\n\n{part}", parse_mode=parse_mode)
        await asyncio.sleep(0.5)


def format_duration(seconds: float) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{int(seconds)}с"
    elif seconds < 3600:
        return f"{int(seconds/60)}м"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}ч"
    else:
        return f"{seconds/86400:.1f}д"


def format_number(num: float, decimals: int = 2) -> str:
    """Форматирование чисел с разделителями"""
    if abs(num) >= 1_000_000_000:
        return f"${num/1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"${num/1_000_000:.2f}M"
    elif abs(num) >= 1_000:
        return f"${num/1_000:.2f}K"
    else:
        return f"${num:,.{decimals}f}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /start
    Приветственное сообщение и главное меню
    """
    
    user = update.effective_user
    
    text = f"""
👋 <b>Привет, {user.first_name}!</b>

🐋 <b>Whale Monitor & Trading Bot</b>

Я помогаю отслеживать крупные перемещения криптовалют и генерировать торговые сигналы на основе:
- Технического анализа (50+ индикаторов)
- Фундаментального анализа
- Hot wallet мониторинга
- ML предсказаний

<b>📋 Основные команды:</b>
/help - Полный список команд
/status - Текущий статус системы
/menu - Главное меню

<b>🔐 Админ команды:</b>
/admin - Панель управления (только для администратора)
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("💼 Позиции", callback_data="positions")
        ],
        [
            InlineKeyboardButton("📈 Перформанс", callback_data="performance"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ]
    
    if is_admin(user.id):
        keyboard.append([
            InlineKeyboardButton("🔧 Админ панель", callback_data="admin_panel")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /help
    Полная справка по всем командам
    """
    
    user_id = update.effective_user.id
    
    text = """
<b>📚 СПРАВКА ПО КОМАНДАМ</b>

<b>🌊 WHALE MONITORING</b>
/status - Статус системы и статистика
/wallets - Список отслеживаемых кошельков
/whales - Последние крупные перемещения
/discover - Запустить поиск новых успешных трейдеров

<b>📈 TRADING SYSTEM</b>
/positions - Открытые торговые позиции
/performance [days] - Статистика торговли (по умолчанию 30д)
/signal <ASSET> - Сгенерировать сигнал вручную
/close <position_id> - Закрыть позицию вручную
/trades [days] - История сделок

<b>⚙️ НАСТРОЙКИ</b>
/config - Текущая конфигурация
/thresholds - Адаптивные пороги
/regime - Режим рынка

<b>🔧 УПРАВЛЕНИЕ</b>
/pause - Приостановить публикацию
/resume - Возобновить публикацию
/restart - Перезапустить систему
/logs [lines] - Последние логи

<b>📊 АНАЛИТИКА</b>
/analytics - Аналитика по активам
/correlations - Корреляции активов
/sentiment <ASSET> - Sentiment анализ актива

<b>💡 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:</b>
/signal BTC - Сигнал по Bitcoin
/performance 7 - Статистика за 7 дней
/close BTC_long_20241031 - Закрыть конкретную позицию
/trades 14 - Сделки за 14 дней

<b>⚠️ ДИСКЛЕЙМЕР:</b>
Все сигналы предоставляются исключительно в информационных целях и НЕ являются финансовыми рекомендациями.
"""
    
    if not is_admin(user_id):
        text += "\n\n<i>🔒 Некоторые команды доступны только администратору</i>"
    
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /menu
    Интерактивное главное меню
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("💼 Позиции", callback_data="positions")
        ],
        [
            InlineKeyboardButton("📈 Перформанс", callback_data="performance"),
            InlineKeyboardButton("💰 Кошельки", callback_data="wallets")
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="menu")
        ]
    ]
    
    if is_admin(update.effective_user.id):
        keyboard.append([
            InlineKeyboardButton("🔧 Админ", callback_data="admin_panel")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "<b>📋 ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:"
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /status
    Полный статус системы
    """
    
    try:
        from app.scheduler import scheduler
        
        stats = scheduler.stats
        now = datetime.utcnow()
        
        text = "<b>📊 СТАТУС СИСТЕМЫ</b>\n"
        text += f"<i>{now.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>\n\n"
        
        uptime = (now - stats['start_time']).total_seconds()
        text += f"⏱️ <b>Uptime:</b> {format_duration(uptime)}\n\n"
        
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"• События собрано: {stats['events_collected']}\n"
        text += f"• Прошло фильтры: {stats['events_qualified']}\n"
        text += f"• Опубликовано: {stats['events_published']}\n"
        
        if stats['events_successful'] + stats['events_failed'] > 0:
            total = stats['events_successful'] + stats['events_failed']
            accuracy = (stats['events_successful'] / total) * 100
            text += f"• Точность: {accuracy:.1f}% ({stats['events_successful']}/{total})\n"
        
        if scheduler.trading_enabled:
            text += f"\n<b>📈 TRADING SYSTEM</b>\n"
            text += f"• Сигналов сгенерировано: {stats.get('trading_signals_generated', 0)}\n"
            text += f"• Сигналов отправлено: {stats.get('trading_signals_sent', 0)}\n"
            
            try:
                positions_summary = scheduler.signal_generator.positions.get_summary()
                text += f"• Открытых позиций: {positions_summary['total_open']}\n"
                text += f"• Unrealized P&L: {format_number(positions_summary['total_unrealized_pnl_usd'])}\n"
                
                if stats.get('last_trading_signal'):
                    elapsed = (now - stats['last_trading_signal']).total_seconds()
                    text += f"• Последний сигнал: {format_duration(elapsed)} назад\n"
            except:
                pass
        else:
            text += f"\n<b>📈 TRADING SYSTEM</b>\n"
            text += f"• Status: ❌ Отключен\n"
        
        if scheduler.adaptive_thresholds:
            adaptive_stats = scheduler.adaptive_thresholds.get_stats()
            text += f"\n<b>🧠 АДАПТИВНАЯ СИСТЕМА</b>\n"
            text += f"• Режим рынка: {adaptive_stats['regime'].upper()}\n"
            text += f"• Сигналов отслежено: {adaptive_stats['signals_tracked']}\n"
            if adaptive_stats['signals_tracked'] > 0:
                text += f"• Точность: {adaptive_stats['accuracy']:.1%}\n"
        
        if scheduler.wallet_db:
            active_wallets = len(scheduler.wallet_db.get_active_wallets())
            total_wallets = len(scheduler.wallet_db.wallets)
            text += f"\n<b>💾 БАЗА КОШЕЛЬКОВ</b>\n"
            text += f"• Активных: {active_wallets}\n"
            text += f"• Всего: {total_wallets}\n"
            text += f"• Найдено: {stats['wallets_discovered']}\n"
            text += f"• Удалено: {stats['wallets_removed']}\n"
        
        if scheduler.chains_enabled:
            chains_events = stats.get('chains_events', {})
            if chains_events:
                text += f"\n<b>🌐 MULTI-CHAIN</b>\n"
                for chain, count in sorted(chains_events.items(), key=lambda x: x[1], reverse=True)[:5]:
                    text += f"• {chain}: {count} событий\n"
        
        if scheduler.analytics_enabled:
            text += f"\n<b>📊 ANALYTICS</b>\n"
            text += f"• Вызовов: {stats.get('analytics_calls', 0)}\n"
        
        text += f"\n<b>💚 HEALTH</b>\n"
        
        if stats['last_cycle_time']:
            silence = (now - stats['last_cycle_time']).total_seconds()
            if silence < 300:
                text += f"• Последний цикл: ✅ {int(silence)}с назад\n"
            else:
                text += f"• Последний цикл: ⚠️ {int(silence/60)}м назад\n"
        
        text += f"• Ошибок: {stats['errors']}\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка получения статуса: {e}")
        traceback.print_exc()


async def cmd_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /wallets
    Список отслеживаемых кошельков
    """
    
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
        
        sorted_wallets = sorted(active_wallets, key=lambda w: w.get('score', 50), reverse=True)
        
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
            text += f"ROI 30d: {roi_30d:+.1%} | Win Rate: {win_rate:.1%}\n"
            
            if wallet.get('specialization'):
                text += f"Specialization: {wallet['specialization']}\n"
            
            text += "\n"
        
        if len(active_wallets) > 20:
            text += f"<i>... и ещё {len(active_wallets) - 20} кошельков</i>\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /whales
    Последние крупные перемещения
    """
    
    try:
        from app.scheduler import scheduler
        
        recent_count = 10
        
        text = f"<b>🐋 ПОСЛЕДНИЕ КРУПНЫЕ ПЕРЕМЕЩЕНИЯ</b>\n\n"
        
        if scheduler.publication_queue:
            text += f"В очереди публикации: {len(scheduler.publication_queue)}\n\n"
            
            for i, item in enumerate(scheduler.publication_queue[:5], 1):
                event = item['event']
                verdict = item['verdict']
                confidence = item['confidence']
                
                text += f"<b>#{i} {event.asset}</b>\n"
                text += f"Amount: {format_number(event.amount_usd)}\n"
                text += f"Verdict: {verdict.upper()} ({confidence}%)\n"
                text += f"Priority: {item['priority']:.1f}\n\n"
        else:
            text += "📊 Очередь публикации пуста\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /discover
    Запустить поиск новых успешных трейдеров
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.smart_discovery:
            await update.message.reply_text("❌ Smart Discovery не инициализирован")
            return
        
        await update.message.reply_text("🔍 Запускаю поиск успешных трейдеров...")
        
        start_time = datetime.utcnow()
        
        async with scheduler.smart_discovery:
            wallets = await scheduler.smart_discovery.discover_new_wallets()
        
        added_count = 0
        for wallet_stats in wallets:
            if scheduler.wallet_db.add_wallet(wallet_stats):
                added_count += 1
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        text = f"✅ <b>Поиск завершён за {elapsed:.1f}с</b>\n\n"
        text += f"Найдено: {len(wallets)} кошельков\n"
        text += f"Добавлено новых: {added_count}\n"
        text += f"Всего в базе: {len(scheduler.wallet_db.get_active_wallets())} активных"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /positions
    Показать открытые торговые позиции
    """
    
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
            
            if p.stop_loss:
                sl_dist = abs((p.current_price - p.stop_loss) / p.current_price * 100)
                text += f"Stop-Loss: ${p.stop_loss:,.2f} ({sl_dist:.1f}% away)\n"
            
            if p.take_profit:
                tp_dist = abs((p.take_profit - p.current_price) / p.current_price * 100)
                text += f"Take-Profit: ${p.take_profit:,.2f} ({tp_dist:.1f}% away)\n"
            
            if hasattr(p, 'opened_at'):
                duration = (datetime.utcnow() - p.opened_at).total_seconds()
                text += f"Duration: {format_duration(duration)}\n"
            
            text += f"ID: <code>{p.position_id}</code>\n"
            text += "\n"
        
        summary = scheduler.signal_generator.positions.get_summary()
        text += f"<b>📊 ИТОГО</b>\n"
        text += f"Позиций: {summary['total_open']}\n"
        text += f"Капитал: {format_number(summary['total_amount_usd'])}\n"
        text += f"Unrealized P&L: {format_number(summary['total_unrealized_pnl_usd'])}\n"
        
        if summary['total_amount_usd'] > 0:
            roi = (summary['total_unrealized_pnl_usd'] / summary['total_amount_usd']) * 100
            text += f"ROI: {roi:+.2f}%\n"
        
        text += "\n<i>⚠️ NOT financial advice</i>"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /performance [days]
    Показать статистику торговли за N дней
    """
    
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
                await update.message.reply_text("❌ Неверный формат. Используйте: /performance [days]")
                return
        
        await update.message.reply_text(f"📊 Рассчитываю статистику за {period_days} дней...")
        
        metrics = await scheduler.signal_generator.performance.calculate_metrics(period_days=period_days)
        
        summary = scheduler.signal_generator.performance.format_summary(metrics)
        
        text = f"<b>📊 ПРОИЗВОДИТЕЛЬНОСТЬ TRADING SYSTEM</b>\n"
        text += f"<i>Период: {period_days} дней</i>\n\n"
        text += f"<pre>{summary}</pre>\n\n"
        text += "<i>⚠️ Past performance does not guarantee future results</i>"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /signal <ASSET>
    Сгенерировать торговый сигнал для актива вручную
    """
    
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
                "❌ Укажите актив\n\n"
                "Пример: /signal BTC"
            )
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
                await update.message.reply_text(f"❌ Не удалось сгенерировать сигнал для {asset}")
                return
            
            msg = scheduler.signal_generator.format_signal_message(signal)
            
            await send_long_message(update, msg)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_close_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /close <position_id>
    Закрыть позицию вручную
    """
    
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
                "Пример: /close BTC_long_20241031_120000\n\n"
                "Посмотреть ID позиций: /positions"
            )
            return
        
        position_id = context.args[0]
        
        position = scheduler.signal_generator.positions.get_position(position_id)
        
        if not position:
            await update.message.reply_text(f"❌ Позиция {position_id} не найдена")
            return
        
        exit_price = position.current_price or position.entry_price
        
        await update.message.reply_text(f"🔄 Закрываю позицию {position.asset}...")
        
        closed = await scheduler.signal_generator.positions.close_position(
            position_id,
            exit_price,
            reason="manual"
        )
        
        if closed:
            pnl_emoji = "🟢" if closed.realized_pnl_usd > 0 else "🔴"
            
            text = f"{pnl_emoji} <b>Позиция закрыта</b>\n\n"
            text += f"<b>{closed.asset}</b> ({closed.position_type.upper()})\n"
            text += f"Entry: ${closed.entry_price:,.2f}\n"
            text += f"Exit: ${closed.exit_price:,.2f}\n"
            text += f"P&L: {format_number(closed.realized_pnl_usd)} ({closed.realized_pnl_pct:+.2f}%)\n"
            text += f"Duration: {format_duration((closed.closed_at - closed.opened_at).total_seconds())}\n"
            text += f"Reason: {closed.close_reason}"
            
            await update.message.reply_text(text, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Ошибка закрытия позиции")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /trades [days]
    История закрытых сделок
    """
    
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
        
        closed_positions = await scheduler.signal_generator.positions.get_closed_positions(limit=100)
        
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        recent_trades = [p for p in closed_positions if p.closed_at >= cutoff]
        
        if not recent_trades:
            await update.message.reply_text(f"📊 Нет закрытых сделок за {period_days} дней")
            return
        
        text = f"<b>📜 ИСТОРИЯ СДЕЛОК ({period_days}д)</b>\n\n"
        
        total_pnl = sum(p.realized_pnl_usd for p in recent_trades)
        winning = [p for p in recent_trades if p.realized_pnl_usd > 0]
        
        text += f"<b>Итого сделок:</b> {len(recent_trades)}\n"
        text += f"<b>Прибыльных:</b> {len(winning)} ({len(winning)/len(recent_trades)*100:.1f}%)\n"
        text += f"<b>Total P&L:</b> {format_number(total_pnl)}\n\n"
        
        text += "<b>Последние сделки:</b>\n\n"
        
        for i, trade in enumerate(recent_trades[:10], 1):
            pnl_emoji = "🟢" if trade.realized_pnl_usd > 0 else "🔴"
            
            text += f"{pnl_emoji} <b>#{i} {trade.asset}</b>\n"
            text += f"Type: {trade.position_type.upper()}\n"
            text += f"P&L: {format_number(trade.realized_pnl_usd)} ({trade.realized_pnl_pct:+.2f}%)\n"
            text += f"Duration: {format_duration((trade.closed_at - trade.opened_at).total_seconds())}\n"
            text += f"Closed: {trade.closed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        if len(recent_trades) > 10:
            text += f"<i>... и ещё {len(recent_trades) - 10} сделок</i>"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /config
    Текущая конфигурация системы
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        from app import settings
        
        text = "<b>⚙️ КОНФИГУРАЦИЯ СИСТЕМЫ</b>\n\n"
        
        text += "<b>🔧 GENERAL</b>\n"
        assets_mode = getattr(config, 'ASSETS', 'All')
        text += f"Assets Mode: {assets_mode}\n"
        text += f"Posts per Hour: {config.whale.posts_per_hour_cap}\n"
        text += f"Poll Interval: {config.whale.poll_seconds}s\n"
        images_enabled = getattr(config.news, 'image_download_enabled', True)
        text += f"Images: {'✅' if images_enabled else '❌'}\n\n"
        
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"Smart Discovery: {'✅' if config.smart_discovery.enabled else '❌'}\n"
        text += f"Adaptive Thresholds: {'✅' if config.adaptive_thresholds.enabled else '❌'}\n"
        text += f"Performance Tracking: {'✅' if config.performance.tracking_enabled else '❌'}\n"
        text += f"Validation: {'✅' if config.validation.enabled else '❌'}\n\n"
        
        if scheduler.trading_enabled:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += "Status: ✅ Enabled\n"
            signal_interval = getattr(settings, 'TRADING_SIGNAL_INTERVAL_HOURS', 1)
            text += f"Signal Interval: {signal_interval}h\n"
            position_update = getattr(settings, 'POSITION_UPDATE_INTERVAL_SECONDS', 60)
            text += f"Position Update: {position_update}s\n"
            
            monitored = getattr(settings, 'TRADING_MONITORED_ASSETS', [])
            text += f"Monitored Assets: {len(monitored)}\n"
        else:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += "Status: ❌ Disabled\n"
        
        text += "\n"
        
        if scheduler.chains_enabled:
            text += "<b>🌐 MULTI-CHAIN</b>\n"
            text += "Status: ✅ Enabled\n"
            text += f"Chains: {', '.join(scheduler.supported_chains)}\n\n"
        
        if scheduler.analytics_enabled:
            text += "<b>📊 ANALYTICS</b>\n"
            text += "Status: ✅ Enabled\n\n"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /thresholds
    Текущие адаптивные пороги
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.adaptive_thresholds:
            await update.message.reply_text("❌ Adaptive thresholds не инициализированы")
            return
        
        stats = scheduler.adaptive_thresholds.get_stats()
        thresholds = stats['current_thresholds']
        
        text = "<b>⚙️ АДАПТИВНЫЕ ПОРОГИ</b>\n\n"
        
        text += f"<b>Режим рынка:</b> {stats['regime'].upper()}\n"
        text += f"<b>Отслежено сигналов:</b> {stats['signals_tracked']}\n"
        if stats['signals_tracked'] > 0:
            text += f"<b>Точность:</b> {stats['accuracy']:.1%}\n"
        text += "\n"
        
        text += "<b>Текущие пороги:</b>\n"
        text += f"• Min Confidence: ≥{thresholds['min_confidence']}\n"
        text += f"• Min Size Rel: ≥{thresholds['min_size_rel']:.2%}\n"
        text += f"• Min Volume 24h: ≥${thresholds['min_volume_24h']:,}\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_regime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /regime
    Текущий режим рынка
    """
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.adaptive_thresholds:
            await update.message.reply_text("❌ Adaptive system не инициализирована")
            return
        
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24h_change": "true",
                "include_7d_change": "true"
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    btc_24h = data["bitcoin"].get("usd_24h_change", 0)
                    btc_7d = data["bitcoin"].get("usd_7d_change", 0)
                else:
                    await update.message.reply_text("❌ Не удалось получить данные рынка")
                    return
        
        regime = scheduler.adaptive_thresholds.market_regime
        
        regime_emoji = {
            "bull": "🐂",
            "bear": "🐻",
            "sideways": "🦀"
        }
        
        text = f"<b>📊 РЕЖИМ РЫНКА</b>\n\n"
        text += f"{regime_emoji.get(regime, '📊')} <b>{regime.upper()}</b>\n\n"
        text += f"<b>Bitcoin (7d):</b> {btc_7d:+.2f}%\n"
        text += f"<b>Bitcoin (24h):</b> {btc_24h:+.2f}%\n\n"
        
        text += "<b>Критерии:</b>\n"
        max_threshold = getattr(config.adaptive_thresholds, 'max_threshold', 70)
        min_threshold = getattr(config.adaptive_thresholds, 'min_threshold', 30)
        text += f"• Bull: >+{max_threshold}% (7d)\n"
        text += f"• Bear: <{min_threshold}% (7d)\n"
        text += f"• Sideways: между ними\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /analytics
    Общая аналитика по активам
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not scheduler.analytics_enabled:
            await update.message.reply_text("❌ Analytics engine не инициализирован")
            return
        
        from app.analytics import get_analytics_engine
        
        analytics = get_analytics_engine()
        
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
        
        text += "\n<b>🎯 КОРРЕЛЯЦИИ</b>\n"
        try:
            correlations = analytics.get_correlation_matrix(['BTC', 'ETH', 'BNB', 'SOL'])
            text += "<i>Доступно через /correlations</i>\n"
        except:
            text += "Данные недоступны\n"
        
        await send_long_message(update, text)

        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /sentiment <ASSET>
    Sentiment анализ актива
    """
    
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
            
            text = f"<b>📊 SENTIMENT АНАЛИЗ: {asset}</b>\n\n"
            
            text += f"<b>Общий sentiment:</b> {sentiment_data.get('overall', 'Neutral')}\n"
            text += f"<b>Score:</b> {sentiment_data.get('score', 0):.2f}/100\n\n"
            
            text += "<b>Источники:</b>\n"
            text += f"• News: {sentiment_data.get('news_sentiment', 'N/A')}\n"
            text += f"• Social: {sentiment_data.get('social_sentiment', 'N/A')}\n"
            text += f"• Technical: {sentiment_data.get('technical_sentiment', 'N/A')}\n\n"
            
            text += f"<b>Рекомендация:</b> {sentiment_data.get('recommendation', 'Нейтральная')}\n"
            
            if sentiment_data.get('key_factors'):
                text += "\n<b>Ключевые факторы:</b>\n"
                for factor in sentiment_data['key_factors'][:5]:
                    text += f"• {factor}\n"
            
            await update.message.reply_text(text, parse_mode='HTML')
            
        except Exception as e:
            text = f"❌ Не удалось получить sentiment для {asset}\n\n"
            text += "<i>Доступные активы: BTC, ETH, BNB, SOL, USDT</i>"
            await update.message.reply_text(text, parse_mode='HTML')

        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /pause
    Приостановить публикацию
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    try:
        from app.scheduler import scheduler
        
        if not hasattr(scheduler, 'paused'):
            scheduler.paused = False
        
        if scheduler.paused:
            await update.message.reply_text("⚠️ Система уже приостановлена")
            return
        
        scheduler.paused = True
        
        text = "⏸️ <b>СИСТЕМА ПРИОСТАНОВЛЕНА</b>\n\n"
        text += "• Публикация whale events: ⏸️ Остановлена\n"
        text += "• Публикация trading signals: ⏸️ Остановлена\n"
        text += "• Мониторинг: ✅ Продолжается\n\n"
        text += "<i>Используйте /resume для возобновления</i>"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /resume
    Возобновить публикацию
    """
    
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
        
        text = "▶️ <b>СИСТЕМА ВОЗОБНОВЛЕНА</b>\n\n"
        text += "• Публикация whale events: ✅ Активна\n"
        text += "• Публикация trading signals: ✅ Активна\n"
        text += "• Мониторинг: ✅ Активен\n\n"
        text += "<i>Система работает в обычном режиме</i>"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /logs [lines]
    Последние строки логов
    """
    
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
        
        import os
        from pathlib import Path
        
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
        except:
            log_text = "Ошибка чтения лог-файла"
        
        text = f"<b>📋 ПОСЛЕДНИЕ {len(recent_lines)} СТРОК ЛОГОВ</b>\n\n"
        text += f"<code>{log_text[-3500:]}</code>"
        
        await send_long_message(update, text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /admin
    Админ панель управления
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("💼 Позиции", callback_data="positions")
        ],
        [
            InlineKeyboardButton("📈 Перформанс", callback_data="performance"),
            InlineKeyboardButton("💰 Кошельки", callback_data="wallets")
        ],
        [
            InlineKeyboardButton("⚙️ Конфиг", callback_data="config"),
            InlineKeyboardButton("🎯 Пороги", callback_data="thresholds")
        ],
        [
            InlineKeyboardButton("🔍 Discovery", callback_data="discover"),
            InlineKeyboardButton("📊 Режим", callback_data="regime")
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="admin_panel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "<b>🔧 АДМИН ПАНЕЛЬ</b>\n\nВыберите действие:"
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


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
                "❌ Произошла ошибка при обработке команды. "
                "Попробуйте позже или обратитесь к администратору."
            )
        except:
            pass


def register_handlers():
    """Регистрация всех обработчиков команд"""
    
    global _handlers_registered
    
    if _handlers_registered:
        print("⚠️ [BOT] Handlers already registered, skipping")
        return
    
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
    
    _handlers_registered = True
    
    print("✅ [BOT] All handlers registered")
    print("   • General: 3 commands")
    print("   • Whale Monitoring: 4 commands")
    print("   • Trading System: 5 commands")
    print("   • Configuration: 3 commands")
    print("   • Analytics: 2 commands")
    print("   • Control: 3 commands")
    print("   • Admin: 1 command")


async def main():
    """Главная функция для standalone запуска бота"""
    
    print("\n" + "="*80)
    print("🤖 TELEGRAM BOT - STANDALONE MODE")
    print("="*80 + "\n")
    
    register_handlers()
    
    app = get_application()
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Bot is running...")
    print("Press Ctrl+C to stop\n")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n⏹️ Stopping bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("✅ Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())