# app/scheduler/whale_components/event_processor.py
"""
Event Processor
Обработка и квалификация событий
"""

import asyncio
import logging
from typing import List, Set
import aiohttp

from app.whales.normalize import WhaleEvent
from .event_filter import EventFilter
from .event_enricher import EventEnricher

logger = logging.getLogger(__name__)


class EventProcessor:
    """Процессор whale событий"""
    
    def __init__(
        self, 
        components: dict, 
        event_filter: EventFilter, 
        event_enricher: EventEnricher
    ):
        """
        Args:
            components: Компоненты системы
            event_filter: Фильтр событий
            event_enricher: Enricher для обогащения
        """
        self.components = components
        self.filter = event_filter
        self.enricher = event_enricher
        self.scorer = components.get('scorer')
        
        if not self.scorer:
            logger.warning("⚠️ [PROCESSOR] Scorer не доступен")
    
    async def process_events(
        self, 
        events: List[WhaleEvent], 
        seen_keys: Set[str]
    ) -> List[WhaleEvent]:
        """
        Обработка списка событий
        
        Args:
            events: Сырые события из блокчейна
            seen_keys: Множество уже обработанных ключей
            
        Returns:
            Список квалифицированных событий
        """
        logger.info(f"🔄 [PROCESSOR] Начинаю обработку {len(events)} событий")
        
        # Фаза 1: Первичная фильтрация
        filtered_events = self._filter_events(events, seen_keys)
        
        if not filtered_events:
            logger.info("🚫 [PROCESSOR] Все события отфильтрованы на первой фазе")
            return []
        
        logger.info(f"✅ [PROCESSOR] Первичная фильтрация: {len(filtered_events)}/{len(events)} прошли")
        
        # Фаза 2: Обогащение рыночными данными
        enriched_events = await self._enrich_events(filtered_events)
        
        if not enriched_events:
            logger.info("🚫 [PROCESSOR] Нет событий после обогащения")
            return []
        
        logger.info(f"💰 [PROCESSOR] Обогащение: {len(enriched_events)}/{len(filtered_events)} успешно")
        
        # Фаза 3: Фильтрация по стоимости и уверенности
        qualified_events = await self._qualify_events(enriched_events)
        
        if not qualified_events:
            logger.info("🚫 [PROCESSOR] Нет событий после квалификации")
            return []
        
        logger.info(f"✅ [PROCESSOR] Квалификация: {len(qualified_events)}/{len(enriched_events)} прошли")
        
        # Фаза 4: Определение фазы рынка
        if self.scorer:
            qualified_events = self.scorer.detect_phase(qualified_events)
            logger.info(f"📊 [PROCESSOR] Фазы рынка определены для {len(qualified_events)} событий")
        
        # Добавление ключей в seen_keys
        for event in qualified_events:
            seen_keys.add(event.get_dedup_key())
        
        return qualified_events
    
    def _filter_events(
        self, 
        events: List[WhaleEvent], 
        seen_keys: Set[str]
    ) -> List[WhaleEvent]:
        """
        Первичная фильтрация событий
        
        Args:
            events: Сырые события
            seen_keys: Множество обработанных ключей
            
        Returns:
            Отфильтрованные события
        """
        filtered = []
        
        for event in events:
            should_process, reason = self.filter.should_process_event(event, seen_keys)
            
            if should_process:
                filtered.append(event)
            else:
                logger.debug(f"🚫 [FILTER] {event.asset}: {reason}")
        
        return filtered
    
    async def _enrich_events(
        self, 
        events: List[WhaleEvent]
    ) -> List[WhaleEvent]:
        """
        Обогащение событий рыночными данными
        
        Args:
            events: Отфильтрованные события
            
        Returns:
            Обогащённые события
        """
        enriched = []
        
        async with aiohttp.ClientSession() as session:
            for event in events:
                try:
                    success = await self.enricher.enrich_with_market_data(event, session)
                    
                    if success:
                        enriched.append(event)
                    else:
                        logger.warning(f"⚠️ [ENRICH] Не удалось обогатить {event.asset}")
                
                except Exception as e:
                    logger.error(f"❌ [ENRICH] Ошибка обогащения {event.asset}: {e}")
                    continue
        
        return enriched
    
    async def _qualify_events(
        self, 
        events: List[WhaleEvent]
    ) -> List[WhaleEvent]:
        """
        Квалификация событий по порогам
        
        Args:
            events: Обогащённые события
            
        Returns:
            Квалифицированные события
        """
        qualified = []
        
        for event in events:
            try:
                # Проверка порога стоимости
                value_passed, value_reason = self.filter.check_value_threshold(event)
                
                if not value_passed:
                    continue
                
                # Расчёт уверенности
                if self.scorer:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    # Проверка порога уверенности
                    confidence_passed, conf_reason = self.filter.check_confidence_threshold(
                        event, confidence
                    )
                    
                    if not confidence_passed:
                        continue
                    
                    # Сохранение вердикта и уверенности в событии
                    event.verdict = verdict
                    event.confidence = confidence
                
                qualified.append(event)
                
                logger.debug(
                    f"✅ [QUALIFY] {event.asset}: "
                    f"${event.amount_usd:,.0f}, "
                    f"confidence={getattr(event, 'confidence', 'N/A')}"
                )
            
            except Exception as e:
                logger.error(f"❌ [QUALIFY] Ошибка квалификации {event.asset}: {e}")
                continue
        
        return qualified