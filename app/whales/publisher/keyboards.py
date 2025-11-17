# app/whales/publisher/keyboards.py
"""
Keyboard Builder for Whale Events
Создание inline клавиатур для whale событий
"""

from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.whales.normalize import WhaleEvent


class KeyboardBuilder:
    """Построение inline клавиатур для whale событий"""

    @staticmethod
    def create_whale_keyboard(
        event: WhaleEvent,
        news: List[Dict]
    ) -> Optional[InlineKeyboardMarkup]:
        """
        Создание клавиатуры для whale события

        Args:
            event: Whale событие
            news: Список связанных новостей

        Returns:
            InlineKeyboardMarkup или None
        """
        try:
            buttons = []

            # Кнопка с explorer ссылкой на транзакцию
            if event.tx_hash and event.chain:
                explorer_url = KeyboardBuilder._get_explorer_url(
                    event.chain,
                    event.tx_hash
                )
                if explorer_url:
                    buttons.append([
                        InlineKeyboardButton(
                            f"🔍 Смотреть на {event.chain.capitalize()}",
                            url=explorer_url
                        )
                    ])

            # Кнопки для связанных новостей (максимум 2)
            if news:
                for article in news[:2]:
                    if 'url' in article and 'title' in article:
                        # Обрезаем заголовок до 30 символов
                        title = article['title'][:30] + "..." if len(article['title']) > 30 else article['title']
                        buttons.append([
                            InlineKeyboardButton(
                                f"📰 {title}",
                                url=article['url']
                            )
                        ])

            # Если нет кнопок, возвращаем None
            if not buttons:
                return None

            return InlineKeyboardMarkup(buttons)

        except Exception as e:
            print(f"⚠️ [KEYBOARD] Ошибка создания клавиатуры: {e}")
            return None

    @staticmethod
    def _get_explorer_url(chain: str, tx_hash: str) -> Optional[str]:
        """
        Получение URL блокчейн explorer

        Args:
            chain: Название блокчейна
            tx_hash: Хеш транзакции

        Returns:
            URL или None
        """
        explorers = {
            'ethereum': f'https://etherscan.io/tx/{tx_hash}',
            'eth': f'https://etherscan.io/tx/{tx_hash}',
            'bsc': f'https://bscscan.com/tx/{tx_hash}',
            'polygon': f'https://polygonscan.com/tx/{tx_hash}',
            'arbitrum': f'https://arbiscan.io/tx/{tx_hash}',
            'optimism': f'https://optimistic.etherscan.io/tx/{tx_hash}',
            'base': f'https://basescan.org/tx/{tx_hash}',
            'avalanche': f'https://snowtrace.io/tx/{tx_hash}',
            'solana': f'https://solscan.io/tx/{tx_hash}',
            'sol': f'https://solscan.io/tx/{tx_hash}',
            'tron': f'https://tronscan.org/#/transaction/{tx_hash}',
        }

        return explorers.get(chain.lower())


__all__ = ['KeyboardBuilder']
