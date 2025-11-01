"""
TELEGRAM BOT - Complete Integration Layer
Команды управления для Whale Monitoring и Trading System

ВОЗМОЖНОСТИ:
✅ Whale Monitoring Commands
✅ Trading System Commands  
✅ Position Management
✅ Performance Analytics
✅ Manual Signal Generation
✅ System Control (pause/resume)
✅ Configuration Management
✅ Real-time Status Updates
✅ Multi-level Help System
✅ Admin Access Control
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict
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

from app import settings

# ============================================================================
# BOT INITIALIZATION
# ============================================================================

# Создаем application
application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
bot = application.bot

print("✅ [BOT] Telegram bot initialized")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    try:
        admin_id = int(settings.ADMIN_CHAT_ID) if isinstance(settings.ADMIN_CHAT_ID, str) else settings.ADMIN_CHAT_ID
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
    
    # Разбиваем на части
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
    
    # Отправляем по частям
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


# ============================================================================
# GENERAL COMMANDS
# ============================================================================

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


# ============================================================================
# WHALE MONITORING COMMANDS
# ============================================================================

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
        
        # Uptime
        uptime = (now - stats['start_time']).total_seconds()
        text += f"⏱️ <b>Uptime:</b> {format_duration(uptime)}\n\n"
        
        # Whale Monitoring
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"• События собрано: {stats['events_collected']}\n"
        text += f"• Прошло фильтры: {stats['events_qualified']}\n"
        text += f"• Опубликовано: {stats['events_published']}\n"
        
        if stats['events_successful'] + stats['events_failed'] > 0:
            total = stats['events_successful'] + stats['events_failed']
            accuracy = (stats['events_successful'] / total) * 100
            text += f"• Точность: {accuracy:.1f}% ({stats['events_successful']}/{total})\n"
        
        # Trading System
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
        
        # Adaptive System
        if scheduler.adaptive_thresholds:
            adaptive_stats = scheduler.adaptive_thresholds.get_stats()
            text += f"\n<b>🧠 АДАПТИВНАЯ СИСТЕМА</b>\n"
            text += f"• Режим рынка: {adaptive_stats['regime'].upper()}\n"
            text += f"• Сигналов отслежено: {adaptive_stats['signals_tracked']}\n"
            if adaptive_stats['signals_tracked'] > 0:
                text += f"• Точность: {adaptive_stats['accuracy']:.1%}\n"
        
        # Wallet Database
        if scheduler.wallet_db:
            active_wallets = len(scheduler.wallet_db.get_active_wallets())
            total_wallets = len(scheduler.wallet_db.wallets)
            text += f"\n<b>💾 БАЗА КОШЕЛЬКОВ</b>\n"
            text += f"• Активных: {active_wallets}\n"
            text += f"• Всего: {total_wallets}\n"
            text += f"• Найдено: {stats['wallets_discovered']}\n"
            text += f"• Удалено: {stats['wallets_removed']}\n"
        
        # Multi-Chain
        if scheduler.chains_enabled:
            chains_events = stats.get('chains_events', {})
            if chains_events:
                text += f"\n<b>🌐 MULTI-CHAIN</b>\n"
                for chain, count in sorted(chains_events.items(), key=lambda x: x[1], reverse=True)[:5]:
                    text += f"• {chain}: {count} событий\n"
        
        # Analytics
        if scheduler.analytics_enabled:
            text += f"\n<b>📊 ANALYTICS</b>\n"
            text += f"• Вызовов: {stats.get('analytics_calls', 0)}\n"
        
        # System Health
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
        
        # Сортируем по score
        sorted_wallets = sorted(active_wallets, key=lambda w: w.get('score', 50), reverse=True)
        
        text = f"<b>💰 ОТСЛЕЖИВАЕМЫЕ КОШЕЛЬКИ</b>\n\n"
        text += f"Всего активных: {len(active_wallets)}\n\n"
        
        # Показываем топ-20
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
        
        # Получаем последние N событий из истории
        recent_count = 10
        
        text = f"<b>🐋 ПОСЛЕДНИЕ КРУПНЫЕ ПЕРЕМЕЩЕНИЯ</b>\n\n"
        
        # Пока что показываем статистику из очереди публикации
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


# ============================================================================
# TRADING SYSTEM COMMANDS
# ============================================================================

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
            
            # Duration
            if hasattr(p, 'opened_at'):
                duration = (datetime.utcnow() - p.opened_at).total_seconds()
                text += f"Duration: {format_duration(duration)}\n"
            
            text += f"ID: <code>{p.position_id}</code>\n"
            text += "\n"
        
        # Summary
        summary = scheduler.signal_generator.positions.get_summary()
        text += f"<b>📊 ИТОГО</b>\n"
        text += f"Позиций: {summary['total_open']}\n"
        text += f"Капитал: {format_number(summary['total_amount_usd'])}\n"
        text += f"Unrealized P&L: {format_number(summary['total_unrealized_pnl_usd'])}\n"
        
        # Performance snapshot
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
        
        # Парсим период
        period_days = 30
        if context.args and len(context.args) > 0:
            try:
                period_days = int(context.args[0])
                period_days = max(1, min(365, period_days))  # 1-365 дней
            except ValueError:
                await update.message.reply_text("❌ Неверный формат. Используйте: /performance [days]")
                return
        
        await update.message.reply_text(f"📊 Рассчитываю статистику за {period_days} дней...")
        
        # Получаем метрики
        metrics = await scheduler.signal_generator.performance.calculate_metrics(period_days=period_days)
        
        # Форматируем
        summary = scheduler.signal_generator.performance.format_summary(metrics)
        
        # Добавляем заголовок
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
        
        # Проверяем аргументы
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Укажите актив\n\n"
                "Пример: /signal BTC"
            )
            return
        
        asset = context.args[0].upper()
        
        await update.message.reply_text(f"🔄 Генерация сигнала для {asset}...")
        
        async with aiohttp.ClientSession() as session:
            # Получаем данные
            price_data = await scheduler._fetch_ohlcv(asset, session)
            
            if price_data is None or len(price_data) < 50:
                await update.message.reply_text(f"❌ Недостаточно данных для {asset}")
                return
            
            # Генерируем сигнал
            signal = await scheduler.signal_generator.generate_signal(
                asset=asset,
                price_data=price_data,
                session=session
            )
            
            if not signal:
                await update.message.reply_text(f"❌ Не удалось сгенерировать сигнал для {asset}")
                return
            
            # Форматируем
            msg = scheduler.signal_generator.format_signal_message(signal)
            
            # Отправляем
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
        
        # Проверяем аргументы
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Укажите ID позиции\n\n"
                "Пример: /close BTC_long_20241031_120000\n\n"
                "Посмотреть ID позиций: /positions"
            )
            return
        
        position_id = context.args[0]
        
        # Получаем позицию
        position = scheduler.signal_generator.positions.get_position(position_id)
        
        if not position:
            await update.message.reply_text(f"❌ Позиция {position_id} не найдена")
            return
        
        # Получаем текущую цену
        exit_price = position.current_price or position.entry_price
        
        await update.message.reply_text(f"🔄 Закрываю позицию {position.asset}...")
        
        # Закрываем
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
        
        # Парсим период
        period_days = 7
        if context.args and len(context.args) > 0:
            try:
                period_days = int(context.args[0])
                period_days = max(1, min(90, period_days))
            except ValueError:
                pass
        
        # Получаем закрытые позиции
        closed_positions = await scheduler.signal_generator.positions.get_closed_positions(limit=100)
        
        # Фильтруем по периоду
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        recent_trades = [p for p in closed_positions if p.closed_at >= cutoff]
        
        if not recent_trades:
            await update.message.reply_text(f"📊 Нет закрытых сделок за {period_days} дней")
            return
        
        text = f"<b>📜 ИСТОРИЯ СДЕЛОК ({period_days}д)</b>\n\n"
        
        # Статистика
        total_pnl = sum(p.realized_pnl_usd for p in recent_trades)
        winning = [p for p in recent_trades if p.realized_pnl_usd > 0]
        
        text += f"<b>Итого сделок:</b> {len(recent_trades)}\n"
        text += f"<b>Прибыльных:</b> {len(winning)} ({len(winning)/len(recent_trades)*100:.1f}%)\n"
        text += f"<b>Total P&L:</b> {format_number(total_pnl)}\n\n"
        
        # Последние 10 сделок
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


# ============================================================================
# CONFIGURATION COMMANDS
# ============================================================================

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
        
        text = "<b>⚙️ КОНФИГУРАЦИЯ СИСТЕМЫ</b>\n\n"
        
        # General
        text += "<b>🔧 GENERAL</b>\n"
        text += f"Assets Mode: {settings.ASSETS}\n"
        text += f"Posts per Hour: {settings.POSTS_PER_HOUR_CAP}\n"
        text += f"Poll Interval: {settings.POLL_SECONDS}s\n"
        text += f"Images: {'✅' if settings.ENABLE_IMAGES else '❌'}\n\n"
        
        # Whale Monitoring
        text += "<b>🐋 WHALE MONITORING</b>\n"
        text += f"Smart Discovery: {'✅' if settings.SMART_DISCOVERY_ENABLED else '❌'}\n"
        text += f"Adaptive Thresholds: {'✅' if settings.ADAPTIVE_THRESHOLDS_ENABLED else '❌'}\n"
        text += f"Performance Tracking: {'✅' if settings.PERFORMANCE_TRACKING_ENABLED else '❌'}\n"
        text += f"Validation: {'✅' if settings.VALIDATION_ENABLED else '❌'}\n\n"
        
        # Trading System
        if scheduler.trading_enabled:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += f"Status: ✅ Enabled\n"
            text += f"Signal Interval: {getattr(settings, 'TRADING_SIGNAL_INTERVAL_HOURS', 1)}h\n"
            text += f"Position Update: {getattr(settings, 'POSITION_UPDATE_INTERVAL_SECONDS', 60)}s\n"
            
            monitored = getattr(settings, 'TRADING_MONITORED_ASSETS', [])
            text += f"Monitored Assets: {len(monitored)}\n"
        else:
            text += "<b>📈 TRADING SYSTEM</b>\n"
            text += f"Status: ❌ Disabled\n"
        
        text += "\n"
        
        # Multi-Chain
        if scheduler.chains_enabled:
            text += f"<b>🌐 MULTI-CHAIN</b>\n"
            text += f"Status: ✅ Enabled\n"
            text += f"Chains: {', '.join(scheduler.supported_chains)}\n\n"
        
        # Analytics
        if scheduler.analytics_enabled:
            text += f"<b>📊 ANALYTICS</b>\n"
            text += f"Status: ✅ Enabled\n\n"
        
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
        
        # Получаем данные BTC
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
        
        # Критерии
        text += "<b>Критерии:</b>\n"
        text += f"• Bull: >+{settings.ADAPTIVE_BULL_THRESHOLD}% (7d)\n"
        text += f"• Bear: <{settings.ADAPTIVE_BEAR_THRESHOLD}% (7d)\n"
        text += f"• Sideways: между ними\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        traceback.print_exc()


# ============================================================================
# ANALYTICS COMMANDS
# ============================================================================

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
        
        await update.message.reply_text("📊 Аналитика в разработке...")
        
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
        
        # Будущая реализация
        await update.message.reply_text("Sentiment анализ в разработке...")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ============================================================================
# CONTROL COMMANDS
# ============================================================================

async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /pause
    Приостановить публикацию
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    await update.message.reply_text("⏸️ Функция паузы в разработке")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /resume
    Возобновить публикацию
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    await update.message.reply_text("▶️ Функция возобновления в разработке")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /logs [lines]
    Последние строки логов
    """
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора")
        return
    
    await update.message.reply_text("📋 Функция логов в разработке")


