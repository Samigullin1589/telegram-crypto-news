# app/scheduler/whale_components/event_filter.py
"""
Event Filter
Фильтрация событий по различным критериям
"""

import logging
from typing import Dict, Set
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class EventFilter:
    """Фильтрация whale событий"""
    
    def __init__(self, components: Dict):
        """
        Args:
            components: Компоненты системы
        """
        self.adaptive_thresholds = components.get('adaptive_thresholds')
        self.discovery = components.get('discovery')
        
        # Счётчики для статистики
        self.filter_stats = {
            'duplicate': 0,
            'asset_not_allowed': 0,
            'internal_transfer': 0,
            'bridge_transfer': 0,
            'reorg_event': 0,
            'below_threshold': 0,
            'low_confidence': 0
        }
    
    def should_process_event(
        self, 
        event: WhaleEvent, 
        seen_keys: Set[str]
    ) -> tuple[bool, str]:
        """
        Проверка необходимости обработки события
        
        Args:
            event: Событие для проверки
            seen_keys: Множество уже обработанных ключей
            
        Returns:
            (should_process, reason) - нужно ли обрабатывать и причина
        """
        # Проверка дубликата
        dedup_key = event.get_dedup_key()
        if dedup_key in seen_keys:
            self.filter_stats['duplicate'] += 1
            return False, "duplicate"
        
        # Проверка разрешённости актива
        if not self._is_asset_allowed(event):
            self.filter_stats['asset_not_allowed'] += 1
            logger.debug(f"🚫 [FILTER] Актив не в watchlist: {event.asset} на {event.chain}")
            return False, "asset_not_allowed"
        
        # Фильтрация внутренних переводов
        if event.is_internal:
            self.filter_stats['internal_transfer'] += 1
            logger.debug(f"🚫 [FILTER] Внутренний перевод: {event.asset}")
            return False, "internal_transfer"
        
        # Фильтрация bridge переводов
        if event.is_bridge:
            self.filter_stats['bridge_transfer'] += 1
            logger.debug(f"🚫 [FILTER] Bridge перевод: {event.asset}")
            return False, "bridge_transfer"
        
        # Фильтрация reorg событий
        if event.is_reorg:
            self.filter_stats['reorg_event'] += 1
            logger.debug(f"🚫 [FILTER] Reorg событие: {event.asset}")
            return False, "reorg_event"
        
        return True, "passed"
    
    def check_value_threshold(
        self, 
        event: WhaleEvent
    ) -> tuple[bool, str]:
        """
        Проверка порога стоимости
        
        Args:
            event: Событие с обогащёнными данными
            
        Returns:
            (passed, reason)
        """
        min_threshold = config.whale.min_usd_threshold
        
        if event.amount_usd < min_threshold:
            self.filter_stats['below_threshold'] += 1
            logger.debug(
                f"🚫 [FILTER] Ниже порога: {event.asset} "
                f"${event.amount_usd:,.0f} < ${min_threshold:,.0f}"
            )
            return False, "below_threshold"
        
        logger.debug(f"✅ [FILTER] Порог пройден: {event.asset} ${event.amount_usd:,.0f}")
        return True, "passed"
    
    def check_confidence_threshold(
        self, 
        event: WhaleEvent, 
        confidence: float
    ) -> tuple[bool, str]:
        """
        Проверка порога уверенности
        
        Args:
            event: Событие
            confidence: Уровень уверенности
            
        Returns:
            (passed, reason)
        """
        thresholds = self._get_thresholds()
        min_confidence = thresholds["min_confidence"]
        
        if confidence < min_confidence:
            self.filter_stats['low_confidence'] += 1
            logger.debug(
                f"🚫 [FILTER] Низкая уверенность: {event.asset} "
                f"{confidence:.2f} < {min_confidence:.2f}"
            )
            return False, "low_confidence"
        
        logger.debug(f"✅ [FILTER] Уверенность достаточна: {event.asset} {confidence:.2f}")
        return True, "passed"
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """
        Проверка разрешённости актива через discovery
        
        Args:
            event: Событие для проверки
            
        Returns:
            True если актив разрешён
        """
        if not self.discovery:
            # Если discovery отсутствует, разрешаем все активы
            return True
        
        is_allowed = self.discovery.is_in_watchlist(event.chain, event.asset)
        
        if not is_allowed:
            logger.debug(
                f"🔍 [DISCOVERY] Актив {event.asset} не найден в watchlist для {event.chain}"
            )
        
        return is_allowed
    
    def _get_thresholds(self) -> Dict:
        """
        Получение текущих порогов фильтрации
        
        Returns:
            Dict с порогами
        """
        if self.adaptive_thresholds:
            thresholds = self.adaptive_thresholds.get_current_thresholds()
            logger.debug(f"🎯 [THRESHOLDS] Используются адаптивные пороги: {thresholds}")
            return thresholds
        
        # Дефолтные пороги
        default_thresholds = {
            "min_confidence": config.whale.min_confidence_score,
            "min_size_rel": 0.10,
            "min_volume_24h": 1000000
        }
        logger.debug(f"🎯 [THRESHOLDS] Используются дефолтные пороги: {default_thresholds}")
        return default_thresholds
    
    def get_stats(self) -> Dict:
        """
        Получение статистики фильтрации
        
        Returns:
            Dict со счётчиками
        """
        return self.filter_stats.copy()
    
    def reset_stats(self):
        """Сброс статистики"""
        for key in self.filter_stats:
            self.filter_stats[key] = 0