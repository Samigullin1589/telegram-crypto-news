# app/whales/monitor/solana_components/solana_event_filter.py
"""
Solana Event Filter
Фильтрация whale событий для Solana
"""

import logging

from app.config import config
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class SolanaEventFilter:
    """Фильтр whale событий для Solana"""
    
    def __init__(self):
        """Инициализация фильтра"""
        self.min_usd_threshold = getattr(config.whale, 'min_usd_threshold', 50000)
    
    def should_process(self, event: WhaleEvent) -> bool:
        """
        Проверка необходимости обработки события
        
        Args:
            event: Whale событие
            
        Returns:
            True если событие должно быть обработано
        """
        # Фильтр по сумме
        if event.amount_usd < self.min_usd_threshold:
            logger.debug(
                f"🚫 [SOLANA FILTER] {event.asset}: "
                f"${event.amount_usd:,.0f} < ${self.min_usd_threshold:,.0f}"
            )
            return False
        
        # Фильтр внутренних переводов
        if event.is_internal:
            logger.debug(f"🚫 [SOLANA FILTER] {event.asset}: internal transfer")
            return False
        
        # Фильтр bridge переводов
        if event.is_bridge:
            logger.debug(f"🚫 [SOLANA FILTER] {event.asset}: bridge transfer")
            return False
        
        # Фильтр некорректных адресов
        if event.from_address == "unknown" or event.to_address == "unknown":
            logger.debug(f"🚫 [SOLANA FILTER] {event.asset}: unknown address")
            return False
        
        return True