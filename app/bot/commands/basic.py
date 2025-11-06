# app/bot/commands/basic.py
"""
Basic bot commands: start, help, menu
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.bot.utils import is_admin
from app.bot.keyboards import get_main_menu_keyboard, get_menu_keyboard


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    
    user = update.effective_user
    
    text = f"""
👋 <b>Привет, {user.first_name}!</b>

🐋 <b>Whale Monitor & Trading Bot</b>

Я помогаю отслеживать крупные перемещения криптовалют и генерировать торговые сигналы.

<b>📋 Основные команды:</b>
/help - Полный список команд
/status - Текущий статус системы
/menu - Главное меню

<b>🔐 Админ команды:</b>
/admin - Панель управления
"""
    
    keyboard = get_main_menu_keyboard(is_admin(user.id))
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    
    user_id = update.effective_user.id
    
    text = """
<b>📚 СПРАВКА ПО КОМАНДАМ</b>

<b>🌊 WHALE MONITORING</b>
/status - Статус системы
/wallets - Отслеживаемые кошельки
/whales - Последние перемещения
/discover - Поиск новых трейдеров

<b>📈 TRADING SYSTEM</b>
/positions - Открытые позиции
/performance [days] - Статистика
/signal <ASSET> - Сгенерировать сигнал
/close <position_id> - Закрыть позицию
/trades [days] - История сделок

<b>⚙️  НАСТРОЙКИ</b>
/config - Конфигурация
/thresholds - Адаптивные пороги
/regime - Режим рынка

<b>🔧 УПРАВЛЕНИЕ</b>
/pause - Приостановить
/resume - Возобновить
/logs [lines] - Логи

<b>📊 АНАЛИТИКА</b>
/analytics - Аналитика активов
/sentiment <ASSET> - Sentiment анализ

<b>💡 ПРИМЕРЫ:</b>
/signal BTC
/performance 7
/trades 14

<b>⚠️  ДИСКЛЕЙМЕР:</b>
Все сигналы - только информация, НЕ финансовые рекомендации.
"""
    
    if not is_admin(user_id):
        text += "\n\n<i>🔒 Некоторые команды только для администратора</i>"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu"""
    
    keyboard = get_menu_keyboard(is_admin(update.effective_user.id))
    
    text = "<b>📋 ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


__all__ = ['cmd_start', 'cmd_help', 'cmd_menu']