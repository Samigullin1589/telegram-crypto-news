# app/scheduler/whale_monitor.py
"""
Whale Monitoring System
Handles whale event detection, filtering, and publishing
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque

from app.config import config
from app.whales.monitor import BlockchainMonitor
from app.whales.normalize import WhaleEvent

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """Мониторинг крупных перемещений криптовалюты"""
    
    def __init__(self, components: Dict):
        self.components = components
        self.seen_keys = components.get('seen_keys', set())
        self.publication_queue = []
        self.recent_publications = deque(maxlen=config.whale.posts_per_hour_cap)
        
        self.scorer = components.get('scorer')
        self.price_provider = components.get('price_provider')
        self.news_gate = components.get('news_gate')
        self.publisher = components.get('publisher')
        self.chart_renderer = components.get('chart_renderer')
        self.history_manager = components.get('history_manager')
        self.adaptive_thresholds = components.get('adaptive_thresholds')
        self.discovery = components.get('discovery')
        
        logger.info("🐋 [WHALE] Monitor инициализирован")
    
    async def run_cycle(self, start_time: datetime, chains: List[str]) -> Dict:
        """Выполнить один цикл мониторинга"""
        try:
            events = []
            async with BlockchainMonitor() as monitor:
                rate_limiter = self.components.get('rate_limiter')
                if rate_limiter:
                    monitor.rate_limiter = rate_limiter
                
                events = await monitor.fetch_events(start_time, chains=chains)
                
                if not events:
                    logger.info("👍 [WHALE] Новых перемещений не найдено")
                else:
                    logger.info(f"🔄 [WHALE] Найдено {len(events)} событий")
                    await self._process_events(events)
            
            await self._publish_from_queue()
            
            return {
                'success': True,
                'events_collected': len(events),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ [WHALE] Ошибка в цикле: {e}")
            raise
    
    async def _process_events(self, events: List[WhaleEvent]):
        """Обработка whale событий"""
        logger.info(f"🔄 [PIPELINE] Обработка {len(events)} событий")
        
        thresholds = self._get_thresholds()
        
        async with aiohttp.ClientSession() as session:
            qualified_events = []
            
            for event in events:
                try:
                    if not self._filter_event(event, thresholds):
                        continue
                    
                    await self.price_provider.enrich_event_with_market_data(event, session)
                    
                    if event.amount_usd < config.whale.min_usd_threshold:
                        continue
                    
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if confidence < thresholds["min_confidence"]:
                        continue
                    
                    qualified_events.append(event)
                    self.seen_keys.add(event.get_dedup_key())
                
                except Exception as e:
                    logger.error(f"⚠️ [FILTER] Ошибка обработки: {e}")
                    continue
            
            logger.info(f"✅ [QUALIFY] Прошло фильтры: {len(qualified_events)} событий")
            
            if not qualified_events:
                return
            
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            for event in qualified_events:
                try:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if not self.scorer.should_publish(event, verdict, confidence):
                        continue
                    
                    history_hint = await self.history_manager.find_similar_event(event, session)
                    if history_hint:
                        event.history_hint = history_hint
                    
                    priority = self.scorer.calculate_priority(event, confidence)
                    
                    self.publication_queue.append({
                        "event": event,
                        "verdict": verdict,
                        "confidence": confidence,
                        "priority": priority,
                        "queued_at": datetime.utcnow()
                    })
                except Exception as e:
                    logger.error(f"⚠️ [SCORE] Ошибка оценки: {e}")
                    continue
            
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            logger.info(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    def _filter_event(self, event: WhaleEvent, thresholds: Dict) -> bool:
        """Фильтрация события"""
        dedup_key = event.get_dedup_key()
        if dedup_key in self.seen_keys:
            return False
        
        if not self._is_asset_allowed(event):
            return False
        
        if event.is_internal or event.is_bridge or event.is_reorg:
            return False
        
        return True
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """Проверка разрешённости актива"""
        if self.discovery:
            return self.discovery.is_in_watchlist(event.chain, event.asset)
        return True
    
    def _get_thresholds(self) -> Dict:
        """Получение текущих порогов"""
        if self.adaptive_thresholds:
            return self.adaptive_thresholds.get_current_thresholds()
        else:
            return {
                "min_confidence": config.whale.min_confidence_score,
                "min_size_rel": 0.10,
                "min_volume_24h": 1000000
            }
    
    async def _publish_from_queue(self):
        """Публикация из очереди"""
        now = datetime.utcnow()
        
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        if len(self.recent_publications) >= config.whale.posts_per_hour_cap:
            logger.info(f"⏸️ [RATE] Лимит {config.whale.posts_per_hour_cap}/час достигнут")
            return
        
        while self.publication_queue and len(self.recent_publications) < config.whale.posts_per_hour_cap:
            item = self.publication_queue.pop(0)
            
            event = item["event"]
            verdict = item["verdict"]
            confidence = item["confidence"]
            
            try:
                async with aiohttp.ClientSession() as session:
                    news = await self.news_gate.get_relevant_news(event, session)
                    
                    chart_path = None
                    
                    published = await self.publisher.publish_whale_event(
                        event, verdict, confidence, news, chart_path
                    )
                    
                    if published:
                        self.recent_publications.append(datetime.utcnow())
                        self.history_manager.save_event(event, verdict)
                        
                        pending = self.components.get('pending_verification')
                        if pending is not None:
                            pending.append({
                                "event": event,
                                "verdict": verdict,
                                "confidence": confidence,
                                "published_at": datetime.utcnow()
                            })
                        
                        logger.info(f"✅ [PUBLISHED] {event.asset} ${event.amount_usd:,.0f}")
                    
                    await asyncio.sleep(120)
            
            except Exception as e:
                logger.error(f"❌ [PUBLISH] Ошибка: {e}")