# app/bot/keyboards.py
"""
Inline keyboards for bot
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
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
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("🔧 Админ панель", callback_data="admin_panel")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def get_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Меню действий"""
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
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("🔧 Админ", callback_data="admin_panel")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Админ панель"""
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
            InlineKeyboardButton("⚙️  Конфиг", callback_data="config"),
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
    
    return InlineKeyboardMarkup(keyboard)


__all__ = [
    'get_main_menu_keyboard',
    'get_menu_keyboard',
    'get_admin_panel_keyboard'
]