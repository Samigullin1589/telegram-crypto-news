# app/scheduler/whale_components/publication_manager.py
"""
Publication Manager
Управление очередью и процессом публикации событий
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque
import aiohttp

from app.config import config
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class PublicationManager:
    """Менеджер публикаций whale событий"""
    
    def __init__(self, components: dict):
        """
        Args:
            components: Компоненты системы
        """
        self.components = components
        
        self.publisher = components.get('publisher')
        self.enricher = components.get('enricher')
        self.chart_renderer = components.get('chart_renderer')
        self.history_manager = components.get('history_manager')
        
        # Очереди и лимиты
        self.publication_queue = []
        self.recent_publications = deque(maxlen=config.whale.posts_per_hour_cap)
        self.posts_per_hour_cap = config.whale.posts_per_hour_cap
        
        # Таймауты и задержки
        self.publish_delay_seconds = 120  # Задержка между публикациями
        
        if not self.publisher:
            logger.error("❌ [PUBLICATION] Publisher не доступен!")
        else:
            logger.info(
                f"📢 [PUBLICATION] Manager инициализирован. "
                f"Лимит: {self.posts_per_hour_cap}/час, "
                f"задержка: {self.publish_delay_seconds}s"
            )
    
    async def publish_batch(self, publication_items: List[Dict]) -> int:
        """
        Публикация пакета событий
        
        Args:
            publication_items: Список элементов для публикации
            
        Returns:
            Количество опубликованных событий
        """
        if not self.publisher:
            logger.error("❌ [PUBLICATION] Невозможно публиковать: publisher отсутствует")
            return 0
        
        # Добавление в очередь
        self.publication_queue.extend(publication_items)
        self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"📋 [QUEUE] Добавлено {len(publication_items)} событий. Всего в очереди: {len(self.publication_queue)}")
        
        # Публикация из очереди
        published_count = await self._process_queue()
        
        return published_count
    
    async def _process_queue(self) -> int:
        """
        Обработка очереди публикаций с учётом лимитов
        
        Returns:
            Количество опубликованных событий
        """
        published_count = 0
        now = datetime.utcnow()
        
        # Очистка старых записей о публикациях
        self._cleanup_recent_publications(now)
        
        # Проверка лимита
        available_slots = self.posts_per_hour_cap - len(self.recent_publications)
        
        if available_slots <= 0:
            logger.info(
                f"⏸️ [RATE] Лимит {self.posts_per_hour_cap}/час достигнут. "
                f"В очереди: {len(self.publication_queue)} событий"
            )
            return 0
        
        logger.info(f"📊 [RATE] Доступно слотов: {available_slots}/{self.posts_per_hour_cap}")
        
        # Публикация событий
        while self.publication_queue and len(self.recent_publications) < self.posts_per_hour_cap:
            item = self.publication_queue.pop(0)
            
            try:
                success = await self._publish_item(item)
                
                if success:
                    published_count += 1
                    self.recent_publications.append(datetime.utcnow())
                    
                    # Задержка между публикациями
                    if self.publication_queue:
                        logger.debug(f"⏱️ [DELAY] Ожидание {self.publish_delay_seconds}s...")
                        await asyncio.sleep(self.publish_delay_seconds)
            
            except Exception as e:
                logger.error(f"❌ [PUBLISH] Критическая ошибка публикации: {e}")
                continue
        
        if self.publication_queue:
            logger.info(f"📋 [QUEUE] Осталось в очереди: {len(self.publication_queue)} событий")
        
        return published_count
    
    async def _publish_item(self, item: Dict) -> bool:
        """
        Публикация одного элемента
        
        Args:
            item: Элемент для публикации
            
        Returns:
            True если публикация успешна
        """
        event = item["event"]
        verdict = item["verdict"]
        confidence = item["confidence"]
        
        logger.info(
            f"📢 [PUBLISH] Начинаю публикацию: {event.asset} "
            f"${event.amount_usd:,.0f} (priority={item['priority']:.2f})"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                # Обогащение дополнительными данными для публикации
                news = None
                if self.enricher:
                    news = await self.enricher.enrich_with_news(event, session)
                
                # Генерация графика (если доступно)
                chart_path = None
                if self.chart_renderer:
                    try:
                        chart_path = await self.chart_renderer.render_chart(event)
                    except Exception as e:
                        logger.warning(f"⚠️ [CHART] Не удалось создать график: {e}")
                
                # Публикация
                published = await self.publisher.publish_whale_event(
                    event=event,
                    verdict=verdict,
                    confidence=confidence,
                    news=news,
                    chart_path=chart_path
                )
                
                if published:
                    logger.info(
                        f"✅ [PUBLISHED] {event.asset} ${event.amount_usd:,.0f} - "
                        f"{verdict} (confidence={confidence:.2f})"
                    )
                    
                    # Сохранение в историю
                    if self.history_manager:
                        self.history_manager.save_event(event, verdict)
                    
                    # Добавление в pending verification
                    pending = self.components.get('pending_verification')
                    if pending is not None:
                        pending.append({
                            "event": event,
                            "verdict": verdict,
                            "confidence": confidence,
                            "published_at": datetime.utcnow()
                        })
                    
                    return True
                else:
                    logger.warning(f"⚠️ [PUBLISH] Публикация не удалась для {event.asset}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ [PUBLISH] Ошибка публикации {event.asset}: {e}", exc_info=True)
            return False
    
    def _cleanup_recent_publications(self, now: datetime):
        """
        Очистка устаревших записей о публикациях
        
        Args:
            now: Текущее время
        """
        hour_ago = now - timedelta(hours=1)
        
        while self.recent_publications and self.recent_publications[0] < hour_ago:
            self.recent_publications.popleft()
    
    def get_queue(self) -> List[Dict]:
        """
        Получение текущей очереди
        
        Returns:
            Копия очереди публикаций
        """
        return self.publication_queue.copy()
    
    def get_recent_publications(self) -> List[datetime]:
        """
        Получение списка последних публикаций
        
        Returns:
            Список времён публикаций
        """
        return list(self.recent_publications)
    
    def get_stats(self) -> Dict:
        """
        Получение статистики публикаций
        
        Returns:
            Dict со статистикой
        """
        now = datetime.utcnow()
        self._cleanup_recent_publications(now)
        
        return {
            'queue_size': len(self.publication_queue),
            'recent_publications_count': len(self.recent_publications),
            'available_slots': self.posts_per_hour_cap - len(self.recent_publications),
            'hourly_limit': self.posts_per_hour_cap
        }