# ============================================================================
# ADMIN PANEL
# ============================================================================

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


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline кнопок"""
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Создаём фейковый update для переиспользования команд
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


# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    
    print(f"❌ [BOT] Exception while handling update {update}:")
    traceback.print_exc()
    
    # Логируем ошибку
    if context.error:
        print(f"Error: {context.error}")
    
    # Пытаемся уведомить пользователя
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке команды. "
                "Попробуйте позже или обратитесь к администратору."
            )
        except:
            pass


# ============================================================================
# HANDLER REGISTRATION
# ============================================================================

_handlers_registered = False

def register_handlers():
    """Регистрация всех обработчиков команд"""
    
    global _handlers_registered
    
    if _handlers_registered:
        print("⚠️ [BOT] Handlers already registered, skipping")
        return
    
    # General commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("menu", cmd_menu))
    
    # Whale monitoring
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("wallets", cmd_wallets))
    application.add_handler(CommandHandler("whales", cmd_whales))
    application.add_handler(CommandHandler("discover", cmd_discover))
    
    # Trading system
    application.add_handler(CommandHandler("positions", cmd_positions))
    application.add_handler(CommandHandler("performance", cmd_performance))
    application.add_handler(CommandHandler("signal", cmd_signal))
    application.add_handler(CommandHandler("close", cmd_close_position))
    application.add_handler(CommandHandler("trades", cmd_trades))
    
    # Configuration
    application.add_handler(CommandHandler("config", cmd_config))
    application.add_handler(CommandHandler("thresholds", cmd_thresholds))
    application.add_handler(CommandHandler("regime", cmd_regime))
    
    # Analytics
    application.add_handler(CommandHandler("analytics", cmd_analytics))
    application.add_handler(CommandHandler("sentiment", cmd_sentiment))
    
    # Control
    application.add_handler(CommandHandler("pause", cmd_pause))
    application.add_handler(CommandHandler("resume", cmd_resume))
    application.add_handler(CommandHandler("logs", cmd_logs))
    
    # Admin
    application.add_handler(CommandHandler("admin", cmd_admin))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    _handlers_registered = True
    
    print("✅ [BOT] All handlers registered")
    print("   • General: 3 commands")
    print("   • Whale Monitoring: 4 commands")
    print("   • Trading System: 5 commands")
    print("   • Configuration: 3 commands")
    print("   • Analytics: 2 commands")
    print("   • Control: 3 commands")
    print("   • Admin: 1 command")


# ============================================================================
# MAIN FUNCTION (для тестирования)
# ============================================================================

async def main():
    """Главная функция для standalone запуска бота"""
    
    print("\n" + "="*80)
    print("🤖 TELEGRAM BOT - STANDALONE MODE")
    print("="*80 + "\n")
    
    # Регистрируем handlers
    register_handlers()
    
    # Инициализируем и запускаем
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ Bot is running...")
    print("Press Ctrl+C to stop\n")
    
    # Ждём завершения
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n⏹️ Stopping bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        print("✅ Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())