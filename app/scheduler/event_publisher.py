# app/scheduler/event_publisher.py
"""
Event Publisher for Whale Monitor
Публикация событий
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Публикация whale событий
    
    Управляет очередью и публикацией
    """
    
    def __init__(self, components: Dict[str, Any]):
        """
        Инициализация publisher
        
        Args:
            components: Компоненты системы
        """
        self.components = components
        self.publication_manager = None
        
        # Попытка загрузить publication manager
        try:
            from .whale_components import PublicationManager
            self.publication_manager = PublicationManager(components)
        except ImportError:
            logger.debug("PublicationManager not available")
    
    async def publish_events(self, events: List[Any]) -> int:
        """
        Публикация событий
        
        Args:
            events: События для публикации
            
        Returns:
            Количество опубликованных событий
        """
        if not self.publication_manager:
            logger.debug("📭 [PUBLISH] Publication manager not available")
            return 0
        
        try:
            # Подготовка элементов для публикации
            items = self._prepare_publication_items(events)
            
            if not items:
                logger.debug("📭 [PUBLISH] No items to publish")
                return 0
            
            # Публикация
            published = await self.publication_manager.publish_batch(items)
            
            return published
        
        except Exception as e:
            logger.error(f"❌ [PUBLISH] Error publishing events: {e}")
            return 0
    
    def _prepare_publication_items(self, events: List[Any]) -> List[Dict[str, Any]]:
        """
        Подготовка элементов для публикации
        
        Args:
            events: События
            
        Returns:
            Список элементов для публикации
        """
        items = []
        scorer = self.components.get('scorer')
        
        if not scorer:
            logger.debug("Scorer not available")
            return []
        
        for event in events:
            try:
                # Расчет вердикта и приоритета
                verdict, confidence = scorer.calculate_verdict_and_confidence(event)
                
                if not scorer.should_publish(event, verdict, confidence):
                    continue
                
                priority = scorer.calculate_priority(event, confidence)
                
                items.append({
                    'event': event,
                    'verdict': verdict,
                    'confidence': confidence,
                    'priority': priority
                })
            
            except Exception as e:
                logger.debug(f"Error preparing event: {e}")
                continue
        
        # Сортировка по приоритету
        items.sort(key=lambda x: x['priority'], reverse=True)
        
        return items
    
    async def cleanup(self):
        """Cleanup publisher"""
        if self.publication_manager and hasattr(self.publication_manager, 'cleanup'):
            try:
                await self.publication_manager.cleanup()
            except Exception as e:
                logger.debug(f"Cleanup error: {e}")


__all__ = ['EventPublisher']