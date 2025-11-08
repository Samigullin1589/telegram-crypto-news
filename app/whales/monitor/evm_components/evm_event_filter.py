# app/whales/monitor/evm_components/evm_event_filter.py
"""
EVM Event Filter
Фильтрация whale событий
"""

import logging
from typing import Optional

from app.config import config
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class EVMEventFilter:
    """Фильтр whale событий"""
    
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
                f"🚫 [FILTER] {event.asset}: ${event.amount_usd:,.0f} < ${self.min_usd_threshold:,.0f}"
            )
            return False
        
        # Фильтр внутренних переводов
        if event.is_internal:
            logger.debug(f"🚫 [FILTER] {event.asset}: internal transfer")
            return False
        
        # Фильтр bridge переводов
        if event.is_bridge:
            logger.debug(f"🚫 [FILTER] {event.asset}: bridge transfer")
            return False
        
        # Фильтр reorg событий
        if event.is_reorg:
            logger.debug(f"🚫 [FILTER] {event.asset}: reorg event")
            return False
        
        return True