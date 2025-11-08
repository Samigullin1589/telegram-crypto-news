# app/scheduler/whale_components/event_enricher.py
"""
Event Enricher
Обогащение событий рыночными данными и историей
"""

import asyncio
import logging
from typing import Optional
import aiohttp

from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class EventEnricher:
    """Обогащение событий дополнительными данными"""
    
    def __init__(self, components: dict):
        """
        Args:
            components: Компоненты системы
        """
        self.price_provider = components.get('price_provider')
        self.history_manager = components.get('history_manager')
        self.news_gate = components.get('news_gate')
        
        if not self.price_provider:
            logger.warning("⚠️ [ENRICHER] Price provider не доступен")
        
        if not self.history_manager:
            logger.warning("⚠️ [ENRICHER] History manager не доступен")
    
    async def enrich_with_market_data(
        self, 
        event: WhaleEvent, 
        session: aiohttp.ClientSession
    ) -> bool:
        """
        Обогащение рыночными данными
        
        Args:
            event: Событие для обогащения (модифицируется in-place)
            session: HTTP сессия
            
        Returns:
            True если обогащение успешно
        """
        if not self.price_provider:
            logger.error(f"❌ [ENRICHER] Не могу обогатить {event.asset}: price_provider отсутствует")
            return False
        
        try:
            await self.price_provider.enrich_event_with_market_data(event, session)
            
            logger.debug(
                f"💰 [ENRICHER] {event.asset}: "
                f"${event.amount_usd:,.0f}, "
                f"price=${event.price_usd:.6f}, "
                f"volume_24h=${event.volume_24h:,.0f}"
            )
            return True
        
        except Exception as e:
            logger.error(f"❌ [ENRICHER] Ошибка обогащения {event.asset}: {e}")
            return False
    
    async def enrich_with_history(
        self, 
        event: WhaleEvent, 
        session: aiohttp.ClientSession
    ) -> Optional[str]:
        """
        Поиск похожих исторических событий
        
        Args:
            event: Событие для поиска истории
            session: HTTP сессия
            
        Returns:
            История hint или None
        """
        if not self.history_manager:
            return None
        
        try:
            history_hint = await self.history_manager.find_similar_event(event, session)
            
            if history_hint:
                event.history_hint = history_hint
                logger.debug(f"📚 [HISTORY] Найдена история для {event.asset}: {history_hint[:100]}...")
            
            return history_hint
        
        except Exception as e:
            logger.error(f"⚠️ [ENRICHER] Ошибка поиска истории для {event.asset}: {e}")
            return None
    
    async def enrich_with_news(
        self, 
        event: WhaleEvent, 
        session: aiohttp.ClientSession
    ) -> Optional[list]:
        """
        Получение релевантных новостей
        
        Args:
            event: Событие для поиска новостей
            session: HTTP сессия
            
        Returns:
            Список новостей или None
        """
        if not self.news_gate:
            logger.debug(f"📰 [NEWS] News gate не доступен для {event.asset}")
            return None
        
        try:
            news = await self.news_gate.get_relevant_news(event, session)
            
            if news:
                logger.debug(f"📰 [NEWS] Найдено {len(news)} новостей для {event.asset}")
            else:
                logger.debug(f"📰 [NEWS] Новостей не найдено для {event.asset}")
            
            return news
        
        except Exception as e:
            logger.error(f"⚠️ [ENRICHER] Ошибка получения новостей для {event.asset}: {e}")
            return None
    
    async def enrich_full(
        self, 
        event: WhaleEvent, 
        session: aiohttp.ClientSession,
        include_history: bool = True,
        include_news: bool = False
    ) -> bool:
        """
        Полное обогащение события всеми доступными данными
        
        Args:
            event: Событие для обогащения
            session: HTTP сессия
            include_history: Включать ли поиск истории
            include_news: Включать ли поиск новостей
            
        Returns:
            True если базовое обогащение успешно
        """
        # Рыночные данные (обязательно)
        market_success = await self.enrich_with_market_data(event, session)
        
        if not market_success:
            return False
        
        # История (опционально)
        if include_history:
            await self.enrich_with_history(event, session)
        
        # Новости (опционально, для публикации)
        if include_news:
            news = await self.enrich_with_news(event, session)
            event.related_news = news
        
        return True