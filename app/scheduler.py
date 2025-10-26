# app/scheduler.py
"""
INTELLIGENT WHALE SCHEDULER v3.0 - Self-Learning System with Multi-Chain Support

РЕВОЛЮЦИОННЫЕ ВОЗМОЖНОСТИ:
✅ Multi-Chain Support (7+ blockchains)
✅ Advanced Analytics (Sentiment, Risk, Correlation, Anomaly)
✅ Smart Money Discovery - автопоиск успешных трейдеров
✅ Validation Engine - автоочистка базы от мусора
✅ Performance Tracking - отслеживание результатов
✅ Adaptive Thresholds - динамические пороги
✅ Learning System - самообучение на ошибках
✅ Cross-Chain Wallet Tracking - мониторинг на всех chains
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from collections import deque, defaultdict
from pathlib import Path
import statistics

from app import settings

# Основные импорты (всегда доступны)
from app.whales.discovery import DiscoveryEngine
from app.whales.monitor import BlockchainMonitor
from app.whales.normalize import WhaleEvent
from app.whales.score import EventScorer
from app.whales.price import PriceProvider
from app.whales.news import NewsGate
from app.whales.publish import WhalePublisher
from app.whales.history import HistoryManager
from app.charts.sparkline import SparklineRenderer

# Multi-Chain Support
try:
    from app.chains import initialize_all_chains, unified_api, get_supported_chains
    CHAINS_AVAILABLE = True
except ImportError:
    CHAINS_AVAILABLE = False
    print("⚠️  Multi-Chain Support не найден")

# Advanced Analytics
try:
    from app.analytics import get_analytics_engine, AnalyticsEngine
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    print("⚠️  Analytics Engine не найден")

# Mining System
try:
    from app.mining.integration import create_mining_system
    MINING_AVAILABLE = True
except ImportError:
    MINING_AVAILABLE = False
    print("⚠️  Mining System не найден")

# Алерты
try:
    from app.alerts import get_alert_manager_sync
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False
    print("⚠️  Alerts не найдены - работаем без них")

# Smart Money Discovery
try:
    from app.whales.smart_discovery import SmartMoneyDiscovery
    SMART_DISCOVERY_AVAILABLE = True
except ImportError:
    SMART_DISCOVERY_AVAILABLE = False
    print("⚠️  Smart Discovery не найден - работаем без него")


class AdaptiveThresholds:
    """
    Динамические пороги, адаптирующиеся под рынок и производительность
    """
    
    def __init__(self):
        self.market_regime = "sideways"  # bull / bear / sideways
        self.performance_history = deque(maxlen=100)
        
        # Базовые пороги
        self.base_thresholds = {
            "min_confidence": settings.ADAPTIVE_BASE_MIN_CONFIDENCE,
            "min_size_rel": settings.ADAPTIVE_BASE_MIN_SIZE_REL,
            "min_volume_24h": settings.ADAPTIVE_BASE_MIN_VOLUME_24H
        }
        
        # Модификаторы для разных режимов
        self.regime_modifiers = {
            "bull": {
                "min_confidence": settings.ADAPTIVE_BULL_CONFIDENCE_MODIFIER,
                "min_size_rel": settings.ADAPTIVE_BULL_SIZE_REL_MODIFIER,
                "min_volume_24h": settings.ADAPTIVE_BULL_VOLUME_MODIFIER
            },
            "bear": {
                "min_confidence": settings.ADAPTIVE_BEAR_CONFIDENCE_MODIFIER,
                "min_size_rel": settings.ADAPTIVE_BEAR_SIZE_REL_MODIFIER,
                "min_volume_24h": settings.ADAPTIVE_BEAR_VOLUME_MODIFIER
            },
            "sideways": {
                "min_confidence": 0,
                "min_size_rel": 0,
                "min_volume_24h": 1.0
            }
        }
        
        print(f"⚙️  [ADAPTIVE] Инициализирован. Базовые пороги: "
              f"confidence≥{self.base_thresholds['min_confidence']}, "
              f"size_rel≥{self.base_thresholds['min_size_rel']:.2%}")
    
    def detect_market_regime(self, btc_change_7d: float) -> str:
        """Определяет режим рынка на основе изменения BTC"""
        if btc_change_7d > settings.ADAPTIVE_BULL_THRESHOLD:
            return "bull"
        elif btc_change_7d < settings.ADAPTIVE_BEAR_THRESHOLD:
            return "bear"
        else:
            return "sideways"
    
    def update_regime(self, btc_change_7d: float):
        """Обновляет режим рынка"""
        old_regime = self.market_regime
        self.market_regime = self.detect_market_regime(btc_change_7d)
        
        if old_regime != self.market_regime:
            print(f"📊 [REGIME] Режим рынка изменён: {old_regime} → {self.market_regime}")
    
    def get_current_thresholds(self) -> Dict:
        """Возвращает текущие пороги с учётом режима и производительности"""
        
        modifiers = self.regime_modifiers[self.market_regime]
        
        thresholds = {
            "min_confidence": int(self.base_thresholds["min_confidence"] + modifiers["min_confidence"]),
            "min_size_rel": self.base_thresholds["min_size_rel"] + modifiers["min_size_rel"],
            "min_volume_24h": int(self.base_thresholds["min_volume_24h"] * modifiers["min_volume_24h"])
        }
        
        # Адаптация на основе производительности
        if len(self.performance_history) >= settings.ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION:
            recent_accuracy = self._calculate_recent_accuracy()
            
            if recent_accuracy < settings.ADAPTIVE_LOW_ACCURACY_THRESHOLD:
                adjustment = settings.ADAPTIVE_ACCURACY_ADJUSTMENT
                thresholds["min_confidence"] += adjustment
                print(f"⚠️  [ADAPTIVE] Низкая точность ({recent_accuracy:.1%}), "
                      f"повышаю min_confidence до {thresholds['min_confidence']}")
            
            elif recent_accuracy > settings.ADAPTIVE_HIGH_ACCURACY_THRESHOLD:
                adjustment = settings.ADAPTIVE_ACCURACY_ADJUSTMENT
                thresholds["min_confidence"] = max(30, thresholds["min_confidence"] - adjustment)
                print(f"✅ [ADAPTIVE] Высокая точность ({recent_accuracy:.1%}), "
                      f"понижаю min_confidence до {thresholds['min_confidence']}")
        
        return thresholds
    
    def add_performance_result(self, signal_data: Dict):
        """Добавляет результат сигнала для обучения"""
        self.performance_history.append(signal_data)
    
    def _calculate_recent_accuracy(self) -> float:
        """Считает точность последних N сигналов"""
        min_signals = settings.ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION
        
        if len(self.performance_history) < min_signals:
            return 0.5
        
        recent = list(self.performance_history)[-min_signals:]
        successful = sum(1 for s in recent if s.get("success", False))
        
        return successful / len(recent)
    
    def get_stats(self) -> Dict:
        """Статистика адаптивной системы"""
        if not self.performance_history:
            return {
                "regime": self.market_regime,
                "signals_tracked": 0,
                "accuracy": 0.0,
                "current_thresholds": self.get_current_thresholds()
            }
        
        successful = sum(1 for s in self.performance_history if s.get("success", False))
        
        return {
            "regime": self.market_regime,
            "signals_tracked": len(self.performance_history),
            "accuracy": successful / len(self.performance_history),
            "current_thresholds": self.get_current_thresholds()
        }


class WalletDatabase:
    """База данных отслеживаемых кошельков с простым JSON хранилищем"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = settings.WALLET_DB_JSON_PATH
        
        self.db_path = Path(db_path)
        self.wallets: List[Dict] = []
        self._load()
    
    def _load(self):
        """Загружает кошельки из файла"""
        try:
            if self.db_path.exists():
                with open(self.db_path, 'r') as f:
                    self.wallets = json.load(f)
                print(f"📂 [WALLET_DB] Загружено {len(self.wallets)} кошельков")
            else:
                print("📂 [WALLET_DB] Новая база данных")
                self.wallets = []
                self._save()
        except Exception as e:
            print(f"⚠️  [WALLET_DB] Ошибка загрузки: {e}")
            self.wallets = []
    
    def _save(self):
        """Сохраняет кошельки в файл"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.db_path, 'w') as f:
                json.dump(self.wallets, f, indent=2)
        except Exception as e:
            print(f"⚠️  [WALLET_DB] Ошибка сохранения: {e}")
    
    def add_wallet(self, wallet_stats) -> bool:
        """Добавляет новый кошелёк"""
        existing = self.get_wallet(wallet_stats.address, wallet_stats.chain)
        if existing:
            return False
        
        if settings.WALLET_AUTO_PRUNE and len(self.wallets) >= settings.WALLET_MAX_TRACKED:
            self._prune_worst_wallets(10)
        
        wallet_data = {
            "address": wallet_stats.address,
            "chain": wallet_stats.chain,
            "roi_30d": wallet_stats.roi_30d,
            "roi_90d": getattr(wallet_stats, 'roi_90d', 0),
            "win_rate": wallet_stats.win_rate,
            "total_trades": wallet_stats.total_trades,
            "specialization": getattr(wallet_stats, 'specialization', 'general'),
            "discovered_at": datetime.utcnow().isoformat(),
            "discovered_via": wallet_stats.best_trades[0]["token"] if hasattr(wallet_stats, 'best_trades') and wallet_stats.best_trades else "unknown",
            "last_trade_at": wallet_stats.last_trade_at.isoformat() if hasattr(wallet_stats.last_trade_at, 'isoformat') else str(wallet_stats.last_trade_at),
            "is_active": True,
            "score": settings.WALLET_INITIAL_SCORE
        }
        
        self.wallets.append(wallet_data)
        self._save()
        
        print(f"✅ [WALLET_DB] Добавлен: {wallet_stats.address[:10]}... (ROI: {wallet_stats.roi_30d:.1%})")
        return True
    
    def get_wallet(self, address: str, chain: str) -> Optional[Dict]:
        """Получает кошелёк по адресу"""
        for wallet in self.wallets:
            if wallet["address"].lower() == address.lower() and wallet["chain"] == chain:
                return wallet
        return None
    
    def get_active_wallets(self) -> List[Dict]:
        """Возвращает активные кошельки"""
        return [w for w in self.wallets if w.get("is_active", True)]
    
    def deactivate_wallet(self, address: str, chain: str, reason: str):
        """Деактивирует кошелёк"""
        wallet = self.get_wallet(address, chain)
        if wallet:
            wallet["is_active"] = False
            wallet["deactivated_at"] = datetime.utcnow().isoformat()
            wallet["deactivation_reason"] = reason
            self._save()
            print(f"❌ [WALLET_DB] Деактивирован: {address[:10]}... ({reason})")
    
    def update_wallet_score(self, address: str, chain: str, new_score: int):
        """Обновляет скор кошелька"""
        wallet = self.get_wallet(address, chain)
        if wallet:
            old_score = wallet.get("score", settings.WALLET_INITIAL_SCORE)
            wallet["score"] = max(settings.WALLET_MIN_SCORE, min(settings.WALLET_MAX_SCORE, new_score))
            wallet["score_updated_at"] = datetime.utcnow().isoformat()
            self._save()
            
            if abs(new_score - old_score) > 10:
                print(f"📊 [WALLET_DB] Скор обновлён: {address[:10]}... {old_score} → {new_score}")
    
    def _prune_worst_wallets(self, count: int):
        """Удаляет худшие кошельки"""
        active = self.get_active_wallets()
        if len(active) <= count:
            return
        
        sorted_wallets = sorted(active, key=lambda w: w.get('score', 50))
        
        for wallet in sorted_wallets[:count]:
            self.deactivate_wallet(
                wallet['address'],
                wallet['chain'],
                'auto_pruned_low_score'
            )


class WhaleScheduler:
    """
    Главный координатор с полной интеграцией всех систем
    """
    
    def __init__(self):
        # Основные компоненты
        self.discovery = DiscoveryEngine()
        self.scorer = EventScorer()
        self.price_provider = PriceProvider()
        self.news_gate = NewsGate()
        self.publisher = WhalePublisher()
        self.chart_renderer = SparklineRenderer()
        self.history_manager = HistoryManager()
        
        # Адаптивные системы
        if settings.ADAPTIVE_THRESHOLDS_ENABLED:
            self.adaptive_thresholds = AdaptiveThresholds()
        else:
            self.adaptive_thresholds = None
        
        if settings.SMART_DISCOVERY_ENABLED or settings.VALIDATION_ENABLED:
            self.wallet_db = WalletDatabase()
        else:
            self.wallet_db = None
        
        # Multi-Chain Support
        self.chains_enabled = False
        if CHAINS_AVAILABLE and hasattr(settings, 'ETHERSCAN_API_KEY'):
            try:
                # Инициализируем chains
                api_keys = {
                    "base": getattr(settings, 'BASE_API_KEY', settings.ETHERSCAN_API_KEY),
                    "arbitrum": getattr(settings, 'ARBITRUM_API_KEY', settings.ETHERSCAN_API_KEY),
                    "optimism": getattr(settings, 'OPTIMISM_API_KEY', settings.ETHERSCAN_API_KEY),
                    "avalanche": getattr(settings, 'AVALANCHE_API_KEY', None),
                    "polygon": getattr(settings, 'POLYGON_API_KEY', None)
                }
                
                solana_rpc = getattr(settings, 'SOLANA_RPC_URLS', None)
                
                initialize_all_chains(solana_rpc=solana_rpc, api_keys=api_keys)
                self.unified_api = unified_api
                self.supported_chains = get_supported_chains()
                self.chains_enabled = True
                
                print(f"✅ [MULTI-CHAIN] Поддержка включена: {', '.join(self.supported_chains)}")
            except Exception as e:
                print(f"⚠️  [MULTI-CHAIN] Ошибка инициализации: {e}")
                self.chains_enabled = False
        
        # Advanced Analytics
        self.analytics_enabled = False
        if ANALYTICS_AVAILABLE:
            try:
                self.analytics_engine = get_analytics_engine()
                self.analytics_enabled = True
                print("✅ [ANALYTICS] Engine инициализирован")
            except Exception as e:
                print(f"⚠️  [ANALYTICS] Ошибка: {e}")
                self.analytics_enabled = False
        
        # Mining System
        self.mining_system = None
        if MINING_AVAILABLE and self.wallet_db:
            try:
                self.mining_system = create_mining_system(self.wallet_db)
                print("✅ [MINING] System инициализирован")
            except Exception as e:
                print(f"⚠️  [MINING] Ошибка: {e}")
        
        # Smart Money Discovery
        self.smart_discovery = None
        if SMART_DISCOVERY_AVAILABLE and settings.SMART_DISCOVERY_ENABLED:
            if hasattr(settings, 'ETHERSCAN_API_KEY') and settings.ETHERSCAN_API_KEY:
                self.smart_discovery = SmartMoneyDiscovery(
                    etherscan_key=settings.ETHERSCAN_API_KEY,
                    coingecko_key=getattr(settings, 'COINGECKO_API_KEY', None)
                )
                print("✅ [SMART_DISCOVERY] Инициализирован")
            else:
                print("⚠️  [SMART_DISCOVERY] Отключен (нет ETHERSCAN_API_KEY)")
        
        # Алерты
        if ALERTS_AVAILABLE:
            self.alert_manager = get_alert_manager_sync(settings.ADMIN_CHAT_ID)
        else:
            self.alert_manager = None
        
        # Очереди и кэши
        self.publication_queue: List[Dict] = []
        self.seen_keys: Set[str] = set()
        self.recent_publications = deque(maxlen=settings.POSTS_PER_HOUR_CAP)
        
        # Статистика
        self.stats = {
            "events_collected": 0,
            "events_qualified": 0,
            "events_published": 0,
            "events_successful": 0,
            "events_failed": 0,
            "wallets_discovered": 0,
            "wallets_removed": 0,
            "errors": 0,
            "last_cycle_time": None,
            "last_discovery_run": None,
            "last_validation_run": None,
            "last_smart_discovery_run": None,
            "start_time": datetime.utcnow(),
            "analytics_calls": 0,
            "chains_events": defaultdict(int)
        }
        
        # Очередь для проверки результатов
        if settings.PERFORMANCE_TRACKING_ENABLED:
            self.pending_verification = deque(maxlen=settings.PERFORMANCE_HISTORY_SIZE)
        else:
            self.pending_verification = None
        
        self._shutdown_flag = False
        
        self._load_state()
        
        print("🐋 [SCHEDULER] Инициализирован с полной интеграцией")
    
    async def run(self):
        """Главный цикл с интеллектуальными компонентами"""
        
        self._print_banner()
        
        # Отправляем уведомление о запуске
        if self.alert_manager and settings.SEND_STARTUP_NOTIFICATION:
            try:
                await self.alert_manager.send_startup_notification()
            except Exception as e:
                print(f"⚠️  Не удалось отправить startup notification: {e}")
        
        # Запускаем параллельные циклы
        tasks = [
            asyncio.create_task(self._discovery_loop(), name="discovery"),
            asyncio.create_task(self._whale_monitor_loop(), name="whale_monitor"),
            asyncio.create_task(self._stats_reporter_loop(), name="stats"),
            asyncio.create_task(self._health_check_loop(), name="health"),
        ]
        
        # Добавляем опциональные циклы
        if settings.ADAPTIVE_THRESHOLDS_ENABLED:
            tasks.append(asyncio.create_task(self._market_regime_updater_loop(), name="regime_updater"))
        
        if settings.PERFORMANCE_TRACKING_ENABLED:
            tasks.append(asyncio.create_task(self._performance_tracker_loop(), name="performance"))
        
        if settings.VALIDATION_ENABLED and self.wallet_db:
            tasks.append(asyncio.create_task(self._validation_loop(), name="validation"))
        
        if settings.SMART_DISCOVERY_ENABLED and self.smart_discovery:
            tasks.append(asyncio.create_task(self._smart_discovery_loop(), name="smart_discovery"))
        
        # НОВОЕ: Mining system loop
        if self.mining_system and MINING_AVAILABLE:
            tasks.append(asyncio.create_task(self._mining_loop(), name="mining"))
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("\n⏹️  [SCHEDULER] Получен сигнал остановки")
        except Exception as e:
            print(f"\n❌ [SCHEDULER] Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._save_state()
    
    async def _whale_monitor_loop(self):
        """Основной цикл мониторинга крупных перемещений"""
        
        start_time = datetime.utcnow() - timedelta(minutes=settings.START_FROM_MINUTES_AGO)
        consecutive_errors = 0
        
        while not self._shutdown_flag:
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
                
                consecutive_errors = 0
                
                print(f"⏰ [WHALE] Следующая проверка через {settings.POLL_SECONDS}с")
                await asyncio.sleep(settings.POLL_SECONDS)
                
            except Exception as e:
                consecutive_errors += 1
                self.stats["errors"] += 1
                
                print(f"❌ [WHALE] Ошибка ({consecutive_errors}/3): {e}")
                
                if consecutive_errors >= 3 and self.alert_manager:
                    try:
                        await self.alert_manager.send_critical_alert(
                            "Monitor Loop Error",
                            f"Критическая ошибка в цикле ({consecutive_errors})",
                            str(e)
                        )
                    except:
                        pass
                
                await asyncio.sleep(300)
    
    async def _process_events(self, events: List[WhaleEvent]):
        """Обработка событий с полной интеграцией analytics и multi-chain"""
        
        print(f"🔄 [PIPELINE] Обработка {len(events)} событий")
        
        # Получаем текущие пороги
        if self.adaptive_thresholds:
            thresholds = self.adaptive_thresholds.get_current_thresholds()
            print(f"⚙️  [THRESHOLDS] Confidence≥{thresholds['min_confidence']}, "
                  f"SizeRel≥{thresholds['min_size_rel']:.2%}, "
                  f"Volume≥${thresholds['min_volume_24h']:,}")
        else:
            thresholds = {
                "min_confidence": 30,
                "min_size_rel": 0.10,
                "min_volume_24h": 1_000_000
            }
        
        async with aiohttp.ClientSession() as session:
            qualified_events = []
            
            filter_stats = {
                "dedup": 0,
                "asset_not_allowed": 0,
                "internal_bridge": 0,
                "price_failed": 0,
                "below_threshold": 0,
                "confidence_too_low": 0,
                "risk_too_high": 0,
                "passed": 0
            }
            
            for event in events:
                try:
                    # Дедупликация
                    dedup_key = event.get_dedup_key()
                    if dedup_key in self.seen_keys:
                        filter_stats["dedup"] += 1
                        continue
                    
                    # Проверка разрешённости актива
                    if not self._is_asset_allowed(event):
                        filter_stats["asset_not_allowed"] += 1
                        continue
                    
                    # Фильтр внутренних/bridge
                    if event.is_internal or event.is_bridge or event.is_reorg:
                        filter_stats["internal_bridge"] += 1
                        continue
                    
                    # Обогащение данными
                    await self.price_provider.enrich_event_with_market_data(event, session)
                    
                    # Базовая проверка размера
                    if event.amount_usd < event.min_usd_threshold:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    # Проверка confidence
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if confidence < thresholds["min_confidence"]:
                        filter_stats["confidence_too_low"] += 1
                        continue
                    
                    # Проверка размера относительно объёма
                    size_rel = event.amount_usd / event.market.volume_24h_usd if event.market.volume_24h_usd else 0
                    
                    if size_rel < thresholds["min_size_rel"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    if event.market.volume_24h_usd < thresholds["min_volume_24h"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    # ================================================================
                    # НОВОЕ: ADVANCED ANALYTICS INTEGRATION
                    # ================================================================
                    
                    if self.analytics_enabled:
                        try:
                            # Подготавливаем данные для аналитики
                            wallet_data = None
                            if self.wallet_db:
                                wallet = self.wallet_db.get_wallet(event.from_address, event.chain)
                                if wallet:
                                    wallet_data = {
                                        "score": wallet.get("score", 50),
                                        "roi_30d": wallet.get("roi_30d", 0),
                                        "win_rate": wallet.get("win_rate", 0.5)
                                    }
                            
                            signal_data = {
                                "asset": event.asset,
                                "confidence": confidence,
                                "size_usd": event.amount_usd,
                                "wallet_data": wallet_data,
                                "market_data": {
                                    "volatility": getattr(event.market, 'volatility', 30),
                                    "volume_24h": event.market.volume_24h_usd,
                                    "market_cap": getattr(event.market, 'market_cap_usd', 0),
                                    "price_change_24h": event.market.price_change_24h_pct
                                }
                            }
                            
                            # Запускаем полный анализ
                            analytics_result = self.analytics_engine.analyze_signal(
                                signal_data,
                                check_correlations=True,
                                check_anomalies=True
                            )
                            
                            self.stats["analytics_calls"] += 1
                            
                            # Фильтруем по risk score
                            risk_score = analytics_result["risk"]["risk_score"]
                            
                            if risk_score > 85:
                                filter_stats["risk_too_high"] += 1
                                print(f"⚠️  [RISK] Пропускаю {event.asset} - риск {risk_score}/100")
                                continue
                            
                            # Добавляем аналитику к событию
                            event.analytics = analytics_result
                            event.final_score = analytics_result["final_score"]
                            
                            print(f"📊 [ANALYTICS] {event.asset}: "
                                  f"Score={analytics_result['final_score']}/100, "
                                  f"Risk={risk_score}/100, "
                                  f"Sentiment={analytics_result['sentiment']['label']}")
                        
                        except Exception as e:
                            print(f"⚠️  [ANALYTICS] Ошибка анализа: {e}")
                            # Продолжаем без аналитики
                    
                    # ================================================================
                    # НОВОЕ: CROSS-CHAIN WALLET TRACKING
                    # ================================================================
                    
                    if self.chains_enabled and hasattr(event, 'from_address'):
                        try:
                            # Проверяем активность кошелька на других chains
                            cross_chain_analysis = await self.unified_api.analyze_wallet_cross_chain(
                                event.from_address
                            )
                            
                            if cross_chain_analysis["active_chains_count"] >= 3:
                                print(f"🏆 [CROSS-CHAIN] Sophisticated trader detected: "
                                      f"{event.from_address[:10]}... "
                                      f"(active on {cross_chain_analysis['active_chains_count']} chains)")
                                
                                # Повышаем приоритет
                                event.cross_chain_score = cross_chain_analysis["risk_score"]
                        
                        except Exception as e:
                            print(f"⚠️  [CROSS-CHAIN] Ошибка анализа: {e}")
                    
                    # Прошло все фильтры
                    filter_stats["passed"] += 1
                    qualified_events.append(event)
                    self.seen_keys.add(dedup_key)
                    
                    # Статистика по chains
                    self.stats["chains_events"][event.chain] += 1
                
                except Exception as e:
                    print(f"⚠️  [FILTER] Ошибка обработки: {e}")
                    self.stats["errors"] += 1
                    continue
            
            self.stats["events_qualified"] += len(qualified_events)
            
            print(f"✅ [QUALIFY] Прошло фильтры: {len(qualified_events)} событий")
            print(f"📊 [STATS] "
                  f"Дубл: {filter_stats['dedup']}, "
                  f"LowConf: {filter_stats['confidence_too_low']}, "
                  f"HighRisk: {filter_stats['risk_too_high']}, "
                  f"Ниже: {filter_stats['below_threshold']}, "
                  f"✅: {filter_stats['passed']}")
            
            if not qualified_events:
                return
            
            # Определение фаз
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            # Добавление в очередь публикации
            for event in qualified_events:
                try:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if not self.scorer.should_publish(event, verdict, confidence):
                        continue
                    
                    # История
                    history_hint = await self.history_manager.find_similar_event(event, session)
                    if history_hint:
                        event.history_hint = history_hint
                    
                    # Приоритет с учётом analytics
                    if hasattr(event, 'final_score'):
                        priority = event.final_score
                    else:
                        priority = self.scorer.calculate_priority(event, confidence)
                    
                    self.publication_queue.append({
                        "event": event,
                        "verdict": verdict,
                        "confidence": confidence,
                        "priority": priority,
                        "queued_at": datetime.utcnow()
                    })
                except Exception as e:
                    print(f"⚠️  [SCORE] Ошибка оценки: {e}")
                    continue
            
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикация из очереди с добавлением в tracking"""
        
        now = datetime.utcnow()
        
        # Очищаем старые публикации (>1 часа)
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        # Проверяем лимит
        if len(self.recent_publications) >= settings.POSTS_PER_HOUR_CAP:
            print(f"⏸️  [RATE] Лимит {settings.POSTS_PER_HOUR_CAP}/час достигнут")
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
                        self.stats["events_published"] += 1
                        
                        # Добавляем в очередь верификации
                        if self.pending_verification is not None:
                            self.pending_verification.append({
                                "event": event,
                                "verdict": verdict,
                                "confidence": confidence,
                                "published_at": datetime.utcnow()
                            })
                        
                        print(f"✅ [PUBLISHED] {event.asset} ${event.amount_usd:,.0f}")
                    
                    await asyncio.sleep(120)
            
            except Exception as e:
                print(f"❌ [PUBLISH] Ошибка: {e}")
                self.stats["errors"] += 1
    
    async def _mining_loop(self):
        """НОВОЕ: Цикл mining system (интеграция discovery + validation)"""
        
        if not self.mining_system:
            return
        
        # Первый запуск через 1 час
        await asyncio.sleep(3600)
        
        while not self._shutdown_flag:
            try:
                print(f"\n{'='*80}")
                print(f"⛏️  [MINING] Запуск mining cycle")
                print(f"{'='*80}")
                
                # Discovery раз в 6 часов
                if not self.stats.get("last_mining_discovery") or \
                   (datetime.utcnow() - self.stats["last_mining_discovery"]).total_seconds() > 21600:
                    
                    result = await self.mining_system.run_discovery_cycle(
                        chains=self.supported_chains if self.chains_enabled else None,
                        max_wallets=settings.SMART_DISCOVERY_MAX_NEW_WALLETS
                    )
                    
                    self.stats["wallets_discovered"] += result["added"]
                    self.stats["last_mining_discovery"] = datetime.utcnow()
                
                # Validation раз в день
                if not self.stats.get("last_mining_validation") or \
                   (datetime.utcnow() - self.stats["last_mining_validation"]).total_seconds() > 86400:
                    
                    result = await self.mining_system.run_validation_cycle()
                    
                    self.stats["wallets_removed"] += result["removed"]
                    self.stats["last_mining_validation"] = datetime.utcnow()
                
                # Stats
                self.mining_system.print_stats()
            
            except Exception as e:
                print(f"❌ [MINING] Ошибка: {e}")
                import traceback
                traceback.print_exc()
            
            # Следующая проверка через 1 час
            await asyncio.sleep(3600)
    
    async def _smart_discovery_loop(self):
        """Автоматический поиск успешных трейдеров"""
        
        if not self.smart_discovery or not self.wallet_db:
            print("⏭️  [SMART_DISCOVERY] Отключен")
            return
        
        await asyncio.sleep(1800)
        
        while not self._shutdown_flag:
            try:
                print(f"\n{'='*80}")
                print(f"🔍 [SMART_DISCOVERY] Запуск поиска успешных трейдеров")
                print(f"{'='*80}")
                
                start_time = datetime.utcnow()
                
                async with self.smart_discovery:
                    wallets = await self.smart_discovery.discover_new_wallets()
                
                added_count = 0
                for wallet_stats in wallets:
                    if self.wallet_db.add_wallet(wallet_stats):
                        added_count += 1
                
                self.stats["wallets_discovered"] += added_count
                self.stats["last_smart_discovery_run"] = datetime.utcnow()
                
                elapsed = (datetime.utcnow() - start_time).seconds
                
                print(f"\n{'='*80}")
                print(f"✅ [SMART_DISCOVERY] Завершён за {elapsed}с")
                print(f"   Найдено: {len(wallets)} кошельков")
                print(f"   Добавлено: {added_count} новых")
                print(f"   Всего в базе: {len(self.wallet_db.get_active_wallets())} активных")
                print(f"{'='*80}\n")
                
                if added_count > 5 and self.alert_manager:
                    try:
                        await self.alert_manager.send_notification(
                            f"🎉 Smart Discovery нашёл {added_count} новых успешных трейдеров!",
                            alert_type="smart_discovery"
                        )
                    except:
                        pass
                
            except Exception as e:
                print(f"❌ [SMART_DISCOVERY] Ошибка: {e}")
                import traceback
                traceback.print_exc()
            
            wait_hours = settings.SMART_DISCOVERY_INTERVAL_HOURS
            print(f"⏰ [SMART_DISCOVERY] Следующий запуск через {wait_hours}ч")
            await asyncio.sleep(wait_hours * 3600)
    
    async def _discovery_loop(self):
        """Обновление watchlist"""
        
        if settings.ASSETS != '*':
            print("⏭️  [DISCOVERY] Отключен (ALLOWLIST режим)")
            return
        
        try:
            print(f"\n🔄 [DISCOVERY] Первичное обновление watchlist")
            await self.discovery.refresh_watchlist()
        except Exception as e:
            print(f"❌ [DISCOVERY] Ошибка: {e}")
        
        while not self._shutdown_flag:
            try:
                wait_seconds = settings.DISCOVERY_REFRESH_HOURS * 3600
                print(f"⏰ [DISCOVERY] Следующее обновление через {settings.DISCOVERY_REFRESH_HOURS}ч")
                await asyncio.sleep(wait_seconds)
                
                print(f"\n🔄 [DISCOVERY] Плановое обновление watchlist")
                await self.discovery.refresh_watchlist()
                
            except Exception as e:
                print(f"❌ [DISCOVERY] Ошибка: {e}")
                await asyncio.sleep(1800)
    
    async def _performance_tracker_loop(self):
        """Отслеживание результатов опубликованных сигналов"""
        
        if not self.pending_verification:
            print("⏭️  [PERFORMANCE] Отключен")
            return
        
        await asyncio.sleep(3600)
        
        while not self._shutdown_flag:
            try:
                if not self.pending_verification:
                    await asyncio.sleep(600)
                    continue
                
                print(f"\n📊 [PERFORMANCE] Проверка {len(self.pending_verification)} сигналов...")
                
                now = datetime.utcnow()
                checked_count = 0
                to_remove = []
                
                for item in list(self.pending_verification):
                    event = item["event"]
                    verdict = item["verdict"]
                    confidence = item["confidence"]
                    published_at = item["published_at"]
                    
                    hours_passed = (now - published_at).total_seconds() / 3600
                    
                    if hours_passed >= 24 and not item.get("checked_24h"):
                        try:
                            async with aiohttp.ClientSession() as session:
                                price_change = await self._get_price_change(event.asset, session)
                            
                            if price_change is not None:
                                success = self._evaluate_signal_success(verdict, price_change)
                                
                                if self.adaptive_thresholds:
                                    signal_data = {
                                        "success": success,
                                        "confidence": confidence,
                                        "verdict": verdict,
                                        "price_change_24h": price_change
                                    }
                                    self.adaptive_thresholds.add_performance_result(signal_data)
                                
                                if success:
                                    self.stats["events_successful"] += 1
                                else:
                                    self.stats["events_failed"] += 1
                                
                                # Обновляем скор кошелька
                                if self.wallet_db and hasattr(event, 'from_address'):
                                    adjustment = settings.WALLET_SCORE_UPDATE_ON_SUCCESS if success else settings.WALLET_SCORE_UPDATE_ON_FAILURE
                                    wallet = self.wallet_db.get_wallet(event.from_address, event.chain)
                                    if wallet:
                                        new_score = wallet.get('score', 50) + adjustment
                                        self.wallet_db.update_wallet_score(event.from_address, event.chain, new_score)
                                
                                item["checked_24h"] = True
                                checked_count += 1
                                
                                print(f"   {'✅' if success else '❌'} {event.asset}: {verdict} → {price_change:+.1%} "
                                      f"({'успех' if success else 'провал'})")
                        
                        except Exception as e:
                            print(f"   ⚠️  Ошибка проверки {event.asset}: {e}")
                    
                    if hours_passed > 48:
                        to_remove.append(item)
                
                for item in to_remove:
                    self.pending_verification.remove(item)
                
                if checked_count > 0 and self.adaptive_thresholds:
                    stats = self.adaptive_thresholds.get_stats()
                    print(f"\n   📈 Текущая точность: {stats.get('accuracy', 0):.1%} ({stats['signals_tracked']} сигналов)")
                    print(f"   🎯 Режим рынка: {stats['regime']}")
                    print(f"   ⚙️  Текущие пороги: confidence≥{stats['current_thresholds']['min_confidence']}\n")
            
            except Exception as e:
                print(f"❌ [PERFORMANCE] Ошибка: {e}")
            
            await asyncio.sleep(3600)
    
    def _evaluate_signal_success(self, verdict: str, price_change: float) -> bool:
        """Оценка успешности сигнала"""
        
        if verdict == "bearish":
            return price_change < settings.PERFORMANCE_SUCCESS_THRESHOLD_BEARISH
        elif verdict == "bullish":
            return price_change > settings.PERFORMANCE_SUCCESS_THRESHOLD_BULLISH
        else:
            return True
    
    async def _get_price_change(self, asset: str, session: aiohttp.ClientSession) -> Optional[float]:
        """Получает изменение цены за 24ч"""
        
        try:
            symbol_to_id = {
                "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
                "SOL": "solana", "MATIC": "matic-network", "AVAX": "avalanche-2",
                "ARB": "arbitrum", "OP": "optimism"
            }
            
            coin_id = symbol_to_id.get(asset)
            if not coin_id:
                return None
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if coin_id in data and "usd_24h_change" in data[coin_id]:
                        return data[coin_id]["usd_24h_change"] / 100
        
        except Exception:
            pass
        
        return None
    
    async def _validation_loop(self):
        """Автоматическая очистка базы кошельков"""
        
        if not self.wallet_db:
            print("⏭️  [VALIDATION] Отключен (нет wallet_db)")
            return
        
        await asyncio.sleep(86400)
        
        while not self._shutdown_flag:
            try:
                print(f"\n{'='*80}")
                print(f"🧹 [VALIDATION] Запуск очистки базы данных")
                print(f"{'='*80}")
                
                active_wallets = self.wallet_db.get_active_wallets()
                
                print(f"   Проверяю {len(active_wallets)} активных кошельков...")
                
                removed_count = 0
                
                for wallet in active_wallets:
                    address = wallet["address"]
                    chain = wallet["chain"]
                    
                    last_trade = datetime.fromisoformat(wallet.get("last_trade_at", datetime.utcnow().isoformat()))
                    days_inactive = (datetime.utcnow() - last_trade).days
                    
                    if days_inactive > settings.VALIDATION_MAX_INACTIVE_DAYS:
                        self.wallet_db.deactivate_wallet(address, chain, f"inactive_{days_inactive}d")
                        removed_count += 1
                        continue
                    
                    score = wallet.get("score", settings.WALLET_INITIAL_SCORE)
                    if score < settings.VALIDATION_MIN_SCORE_TO_KEEP:
                        self.wallet_db.deactivate_wallet(address, chain, f"low_score_{score}")
                        removed_count += 1
                        continue
                    
                    if settings.VALIDATION_CHECK_PERFORMANCE:
                        roi_30d = wallet.get("roi_30d", 0)
                        if roi_30d < settings.VALIDATION_MIN_ROI_TO_KEEP:
                            self.wallet_db.deactivate_wallet(address, chain, f"negative_roi_{roi_30d:.1%}")
                            removed_count += 1
                            continue
                
                self.stats["wallets_removed"] += removed_count
                self.stats["last_validation_run"] = datetime.utcnow()
                
                remaining = len(self.wallet_db.get_active_wallets())
                
                print(f"\n{'='*80}")
                print(f"✅ [VALIDATION] Очистка завершена")
                print(f"   Проверено: {len(active_wallets)} кошельков")
                print(f"   Удалено: {removed_count}")
                print(f"   Осталось активных: {remaining}")
                print(f"{'='*80}\n")
                
                if removed_count > settings.VALIDATION_NOTIFY_THRESHOLD and self.alert_manager:
                    try:
                        await self.alert_manager.send_notification(
                            f"🧹 Validation удалил {removed_count} неактуальных кошельков",
                            alert_type="validation"
                        )
                    except:
                        pass
            
            except Exception as e:
                print(f"❌ [VALIDATION] Ошибка: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"⏰ [VALIDATION] Следующая проверка через {settings.VALIDATION_INTERVAL_DAYS} дней")
            await asyncio.sleep(settings.VALIDATION_INTERVAL_DAYS * 86400)
    
    async def _market_regime_updater_loop(self):
        """Обновление режима рынка"""
        
        if not self.adaptive_thresholds:
            print("⏭️  [REGIME] Отключен")
            return
        
        while not self._shutdown_flag:
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.coingecko.com/api/v3/simple/price"
                    params = {
                        "ids": "bitcoin",
                        "vs_currencies": "usd",
                        "include_7d_change": "true"
                    }
                    
                    async with session.get(url, params=params, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            btc_change = data["bitcoin"].get("usd_7d_change", 0)
                            self.adaptive_thresholds.update_regime(btc_change)
            
            except Exception as e:
                print(f"⚠️  [REGIME] Ошибка: {e}")
            
            await asyncio.sleep(settings.ADAPTIVE_MARKET_REGIME_UPDATE_HOURS * 3600)
    
    async def _stats_reporter_loop(self):
        """Отправка ежедневной статистики"""
        
        await asyncio.sleep(86400)
        
        while not self._shutdown_flag:
            try:
                if self.alert_manager and settings.SEND_DAILY_STATS:
                    
                    extended_stats = {
                        **self.stats
                    }
                    
                    if self.adaptive_thresholds:
                        extended_stats["adaptive"] = self.adaptive_thresholds.get_stats()
                    
                    if self.wallet_db:
                        extended_stats["wallet_db"] = {
                            "total": len(self.wallet_db.wallets),
                            "active": len(self.wallet_db.get_active_wallets())
                        }
                    
                    if self.analytics_enabled:
                        extended_stats["analytics_calls"] = self.stats.get("analytics_calls", 0)
                    
                    if self.chains_enabled:
                        extended_stats["chains_events"] = dict(self.stats.get("chains_events", {}))
                    
                    await self.alert_manager.send_daily_stats({"whale": extended_stats})
                
                # Сброс счётчиков
                self.stats["events_collected"] = 0
                self.stats["events_qualified"] = 0
                self.stats["events_published"] = 0
                self.stats["events_successful"] = 0
                self.stats["events_failed"] = 0
                self.stats["wallets_discovered"] = 0
                self.stats["wallets_removed"] = 0
                self.stats["errors"] = 0
                self.stats["analytics_calls"] = 0
                self.stats["chains_events"] = defaultdict(int)
            
            except Exception as e:
                print(f"⚠️  [STATS] Ошибка: {e}")
            
            await asyncio.sleep(86400)
    
    async def _health_check_loop(self):
        """Проверка здоровья системы"""
        
        while not self._shutdown_flag:
            try:
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
                
                if not settings.HEALTH_CHECK_ENABLED:
                    continue
                
                now = datetime.utcnow()
                
                if self.stats["last_cycle_time"]:
                    silence = (now - self.stats["last_cycle_time"]).seconds
                    
                    if silence > settings.HEALTH_CHECK_MAX_SILENCE:
                        if self.alert_manager:
                            await self.alert_manager.send_warning(
                                f"⚠️  Последний цикл был {silence//60} минут назад",
                                alert_type="health_check"
                            )
            
            except Exception as e:
                print(f"⚠️  [HEALTH] Ошибка: {e}")
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """Проверка разрешённости актива"""
        if settings.ASSETS == '*':
            return self.discovery.is_in_watchlist(event.chain, event.asset)
        else:
            return event.asset in settings.ASSETS_LIST
    
    def _load_state(self):
        """Загрузка состояния"""
        try:
            state_file = Path(settings.STATE_FILE)
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.seen_keys = set(state.get("seen_keys", []))
                print(f"📂 [STATE] Загружено {len(self.seen_keys)} ключей")
            else:
                self.seen_keys = set()
        except Exception as e:
            print(f"⚠️  [STATE] Ошибка загрузки: {e}")
            self.seen_keys = set()
    
    def _save_state(self):
        """Сохранение состояния"""
        try:
            state = {
                "last_seen_timestamp": datetime.utcnow().isoformat(),
                "seen_keys": list(self.seen_keys)[-10000:]
            }
            
            state_file = Path(settings.STATE_FILE)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"💾 [STATE] Сохранено")
        except Exception as e:
            print(f"⚠️  [STATE] Ошибка: {e}")
    
    def _print_banner(self):
        """Вывод баннера при запуске"""
        print("\n" + "="*80)
        print("🐋 INTELLIGENT WHALE MONITOR v3.0 [FULL INTEGRATION]")
        print("="*80)
        print(f"Режим: {'DISCOVERY' if settings.ASSETS == '*' else 'ALLOWLIST'}")
        print(f"Канал: {settings.CHAT_ID}")
        print(f"Лимит: {settings.POSTS_PER_HOUR_CAP}/час")
        
        print(f"\n🧠 ИНТЕЛЛЕКТУАЛЬНЫЕ СИСТЕМЫ:")
        print(f"  Smart Discovery: {'✅ каждые ' + str(settings.SMART_DISCOVERY_INTERVAL_HOURS) + 'ч' if settings.SMART_DISCOVERY_ENABLED and self.smart_discovery else '❌'}")
        print(f"  Adaptive Thresholds: {'✅' if settings.ADAPTIVE_THRESHOLDS_ENABLED else '❌'}")
        print(f"  Performance Tracking: {'✅' if settings.PERFORMANCE_TRACKING_ENABLED else '❌'}")
        print(f"  Validation: {'✅ каждые ' + str(settings.VALIDATION_INTERVAL_DAYS) + 'д' if settings.VALIDATION_ENABLED else '❌'}")
        print(f"  Mining System: {'✅' if self.mining_system else '❌'}")
        
        print(f"\n🌐 MULTI-CHAIN:")
        if self.chains_enabled:
            print(f"  Status: ✅ Enabled")
            print(f"  Chains: {', '.join(self.supported_chains)}")
        else:
            print(f"  Status: ❌ Disabled")
        
        print(f"\n📊 ANALYTICS:")
        if self.analytics_enabled:
            print(f"  Status: ✅ Enabled")
            print(f"  Modules: Sentiment, Risk Scoring, Correlation, Anomaly")
        else:
            print(f"  Status: ❌ Disabled")
        
        if self.wallet_db:
            print(f"\n💾 Tracked Wallets: {len(self.wallet_db.get_active_wallets())}")
        
        if self.adaptive_thresholds:
            thresholds = self.adaptive_thresholds.get_current_thresholds()
            print(f"\n⚙️  Стартовые пороги:")
            print(f"  Confidence: ≥{thresholds['min_confidence']}")
            print(f"  Size Rel: ≥{thresholds['min_size_rel']:.2%}")
            print(f"  Volume: ≥${thresholds['min_volume_24h']:,}")
        
        print("="*80 + "\n")
    
    async def shutdown(self):
        """Graceful shutdown"""
        print("\n⏹️  [SCHEDULER] Shutdown initiated...")
        self._shutdown_flag = True
        self._save_state()
        
        # Финальная статистика
        print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        print(f"  События собрано: {self.stats['events_collected']}")
        print(f"  Прошло фильтры: {self.stats['events_qualified']}")
        print(f"  Опубликовано: {self.stats['events_published']}")
        
        if self.stats['events_successful'] + self.stats['events_failed'] > 0:
            total = self.stats['events_successful'] + self.stats['events_failed']
            accuracy = (self.stats['events_successful'] / total) * 100
            print(f"  Успешных: {self.stats['events_successful']}/{total} ({accuracy:.1f}%)")
        
        if self.analytics_enabled:
            print(f"\n📊 ANALYTICS:")
            print(f"  Total calls: {self.stats.get('analytics_calls', 0)}")
        
        if self.chains_enabled:
            print(f"\n🌐 CHAINS:")
            for chain, count in sorted(self.stats.get('chains_events', {}).items(), key=lambda x: x[1], reverse=True):
                print(f"  {chain}: {count} events")
        
        if self.adaptive_thresholds:
            stats = self.adaptive_thresholds.get_stats()
            print(f"\n🧠 АДАПТИВНАЯ СИСТЕМА:")
            print(f"  Режим рынка: {stats['regime']}")
            print(f"  Точность: {stats.get('accuracy', 0):.1%} ({stats['signals_tracked']} сигналов)")
        
        if self.wallet_db:
            print(f"\n💾 WALLET DATABASE:")
            print(f"  Всего: {len(self.wallet_db.wallets)}")
            print(f"  Активных: {len(self.wallet_db.get_active_wallets())}")
            print(f"  Найдено: {self.stats['wallets_discovered']}")
            print(f"  Удалено: {self.stats['wallets_removed']}")
        
        uptime_hours = (datetime.utcnow() - self.stats['start_time']).total_seconds() / 3600
        print(f"\n⏱️  Uptime: {uptime_hours:.1f}h")
        
        print("\n✅ [SCHEDULER] Shutdown complete")