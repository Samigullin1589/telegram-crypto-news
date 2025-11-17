# app/whales/publisher/utils.py
"""
Publisher Utilities
Вспомогательные функции для издателя
"""

import re
from typing import Optional


class PublisherUtils:
    """Утилиты для издателя"""

    @staticmethod
    def strip_html(text: str) -> str:
        """
        Удаление HTML тегов из текста

        Args:
            text: Текст с HTML тегами

        Returns:
            Очищенный текст
        """
        # Удаляем HTML теги
        clean = re.sub(r'<[^>]+>', '', text)

        # Удаляем множественные пробелы
        clean = re.sub(r'\s+', ' ', clean)

        # Удаляем пробелы в начале и конце
        clean = clean.strip()

        return clean

    @staticmethod
    def truncate_message(text: str, max_length: int = 4000) -> str:
        """
        Обрезка сообщения до максимальной длины

        Args:
            text: Исходный текст
            max_length: Максимальная длина

        Returns:
            Обрезанный текст
        """
        if len(text) <= max_length:
            return text

        # Обрезаем с запасом для "..."
        truncated = text[:max_length - 3]

        # Пытаемся обрезать по последнему переносу строки
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.8:  # Если обрезка не слишком агрессивная
            truncated = truncated[:last_newline]

        return truncated + "..."

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Экранирование специальных символов для Markdown

        Args:
            text: Исходный текст

        Returns:
            Экранированный текст
        """
        # Символы, которые нужно экранировать в Markdown
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

        for char in special_chars:
            text = text.replace(char, f'\\{char}')

        return text

    @staticmethod
    def format_number(num: float, decimals: int = 2) -> str:
        """
        Форматирование числа с разделителями тысяч

        Args:
            num: Число
            decimals: Количество знаков после запятой

        Returns:
            Отформатированная строка
        """
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.{decimals}f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.{decimals}f}M"
        elif num >= 1_000:
            return f"{num/1_000:.{decimals}f}K"
        else:
            return f"{num:.{decimals}f}"

    @staticmethod
    def get_emoji_for_direction(direction: str) -> str:
        """
        Получение emoji для направления движения

        Args:
            direction: Направление (inflow, outflow, etc.)

        Returns:
            Emoji строка
        """
        emoji_map = {
            'inflow_to_exchange': '📥',
            'outflow_from_exchange': '📤',
            'transfer': '🔄',
            'whale_to_whale': '🐋➡️🐋',
            'accumulation': '📊',
            'distribution': '💸',
        }

        return emoji_map.get(direction, '🔹')

    @staticmethod
    def get_emoji_for_phase(phase: str) -> str:
        """
        Получение emoji для фазы рынка

        Args:
            phase: Фаза (accumulation, distribution, etc.)

        Returns:
            Emoji строка
        """
        emoji_map = {
            'accumulation': '📊',
            'distribution': '💸',
            'transfer_cluster': '🔄',
            'isolated_event': '🔹',
        }

        return emoji_map.get(phase, '🔹')


__all__ = ['PublisherUtils']
