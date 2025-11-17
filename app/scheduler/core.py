# app/scheduler/core.py
"""
Integrated Scheduler Core
Main coordinator for all monitoring systems
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict, deque

from app.config import config
from app.scheduler.helpers import (
    load_state, save_state, 
    print_startup_banner, print_shutdown_summary
)
from app.scheduler.wallet_db import WalletDatabase
from app.scheduler.adaptive import AdaptiveThresholds
from app.scheduler.whale_monitor import WhaleMonitor
from app.scheduler.trading import TradingSystem
from app.scheduler.hyperliquid import HyperliquidSystem

logger = logging.getLogger(__name__)


class IntegratedScheduler:
    """Главный координатор всех систем мониторинга"""
    
    def __init__(self):
        logger.info("\n" + "="*80)
        logger.info("🚀 INTEGRATED SCHEDULER v4.4 - INITIALIZATION")
        logger.info("="*80 + "\n")
        
        self._shutdown_flag = False
        self.tasks = []
        
        self._init_whale_components()
        self._init_optional_features()
        self._init_stats()
        
        self.whale_monitor = WhaleMonitor(self._get_components())
        self.trading_system = TradingSystem(self._get_components())
        self.hyperliquid_system = HyperliquidSystem(self._get_components())
        
        logger.info("\n" + "="*80)
        logger.info("✅ INITIALIZATION COMPLETE")
        logger.info("="*80 + "\n")
    
    def _init_whale_components(self):
        """Инициализация компонентов whale monitoring"""
        logger.info("📦 [1/3] Инициализация Whale Monitoring...")

        # Пытаемся импортировать компоненты с обработкой ошибок
        try:
            from app.whales.discovery import DiscoveryEngine
            self.discovery = DiscoveryEngine()
        except Exception as e:
            logger.warning(f"   ⚠️  Discovery Engine не загружен: {e}")
            self.discovery = None

        try:
            from app.whales.score import EventScorer
            self.scorer = EventScorer()
        except Exception as e:
            logger.error(f"   ❌ EventScorer не загружен: {e}")
            self.scorer = None

        try:
            from app.whales.price import PriceProvider
            self.price_provider = PriceProvider()
        except Exception as e:
            logger.error(f"   ❌ PriceProvider не загружен: {e}")
            self.price_provider = None

        try:
            from app.whales.news import NewsGate
            self.news_gate = NewsGate()
        except Exception as e:
            logger.warning(f"   ⚠️  NewsGate не загружен: {e}")
            self.news_gate = None

        try:
            from app.whales.publisher.core import WhalePublisher
            self.publisher = WhalePublisher()
        except Exception as e:
            logger.error(f"   ❌ WhalePublisher не загружен: {e}")
            self.publisher = None

        try:
            from app.charts.sparkline import SparklineRenderer
            self.chart_renderer = SparklineRenderer()
        except Exception as e:
            logger.warning(f"   ⚠️  SparklineRenderer не загружен: {e}")
            self.chart_renderer = None

        try:
            from app.whales.history.manager import HistoryManager
            self.history_manager = HistoryManager()
        except Exception as e:
            logger.error(f"   ❌ HistoryManager не загружен: {e}")
            self.history_manager = None

        # EventEnricher - КРИТИЧЕСКИЙ компонент для обогащения
        try:
            from app.scheduler.whale_components.event_enricher import EventEnricher
            # Создаем enricher, передавая компоненты
            enricher_components = {
                'price_provider': self.price_provider,
                'history_manager': self.history_manager,
                'news_gate': self.news_gate
            }
            self.enricher = EventEnricher(enricher_components)
            logger.info("   ✓ EventEnricher created")
        except Exception as e:
            logger.error(f"   ❌ EventEnricher не загружен: {e}")
            self.enricher = None

        if config.is_feature_enabled('adaptive_thresholds'):
            self.adaptive_thresholds = AdaptiveThresholds()
        else:
            self.adaptive_thresholds = None

        if config.is_feature_enabled('smart_discovery') or config.is_feature_enabled('validation'):
            self.wallet_db = WalletDatabase()
        else:
            self.wallet_db = None

        self.seen_keys = load_state()

        logger.info("   ✓ Whale components loaded")
    
    def _init_optional_features(self):
        """Инициализация опциональных возможностей"""
        logger.info("\n📦 [2/3] Инициализация Optional Features...")
        
        self.rate_limiter = None
        self.alert_manager = None
        
        logger.info("   ✓ Optional features initialized")
    
    def _init_stats(self):
        """Инициализация статистики"""
        logger.info("\n📦 [3/3] Инициализация Statistics...")
        
        self.stats = {
            "events_collected": 0,
            "events_qualified": 0,
            "events_published": 0,
            "events_successful": 0,
            "events_failed": 0,
            "errors": 0,
            "trading_signals_generated": 0,
            "trading_signals_sent": 0,
            "news_cycles": 0,
            "news_articles_processed": 0,
            "news_articles_published": 0,
            "last_cycle_time": None,
            "last_news_cycle": None,
            "start_time": datetime.utcnow()
        }
        
        if config.is_feature_enabled('performance_tracking'):
            self.pending_verification = deque(maxlen=100)
        else:
            self.pending_verification = None
        
        logger.info("   ✓ Statistics initialized")
    
    def _get_components(self) -> Dict:
        """Получение всех компонентов для передачи в подсистемы"""
        components = {
            'discovery': self.discovery,
            'scorer': self.scorer,
            'price_provider': self.price_provider,
            'news_gate': self.news_gate,
            'publisher': self.publisher,
            'chart_renderer': self.chart_renderer,
            'history_manager': self.history_manager,
            'enricher': self.enricher,  # КРИТИЧЕСКИ ВАЖНО для PublicationManager!
            'adaptive_thresholds': self.adaptive_thresholds,
            'wallet_db': self.wallet_db,
            'seen_keys': self.seen_keys,
            'rate_limiter': self.rate_limiter,
            'pending_verification': self.pending_verification
        }

        # DEBUG: Логируем какие компоненты реально не None
        loaded = [k for k, v in components.items() if v is not None]
        logger.debug(f"📦 [COMPONENTS] Передаем {len(loaded)}/{len(components)}: {', '.join(loaded)}")

        return components
    
    def set_rate_limiter(self, rate_limiter):
        """Установка rate limiter"""
        self.rate_limiter = rate_limiter
        logger.info("✅ [SCHEDULER] Rate limiter подключен")
    
    async def start(self):
        """Запуск всех циклов"""
        print_startup_banner(self._get_components())
        
        self.tasks = [
            asyncio.create_task(self._whale_monitor_loop(), name="whale_monitor"),
            asyncio.create_task(self._health_check_loop(), name="health"),
        ]
        
        if self.trading_system.enabled:
            self.tasks.extend([
                asyncio.create_task(self._trading_signal_loop(), name="trading_signals"),
                asyncio.create_task(self._position_management_loop(), name="positions"),
            ])
        
        if self.hyperliquid_system.enabled:
            self.tasks.extend([
                asyncio.create_task(self._hyperliquid_whale_loop(), name="hyperliquid_whale"),
                asyncio.create_task(self._hyperliquid_liquidations_loop(), name="hyperliquid_liq"),
            ])
        
        logger.info(f"\n🚀 [SCHEDULER] Запущено {len(self.tasks)} циклов:")
        for task in self.tasks:
            logger.info(f"   • {task.get_name()}")
        logger.info("")
    
    async def run(self):
        """Главный цикл"""
        await self.start()
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("\n⏹️ [SCHEDULER] Получен сигнал остановки")
        except Exception as e:
            logger.error(f"\n❌ [SCHEDULER] Критическая ошибка: {e}")
        finally:
            await self.shutdown()
    
    async def run_cycle(self):
        """Выполнить один цикл whale monitoring (для manual запуска)"""
        self.stats["last_cycle_time"] = datetime.utcnow()
        start_time = datetime.utcnow() - timedelta(seconds=config.whale.poll_seconds)
        chains = config.blockchain.enabled_chains
        
        result = await self.whale_monitor.run_cycle(start_time, chains)
        
        self.stats["events_collected"] += result.get('events_collected', 0)
        
        return result
    
    async def run_news_cycle(self):
        """Выполнить один цикл обработки новостей (для NewsProcessor)"""
        self.stats["last_news_cycle"] = datetime.utcnow()
        self.stats["news_cycles"] += 1
        
        now = datetime.utcnow()
        recent_pubs = self.whale_monitor.recent_publications
        
        while recent_pubs and (now - recent_pubs[0]).seconds > 3600:
            recent_pubs.popleft()
        
        available_slots = config.whale.posts_per_hour_cap - len(recent_pubs)
        
        return {
            'success': available_slots > 0,
            'available_slots': available_slots,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def record_news_publication(self):
        """Регистрация публикации новости"""
        self.whale_monitor.recent_publications.append(datetime.utcnow())
        self.stats["news_articles_published"] += 1
    
    def record_news_article_processed(self):
        """Регистрация обработанной статьи"""
        self.stats["news_articles_processed"] += 1
    
    async def _whale_monitor_loop(self):
        """Основной цикл мониторинга whale"""
        start_time = datetime.utcnow() - timedelta(minutes=config.whale.start_from_minutes_ago)
        
        while not self._shutdown_flag:
            try:
                logger.info(f"\n📊 [WHALE] Цикл: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

                chains = config.blockchain.enabled_chains
                result = await self.whale_monitor.run_cycle(start_time, chains)
                
                self.stats["events_collected"] += result.get('events_collected', 0)
                
                start_time = datetime.utcnow()
                
                logger.info(f"⏰ [WHALE] Следующая проверка через {config.whale.poll_seconds}с")
                await asyncio.sleep(config.whale.poll_seconds)
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"❌ [WHALE] Ошибка: {e}")
                await asyncio.sleep(300)
    
    async def _trading_signal_loop(self):
        """Цикл генерации торговых сигналов"""
        await asyncio.sleep(300)
        
        check_interval = config.trading.signal_interval_hours * 3600
        
        while not self._shutdown_flag:
            try:
                result = await self.trading_system.run_signal_cycle()
                
                self.stats["trading_signals_generated"] += result.get('signals_generated', 0)
                self.stats["trading_signals_sent"] += result.get('signals_sent', 0)
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"❌ [TRADING] Ошибка: {e}")
                await asyncio.sleep(600)
    
    async def _position_management_loop(self):
        """Цикл управления позициями"""
        await asyncio.sleep(60)
        
        update_interval = config.trading.position_update_interval_seconds
        
        while not self._shutdown_flag:
            try:
                await self.trading_system.update_positions()
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"❌ [POSITIONS] Ошибка: {e}")
                await asyncio.sleep(60)
    
    async def _hyperliquid_whale_loop(self):
        """Цикл мониторинга whale activity на Hyperliquid"""
        await asyncio.sleep(240)
        
        while not self._shutdown_flag:
            try:
                await self.hyperliquid_system.check_whale_activity()
                await asyncio.sleep(600)
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"❌ [HYPERLIQUID] Whale error: {e}")
                await asyncio.sleep(300)
    
    async def _hyperliquid_liquidations_loop(self):
        """Цикл мониторинга ликвидаций на Hyperliquid"""
        await asyncio.sleep(360)
        
        while not self._shutdown_flag:
            try:
                await self.hyperliquid_system.check_liquidations()
                await asyncio.sleep(600)
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"❌ [HYPERLIQUID] Liquidations error: {e}")
                await asyncio.sleep(300)
    
    async def _health_check_loop(self):
        """Проверка здоровья системы"""
        while not self._shutdown_flag:
            try:
                await asyncio.sleep(300)
                
                if self.stats["last_cycle_time"]:
                    silence = (datetime.utcnow() - self.stats["last_cycle_time"]).seconds
                    if silence > 3600:
                        logger.warning(f"⚠️ [HEALTH] Молчание {silence//60} минут")
            
            except Exception as e:
                logger.error(f"⚠️ [HEALTH] Ошибка: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n⏹️ [SCHEDULER] Shutdown initiated...")
        self._shutdown_flag = True
        
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        save_state(self.seen_keys)
        print_shutdown_summary(self.stats)
    
    async def cleanup(self):
        """Cleanup для совместимости"""
        await self.shutdown()