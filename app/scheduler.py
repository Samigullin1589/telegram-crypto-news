# app/scheduler.py (МАКСИМАЛЬНО УЛУЧШЕННАЯ ВЕРСИЯ)
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
from app.alerts import get_alert_manager

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
        self.alert_manager = get_alert_manager()
        
        self.publication_queue: List[Dict] = []
        self.seen_keys: set = set()
        self.recent_publications = deque(maxlen=settings.POSTS_PER_HOUR_CAP)
        
        # Статистика
        self.stats = {
            "events_collected": 0,
            "events_qualified": 0,
            "events_published": 0,
            "errors": 0,
            "last_cycle_time": None,
            "start_time": datetime.utcnow()
        }
        
        self._load_state()
    
    async def run(self):
        """Главный цикл работы"""
        print("=" * 80)
        print("🐋 ONE-CHANNEL WHALE MONITOR + NEWS BOT [IMPROVED]")
        print("=" * 80)
        print(f"Режим: {'DISCOVERY (весь рынок)' if settings.ASSETS == '*' else 'ALLOWLIST'}")
        print(f"Канал: {settings.CHAT_ID}")
        print(f"Лимит публикаций: {settings.POSTS_PER_HOUR_CAP}/час")
        print(f"Алерты: включены")
        print("=" * 80)
        
        # Отправляем уведомление о запуске
        try:
            await self.alert_manager.send_startup_notification()
        except Exception as e:
            print(f"⚠️  Не удалось отправить уведомление о запуске: {e}")
        
        tasks = [
            self._discovery_loop(),
            self._whale_monitor_loop(),
            self._stats_reporter_loop(),
            self._health_check_loop(),
        ]
        
        await asyncio.gather(*tasks)
    
    async def _discovery_loop(self):
        """Обновление watchlist"""
        if settings.ASSETS != '*':
            print("⏭️  Discovery отключен (ALLOWLIST режим)")
            return
        
        # УЛУЧШЕНИЕ: Запускаем сразу, не ждём
        try:
            print(f"\n🔄 [DISCOVERY] Первичное обновление watchlist")
            await self.discovery.refresh_watchlist()
        except Exception as e:
            print(f"❌ [DISCOVERY] Ошибка первичного обновления: {e}")
            await self.alert_manager.send_critical_alert(
                "Discovery Error",
                "Не удалось обновить watchlist при старте",
                str(e)
            )
        
        while True:
            try:
                wait_seconds = settings.DISCOVERY_REFRESH_HOURS * 3600
                print(f"⏰ [DISCOVERY] Следующее обновление через {settings.DISCOVERY_REFRESH_HOURS}ч")
                await asyncio.sleep(wait_seconds)
                
                print(f"\n🔄 [DISCOVERY] Плановое обновление watchlist")
                await self.discovery.refresh_watchlist()
                
            except Exception as e:
                print(f"❌ [DISCOVERY] Ошибка: {e}")
                await self.alert_manager.send_critical_alert(
                    "Discovery Error",
                    "Ошибка обновления watchlist",
                    str(e)
                )
                await asyncio.sleep(1800)
    
    async def _whale_monitor_loop(self):
        """Мониторинг крупных перемещений"""
        start_time = datetime.utcnow() - timedelta(minutes=settings.START_FROM_MINUTES_AGO)
        consecutive_errors = 0
        
        while True:
            try:
                print(f"\n📊 [WHALE] Цикл: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                self.stats["last_cycle_time"] = datetime.utcnow()
                
                async with BlockchainMonitor() as monitor:
                    events = await monitor.fetch_events(start_time)
                    self.stats["events_collected"] += len(events)
                    
                    if not events:
                        print("👍 [WHALE] Новых перемещений не найдено")
                    else:
                        await self._process_events(events)
                
                start_time = datetime.utcnow()
                await self._publish_from_queue()
                
                # Сброс счётчика ошибок при успехе
                consecutive_errors = 0
                
                print(f"⏰ [WHALE] Следующая проверка через {settings.POLL_SECONDS}с")
                await asyncio.sleep(settings.POLL_SECONDS)
                
            except Exception as e:
                consecutive_errors += 1
                self.stats["errors"] += 1
                
                print(f"❌ [WHALE] Критическая ошибка ({consecutive_errors}/3): {e}")
                
                # Отправляем алерт при повторяющихся ошибках
                if consecutive_errors >= 3:
                    await self.alert_manager.send_critical_alert(
                        "Monitor Loop Error",
                        f"Критическая ошибка в цикле мониторинга (подряд: {consecutive_errors})",
                        str(e)
                    )
                
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
                try:
                    if settings.DEBUG_FILTERS:
                        print(f"\n🔍 [FILTER] Проверяю: {event.asset} {event.amount_native:,.2f} ≈ ${event.amount_usd:,.0f}")
                    
                    # 1. Дедупликация
                    dedup_key = event.get_dedup_key()
                    if dedup_key in self.seen_keys:
                        filter_stats["dedup"] += 1
                        if settings.DEBUG_FILTERS:
                            print(f"  ❌ Дубликат")
                        continue
                    
                    # 2. Проверка разрешённости актива
                    if not self._is_asset_allowed(event):
                        filter_stats["asset_not_allowed"] += 1
                        if settings.DEBUG_FILTERS:
                            print(f"  ❌ Актив не разрешён")
                        continue
                    
                    # 3. Проверка флагов internal/bridge/reorg
                    if event.is_internal or event.is_bridge or event.is_reorg:
                        filter_stats["internal_bridge"] += 1
                        if settings.DEBUG_FILTERS:
                            print(f"  ❌ Internal/Bridge/Reorg")
                        continue
                    
                    # 4. Обогащение рыночными данными
                    if settings.DEBUG_FILTERS:
                        print(f"  💵 До: ${event.amount_usd:,.0f}, порог ${event.min_usd_threshold:,.0f}")
                    
                    await self.price_provider.enrich_event_with_market_data(event, session)
                    
                    if settings.DEBUG_FILTERS:
                        print(f"  💵 После: ${event.amount_usd:,.0f}, порог ${event.min_usd_threshold:,.0f}")
                    
                    # 5. Проверка порога USD
                    if event.amount_usd < event.min_usd_threshold:
                        filter_stats["below_threshold"] += 1
                        if settings.DEBUG_FILTERS:
                            print(f"  ❌ Ниже порога")
                        continue
                    
                    # ✅ Прошло!
                    filter_stats["passed"] += 1
                    qualified_events.append(event)
                    self.seen_keys.add(dedup_key)
                    
                    if settings.DEBUG_FILTERS:
                        print(f"  ✅ ПРОШЛО!")
                
                except Exception as e:
                    print(f"⚠️  [FILTER] Ошибка обработки события: {e}")
                    self.stats["errors"] += 1
                    continue
            
            # Итоги
            self.stats["events_qualified"] += len(qualified_events)
            
            print(f"✅ [QUALIFY] Прошло фильтры: {len(qualified_events)} событий")
            
            if settings.DEBUG_FILTERS:
                print(f"📊 [STATS] "
                      f"Дубл: {filter_stats['dedup']}, "
                      f"Запрещ: {filter_stats['asset_not_allowed']}, "
                      f"Internal: {filter_stats['internal_bridge']}, "
                      f"Ниже: {filter_stats['below_threshold']}, "
                      f"✅: {filter_stats['passed']}")
            
            if not qualified_events:
                return
            
            # Определение фаз
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            # Скоринг и добавление в очередь
            for event in qualified_events:
                try:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if not self.scorer.should_publish(event, verdict, confidence):
                        if settings.DEBUG_FILTERS:
                            print(f"⏭️  [SKIP] {event.asset}: confidence={confidence}")
                        continue
                    
                    # История
                    history_hint = await self.history_manager.find_similar_event(event, session)
                    if history_hint:
                        event.history_hint = history_hint
                    
                    # Приоритет
                    priority = self.scorer.calculate_priority(event, confidence)
                    
                    self.publication_queue.append({
                        "event": event,
                        "verdict": verdict,
                        "confidence": confidence,
                        "priority": priority,
                        "queued_at": datetime.utcnow()
                    })
                except Exception as e:
                    print(f"⚠️  [SCORE] Ошибка оценки события: {e}")
                    self.stats["errors"] += 1
                    continue
            
            # Сортировка по приоритету
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикует события из очереди"""
        now = datetime.utcnow()
        
        # Очистка старых записей
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        # Проверка лимита
        if len(self.recent_publications) >= settings.POSTS_PER_HOUR_CAP:
            print(f"⏸️  [RATE] Лимит {settings.POSTS_PER_HOUR_CAP}/час достигнут")
            return
        
        # Публикация
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
                        self.stats["events_published"] += 1
                        print(f"✅ [PUBLISHED] {event.asset} ${event.amount_usd:,.0f}")
                    
                    await asyncio.sleep(120)
                    
            except Exception as e:
                print(f"❌ [PUBLISH] Ошибка: {e}")
                self.stats["errors"] += 1
                await self.alert_manager.send_critical_alert(
                    "Publish Error",
                    f"Не удалось опубликовать событие {event.asset}",
                    str(e)
                )
    
    async def _stats_reporter_loop(self):
        """Отправляет ежедневную статистику"""
        
        # Ждём 24 часа с момента старта
        await asyncio.sleep(86400)
        
        while True:
            try:
                await self.alert_manager.send_daily_stats(self.stats)
                
                # Сброс счётчиков
                self.stats["events_collected"] = 0
                self.stats["events_qualified"] = 0
                self.stats["events_published"] = 0
                self.stats["errors"] = 0
                
            except Exception as e:
                print(f"⚠️  [STATS] Ошибка отправки статистики: {e}")
            
            await asyncio.sleep(86400)  # Каждые 24 часа
    
    async def _health_check_loop(self):
        """Проверка здоровья системы"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Каждые 5 минут
                
                now = datetime.utcnow()
                
                # Проверяем, был ли последний цикл недавно
                if self.stats["last_cycle_time"]:
                    time_since_cycle = (now - self.stats["last_cycle_time"]).seconds
                    
                    if time_since_cycle > 600:  # Более 10 минут
                        await self.alert_manager.send_warning(
                            f"⚠️ Последний цикл был {time_since_cycle//60} минут назад. Возможна проблема."
                        )
                
            except Exception as e:
                print(f"⚠️  [HEALTH] Ошибка health check: {e}")
    
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
                print(f"📂 [STATE] Загружено {len(self.seen_keys)} ключей")
        except FileNotFoundError:
            print("📂 [STATE] Новый старт")
            self.seen_keys = set()
        except Exception as e:
            print(f"⚠️  [STATE] Ошибка: {e}")
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
            print(f"💾 [STATE] Сохранено")
        except Exception as e:
            print(f"⚠️  [STATE] Ошибка сохранения: {e}")
    
    async def shutdown(self):
        """Корректное завершение"""
        print("\n⏹️  [SHUTDOWN] Остановка...")
        self._save_state()
        print("✅ [SHUTDOWN] Готово")