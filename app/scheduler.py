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
        """Обрабатывает события через pipeline с детальным логированием"""
        print(f"🔄 [PIPELINE] Обработка {len(events)} событий")
        
        async with aiohttp.ClientSession() as session:
            qualified_events = []
            
            # Статистика фильтрации
            filter_stats = {
                "dedup": 0,
                "asset_not_allowed": 0,
                "internal_bridge": 0,
                "price_failed": 0,
                "below_threshold": 0,
                "passed": 0
            }
            
            for event in events:
                if settings.DEBUG_FILTERS:
                    print(f"\n🔍 [FILTER] Проверяю: {event.asset} {event.amount_native:,.2f} ≈ ${event.amount_usd:,.0f}")
                
                # 1. Дедупликация
                dedup_key = event.get_dedup_key()
                if dedup_key in self.seen_keys:
                    filter_stats["dedup"] += 1
                    if settings.DEBUG_FILTERS:
                        print(f"  ❌ Дубликат (dedup_key уже в seen_keys)")
                    continue
                
                # 2. Проверка разрешённости актива
                if not self._is_asset_allowed(event):
                    filter_stats["asset_not_allowed"] += 1
                    if settings.DEBUG_FILTERS:
                        print(f"  ❌ Актив не разрешён (не в watchlist/allowlist)")
                    continue
                
                # 3. Проверка флагов internal/bridge/reorg
                if event.is_internal or event.is_bridge or event.is_reorg:
                    filter_stats["internal_bridge"] += 1
                    if settings.DEBUG_FILTERS:
                        print(f"  ❌ Внутренний перевод / bridge / reorg")
                    continue
                
                # 4. Обогащение рыночными данными (КРИТИЧЕСКИЙ ШАГ)
                if settings.DEBUG_FILTERS:
                    print(f"  💵 До обогащения: amount_usd=${event.amount_usd:,.0f}, threshold=${event.min_usd_threshold:,.0f}")
                
                await self.price_provider.enrich_event_with_market_data(event, session)
                
                if settings.DEBUG_FILTERS:
                    print(f"  💵 После обогащения: amount_usd=${event.amount_usd:,.0f}, threshold=${event.min_usd_threshold:,.0f}")
                
                # Проверка на провал обогащения
                if not event.market.price or not event.market.volume_24h_usd:
                    filter_stats["price_failed"] += 1
                    if settings.DEBUG_FILTERS:
                        print(f"  ⚠️  Не удалось получить цену/объём (будет пропущено позже в scorer)")
                    # НЕ фильтруем здесь, пусть scorer решит
                
                # 5. Проверка порога USD
                if event.amount_usd < event.min_usd_threshold:
                    filter_stats["below_threshold"] += 1
                    if settings.DEBUG_FILTERS:
                        print(f"  ❌ Ниже порога: ${event.amount_usd:,.0f} < ${event.min_usd_threshold:,.0f}")
                    continue
                
                # ✅ Прошло все фильтры!
                filter_stats["passed"] += 1
                qualified_events.append(event)
                self.seen_keys.add(dedup_key)
                
                if settings.DEBUG_FILTERS:
                    print(f"  ✅ ПРОШЛО ФИЛЬТРЫ!")
            
            # Итоговая статистика
            print(f"✅ [QUALIFY] Прошло фильтры: {len(qualified_events)} событий")
            
            if settings.DEBUG_FILTERS:
                print(f"📊 [FILTER STATS] "
                      f"Дубликаты: {filter_stats['dedup']}, "
                      f"Не разрешён: {filter_stats['asset_not_allowed']}, "
                      f"Internal/Bridge: {filter_stats['internal_bridge']}, "
                      f"Нет цены: {filter_stats['price_failed']}, "
                      f"Ниже порога: {filter_stats['below_threshold']}, "
                      f"✅ Прошло: {filter_stats['passed']}")
            
            if not qualified_events:
                return
            
            # Определение фаз
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            # Скоринг и добавление в очередь публикации
            for event in qualified_events:
                verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                
                if not self.scorer.should_publish(event, verdict, confidence):
                    if settings.DEBUG_FILTERS:
                        print(f"⏭️  [SKIP] {event.asset}: не проходит критерии публикации (confidence={confidence})")
                    continue
                
                # Поиск похожих событий в истории
                history_hint = await self.history_manager.find_similar_event(event, session)
                if history_hint:
                    event.history_hint = history_hint
                
                # Расчёт приоритета
                priority = self.scorer.calculate_priority(event, confidence)
                
                self.publication_queue.append({
                    "event": event,
                    "verdict": verdict,
                    "confidence": confidence,
                    "priority": priority,
                    "queued_at": datetime.utcnow()
                })
            
            # Сортировка по приоритету
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикует события из очереди"""
        now = datetime.utcnow()
        
        # Очистка старых записей из recent_publications
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        # Проверка лимита публикаций в час
        if len(self.recent_publications) >= settings.POSTS_PER_HOUR_CAP:
            print(f"⏸️  [RATE] Достигнут лимит {settings.POSTS_PER_HOUR_CAP} публикаций/час")
            return
        
        # Публикация событий из очереди
        while self.publication_queue and len(self.recent_publications) < settings.POSTS_PER_HOUR_CAP:
            item = self.publication_queue.pop(0)
            
            event = item["event"]
            verdict = item["verdict"]
            confidence = item["confidence"]
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Получение релевантных новостей
                    news = await self.news_gate.get_relevant_news(event, session)
                    
                    # Создание графика
                    chart_path = None
                    if settings.ENABLE_IMAGES:
                        chart_path = f"/tmp/chart_{event.asset}_{int(datetime.utcnow().timestamp())}.png"
                        success = await self.chart_renderer.render(event.asset, event.tx_time_utc, chart_path)
                        if not success:
                            chart_path = None
                    
                    # Публикация
                    published = await self.publisher.publish_whale_event(
                        event, verdict, confidence, news, chart_path
                    )
                    
                    if published:
                        self.recent_publications.append(datetime.utcnow())
                        self.history_manager.save_event(event, verdict)
                        print(f"✅ [PUBLISHED] {event.asset} ${event.amount_usd:,.0f}")
                    
                    # Задержка между публикациями
                    await asyncio.sleep(120)
                    
            except Exception as e:
                print(f"❌ [PUBLISH] Ошибка публикации: {e}")
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """Проверяет разрешён ли актив"""
        if settings.ASSETS == '*':
            # Discovery режим: проверяем наличие в watchlist
            return self.discovery.is_in_watchlist(event.chain, event.asset)
        else:
            # Allowlist режим: проверяем наличие в списке
            return event.asset in settings.ASSETS_LIST
    
    def _load_state(self):
        """Загружает состояние из файла"""
        try:
            with open(settings.STATE_FILE, 'r') as f:
                state = json.load(f)
                self.seen_keys = set(state.get("seen_keys", []))
                print(f"📂 [STATE] Загружено {len(self.seen_keys)} dedupe ключей")
        except FileNotFoundError:
            print("📂 [STATE] Файл состояния не найден, начинаем с чистого листа")
            self.seen_keys = set()
        except Exception as e:
            print(f"⚠️  [STATE] Ошибка загрузки состояния: {e}")
            self.seen_keys = set()
    
    def _save_state(self):
        """Сохраняет состояние в файл"""
        try:
            state = {
                "last_seen_timestamp": datetime.utcnow().isoformat(),
                "seen_keys": list(self.seen_keys)[-10000:]  # Сохраняем последние 10K
            }
            with open(settings.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"💾 [STATE] Сохранено {len(state['seen_keys'])} ключей")
        except Exception as e:
            print(f"⚠️  [STATE] Не удалось сохранить состояние: {e}")
    
    async def shutdown(self):
        """Корректное завершение работы"""
        print("\n⏹️  [SHUTDOWN] Остановка системы...")
        self._save_state()
        print("✅ [SHUTDOWN] Состояние сохранено. Завершение.")