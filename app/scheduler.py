# app/scheduler.py
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict
from collections import deque

from app import settings
from app.whales.discovery import DiscoveryEngine
from app.whales.monitor import BlockchainMonitor
from app.whales.normalize import WhaleEvent
from app.whales.score import EventScorer
from app.whales.price import PriceProvider
from app.whales.news import NewsGate
from app.whales.publish import WhalePublisher
from app.whales.history import HistoryManager
from app.charts.sparkline import SparklineRenderer

class WhaleScheduler:
    """Главный координатор системы мониторинга китов"""
    
    def __init__(self):
        self.discovery = DiscoveryEngine()
        self.scorer = EventScorer()
        self.price_provider = PriceProvider()
        self.news_gate = NewsGate()
        self.publisher = WhalePublisher()
        self.chart_renderer = SparklineRenderer()
        self.history_manager = HistoryManager()
        
        self.publication_queue: List[Dict] = []
        self.seen_keys: set = set()
        self.recent_publications = deque(maxlen=settings.POSTS_PER_HOUR_CAP)
        
        self._load_state()
    
    async def run(self):
        """Главный цикл работы"""
        print("=" * 80)
        print("🐋 ONE-CHANNEL WHALE MONITOR + NEWS BOT")
        print("=" * 80)
        print(f"Режим: {'DISCOVERY (весь рынок)' if settings.ASSETS == '*' else 'ALLOWLIST'}")
        print(f"Канал: {settings.CHAT_ID}")
        print(f"Лимит публикаций: {settings.POSTS_PER_HOUR_CAP}/час")
        print("=" * 80)
        
        tasks = [
            self._discovery_loop(),
            self._whale_monitor_loop(),
        ]
        
        await asyncio.gather(*tasks)
    
    async def _discovery_loop(self):
        """Обновление watchlist"""
        if settings.ASSETS != '*':
            print("⏭️  Discovery отключен (ALLOWLIST режим)")
            return
        
        while True:
            try:
                print(f"\n🔄 [DISCOVERY] Запуск обновления watchlist")
                await self.discovery.refresh_watchlist()
                
                wait_seconds = settings.DISCOVERY_REFRESH_HOURS * 3600
                print(f"⏰ [DISCOVERY] Следующее обновление через {settings.DISCOVERY_REFRESH_HOURS}ч")
                await asyncio.sleep(wait_seconds)
                
            except Exception as e:
                print(f"❌ [DISCOVERY] Ошибка: {e}")
                await asyncio.sleep(1800)
    
    async def _whale_monitor_loop(self):
        """Мониторинг крупных перемещений"""
        start_time = datetime.utcnow() - timedelta(minutes=settings.START_FROM_MINUTES_AGO)
        
        while True:
            try:
                print(f"\n📊 [WHALE] Цикл: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                
                async with BlockchainMonitor() as monitor:
                    events = await monitor.fetch_events(start_time)
                    
                    if not events:
                        print("👍 [WHALE] Новых перемещений не найдено")
                    else:
                        await self._process_events(events)
                
                start_time = datetime.utcnow()
                await self._publish_from_queue()
                
                print(f"⏰ [WHALE] Следующая проверка через {settings.POLL_SECONDS}с")
                await asyncio.sleep(settings.POLL_SECONDS)
                
            except Exception as e:
                print(f"❌ [WHALE] Критическая ошибка: {e}")
                await asyncio.sleep(300)
    
    async def _process_events(self, events: List[WhaleEvent]):
        """Обрабатывает события через pipeline"""
        print(f"🔄 [PIPELINE] Обработка {len(events)} событий")
        
        async with aiohttp.ClientSession() as session:
            qualified_events = []
            
            for event in events:
                dedup_key = event.get_dedup_key()
                if dedup_key in self.seen_keys:
                    continue
                
                if not self._is_asset_allowed(event):
                    continue
                
                if event.is_internal or event.is_bridge or event.is_reorg:
                    continue
                
                await self.price_provider.enrich_event_with_market_data(event, session)
                
                if event.amount_usd < event.min_usd_threshold:
                    continue
                
                qualified_events.append(event)
                self.seen_keys.add(dedup_key)
            
            print(f"✅ [QUALIFY] Прошло фильтры: {len(qualified_events)} событий")
            
            if not qualified_events:
                return
            
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            for event in qualified_events:
                verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                
                if not self.scorer.should_publish(event, verdict, confidence):
                    print(f"⏭️  [SKIP] {event.asset}: не проходит критерии")
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
            
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикует события из очереди"""
        now = datetime.utcnow()
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        if len(self.recent_publications) >= settings.POSTS_PER_HOUR_CAP:
            print(f"⏸️  [RATE] Достигнут лимит {settings.POSTS_PER_HOUR_CAP} публикаций/час")
            return
        
        while self.publication_queue and len(self.recent_publications) < settings.POSTS_PER_HOUR_CAP:
            item = self.publication_queue.pop(0)
            
            event = item["event"]
            verdict = item["verdict"]
            confidence = item["confidence"]
            
            try:
                async with aiohttp.ClientSession() as session:
                    news = await self.news_gate.get_relevant_news(event, session)
                    
                    chart_path = None
                    if settings.ENABLE_IMAGES:
                        chart_path = f"/tmp/chart_{event.asset}_{int(datetime.utcnow().timestamp())}.png"
                        success = await self.chart_renderer.render(event.asset, event.tx_time_utc, chart_path)
                        if not success:
                            chart_path = None
                    
                    published = await self.publisher.publish_whale_event(
                        event, verdict, confidence, news, chart_path
                    )
                    
                    if published:
                        self.recent_publications.append(datetime.utcnow())
                        self.history_manager.save_event(event, verdict)
                    
                    await asyncio.sleep(120)
                    
            except Exception as e:
                print(f"❌ [PUBLISH] Ошибка: {e}")
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """Проверяет разрешён ли актив"""
        if settings.ASSETS == '*':
            return self.discovery.is_in_watchlist(event.chain, event.asset)
        else:
            return event.asset in settings.ASSETS_LIST
    
    def _load_state(self):
        """Загружает состояние"""
        try:
            with open(settings.STATE_FILE, 'r') as f:
                state = json.load(f)
                self.seen_keys = set(state.get("seen_keys", []))
                print(f"📂 [STATE] Загружено {len(self.seen_keys)} dedupe ключей")
        except FileNotFoundError:
            print("📂 [STATE] Файл состояния не найден")
            self.seen_keys = set()
    
    def _save_state(self):
        """Сохраняет состояние"""
        try:
            state = {
                "last_seen_timestamp": datetime.utcnow().isoformat(),
                "seen_keys": list(self.seen_keys)[-10000:]
            }
            with open(settings.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️  [STATE] Не удалось сохранить: {e}")
    
    async def shutdown(self):
        """Корректное завершение"""
        print("\n⏹️  [SHUTDOWN] Остановка системы...")
        self._save_state()
        print("✅ [SHUTDOWN] Состояние сохранено")