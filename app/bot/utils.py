# app/bot/utils.py
"""
Bot utilities - formatting, validation, checks
"""

import asyncio
from typing import Optional
from telegram import Update
from telegram.constants import ParseMode
from app.config import config


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    try:
        admin_id = config.telegram.admin_chat_id
        if isinstance(admin_id, str):
            admin_id = int(admin_id)
        return user_id == admin_id
    except (ValueError, TypeError, AttributeError):
        return False


async def send_long_message(update: Update, text: str, parse_mode: str = ParseMode.HTML):
    """Отправка длинного сообщения с разбиением"""
    
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
        prefix = f"<i>Часть {i+1}/{len(parts)}</i>\n\n" if i > 0 else ""
        await update.message.reply_text(f"{prefix}{part}", parse_mode=parse_mode)
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


__all__ = ['is_admin', 'send_long_message', 'format_duration', 'format_number']