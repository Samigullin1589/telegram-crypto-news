"""
INTEGRATED SCHEDULER v4.2 - Complete Trading & Whale Monitoring System

РЕВОЛЮЦИОННЫЕ ВОЗМОЖНОСТИ:
✅ Multi-Chain Support (7+ blockchains)
✅ Advanced Analytics (Sentiment, Risk, Correlation, Anomaly)
✅ Smart Money Discovery - автопоиск успешных трейдеров
✅ Validation Engine - автоочистка базы от мусора
✅ Performance Tracking - отслеживание результатов
✅ Adaptive Thresholds - динамические пороги
✅ Learning System - самообучение на ошибках
✅ Cross-Chain Wallet Tracking - мониторинг на всех chains

НОВОЕ В v4.2:
🔥 Solana Fallback RPC Rotation - автоматическое переключение между RPC endpoints
🔥 Intelligent Backoff Strategy - умные паузы при перегрузке API
🔥 Enhanced Error Recovery - улучшенное восстановление после ошибок
🔥 Trading System Integration - полная интеграция торговой системы
"""

import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from collections import deque, defaultdict
from pathlib import Path
import statistics
import traceback
import time

from app import settings

# ============================================================================
# WHALE MONITORING IMPORTS
# ============================================================================
from app.whales.discovery import DiscoveryEngine
from app.whales.monitor import BlockchainMonitor
from app.whales.normalize import WhaleEvent
from app.whales.score import EventScorer
from app.whales.price import PriceProvider
from app.whales.news import NewsGate
from app.whales.publish import WhalePublisher
from app.whales.history import HistoryManager
from app.charts.sparkline import SparklineRenderer

# ============================================================================
# TRADING SYSTEM IMPORTS (НОВОЕ)
# ============================================================================
try:
    from app.trading.signal_generator import SignalGenerator
    from app.trading.position_tracker import PositionTracker
    from app.trading.performance_stats import PerformanceStats
    TRADING_AVAILABLE = True
except ImportError:
    TRADING_AVAILABLE = False
    print("⚠️ Trading System не найден - работаем без него")

# ============================================================================
# OPTIONAL FEATURES
# ============================================================================

# Multi-Chain Support
try:
    from app.chains import initialize_all_chains, unified_api, get_supported_chains
    CHAINS_AVAILABLE = True
except ImportError:
    CHAINS_AVAILABLE = False
    print("⚠️ Multi-Chain Support не найден")

# Advanced Analytics
try:
    from app.analytics import get_analytics_engine, AnalyticsEngine
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    print("⚠️ Analytics Engine не найден")

# Mining System
try:
    from app.mining.integration import create_mining_system
    MINING_AVAILABLE = True
except ImportError:
    MINING_AVAILABLE = False
    print("⚠️ Mining System не найден")

# Алерты
try:
    from app.alerts import get_alert_manager_sync
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False
    print("⚠️ Alerts не найдены - работаем без них")

# Smart Money Discovery
try:
    from app.whales.smart_discovery import SmartMoneyDiscovery
    SMART_DISCOVERY_AVAILABLE = True
except ImportError:
    SMART_DISCOVERY_AVAILABLE = False
    print("⚠️ Smart Discovery не найден - работаем без него")


class AdaptiveThresholds:
    """
    Динамические пороги, адаптирующиеся под рынок и производительность
    """
    
    def __init__(self):
        self.market_regime = "sideways"
        self.performance_history = deque(maxlen=100)
        
        self.base_thresholds = {
            "min_confidence": settings.ADAPTIVE_BASE_MIN_CONFIDENCE,
            "min_size_rel": settings.ADAPTIVE_BASE_MIN_SIZE_REL,
            "min_volume_24h": settings.ADAPTIVE_BASE_MIN_VOLUME_24H
        }
        
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
        
        print(f"⚙️ [ADAPTIVE] Инициализирован. Базовые пороги: "
              f"confidence≥{self.base_thresholds['min_confidence']}, "
              f"size_rel≥{self.base_thresholds['min_size_rel']:.2%}")
    
    def detect_market_regime(self, btc_change_7d: float) -> str:
        if btc_change_7d > settings.ADAPTIVE_BULL_THRESHOLD:
            return "bull"
        elif btc_change_7d < settings.ADAPTIVE_BEAR_THRESHOLD:
            return "bear"
        else:
            return "sideways"
    
    def update_regime(self, btc_change_7d: float):
        old_regime = self.market_regime
        self.market_regime = self.detect_market_regime(btc_change_7d)
        
        if old_regime != self.market_regime:
            print(f"📊 [REGIME] Режим рынка изменён: {old_regime} → {self.market_regime}")
    
    def get_current_thresholds(self) -> Dict:
        modifiers = self.regime_modifiers[self.market_regime]
        
        thresholds = {
            "min_confidence": int(self.base_thresholds["min_confidence"] + modifiers["min_confidence"]),
            "min_size_rel": self.base_thresholds["min_size_rel"] + modifiers["min_size_rel"],
            "min_volume_24h": int(self.base_thresholds["min_volume_24h"] * modifiers["min_volume_24h"])
        }
        
        if len(self.performance_history) >= settings.ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION:
            recent_accuracy = self._calculate_recent_accuracy()
            
            if recent_accuracy < settings.ADAPTIVE_LOW_ACCURACY_THRESHOLD:
                adjustment = settings.ADAPTIVE_ACCURACY_ADJUSTMENT
                thresholds["min_confidence"] += adjustment
                print(f"⚠️ [ADAPTIVE] Низкая точность ({recent_accuracy:.1%}), "
                      f"повышаю min_confidence до {thresholds['min_confidence']}")
            
            elif recent_accuracy > settings.ADAPTIVE_HIGH_ACCURACY_THRESHOLD:
                adjustment = settings.ADAPTIVE_ACCURACY_ADJUSTMENT
                thresholds["min_confidence"] = max(30, thresholds["min_confidence"] - adjustment)
                print(f"✅ [ADAPTIVE] Высокая точность ({recent_accuracy:.1%}), "
                      f"понижаю min_confidence до {thresholds['min_confidence']}")
        
        return thresholds
    
    def add_performance_result(self, signal_data: Dict):
        self.performance_history.append(signal_data)
    
    def _calculate_recent_accuracy(self) -> float:
        min_signals = settings.ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION
        
        if len(self.performance_history) < min_signals:
            return 0.5
        
        recent = list(self.performance_history)[-min_signals:]
        successful = sum(1 for s in recent if s.get("success", False))
        
        return successful / len(recent)
    
    def get_stats(self) -> Dict:
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
            print(f"⚠️ [WALLET_DB] Ошибка загрузки: {e}")
            self.wallets = []
    
    def _save(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.db_path, 'w') as f:
                json.dump(self.wallets, f, indent=2)
        except Exception as e:
            print(f"⚠️ [WALLET_DB] Ошибка сохранения: {e}")
    
    def add_wallet(self, wallet_stats) -> bool:
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
        for wallet in self.wallets:
            if wallet["address"].lower() == address.lower() and wallet["chain"] == chain:
                return wallet
        return None
    
    def get_active_wallets(self) -> List[Dict]:
        return [w for w in self.wallets if w.get("is_active", True)]
    
    def deactivate_wallet(self, address: str, chain: str, reason: str):
        wallet = self.get_wallet(address, chain)
        if wallet:
            wallet["is_active"] = False
            wallet["deactivated_at"] = datetime.utcnow().isoformat()
            wallet["deactivation_reason"] = reason
            self._save()
            print(f"❌ [WALLET_DB] Деактивирован: {address[:10]}... ({reason})")
    
    def update_wallet_score(self, address: str, chain: str, new_score: int):
        wallet = self.get_wallet(address, chain)
        if wallet:
            old_score = wallet.get("score", settings.WALLET_INITIAL_SCORE)
            wallet["score"] = max(settings.WALLET_MIN_SCORE, min(settings.WALLET_MAX_SCORE, new_score))
            wallet["score_updated_at"] = datetime.utcnow().isoformat()
            self._save()
            
            if abs(new_score - old_score) > 10:
                print(f"📊 [WALLET_DB] Скор обновлён: {address[:10]}... {old_score} → {new_score}")
    
    def _prune_worst_wallets(self, count: int):
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


class IntegratedScheduler:
    """
    Главный координатор с полной интеграцией whale monitoring и trading system
    """
    
    def __init__(self):
        print("\n" + "="*80)
        print("🚀 INTEGRATED SCHEDULER v4.2 - INITIALIZATION")
        print("="*80 + "\n")
        
        # ====================================================================
        # WHALE MONITORING COMPONENTS
        # ====================================================================
        print("📦 [1/3] Инициализация Whale Monitoring...")
        
        self.discovery = DiscoveryEngine()
        self.scorer = EventScorer()
        self.price_provider = PriceProvider()
        self.news_gate = NewsGate()
        self.publisher = WhalePublisher()
        self.chart_renderer = SparklineRenderer()
        self.history_manager = HistoryManager()
        
        print("   ✓ Discovery Engine")
        print("   ✓ Event Scorer")
        print("   ✓ Price Provider")
        print("   ✓ News Gate")
        print("   ✓ Publisher")
        print("   ✓ Chart Renderer")
        print("   ✓ History Manager")
        
        # Адаптивные системы
        if settings.ADAPTIVE_THRESHOLDS_ENABLED:
            self.adaptive_thresholds = AdaptiveThresholds()
            print("   ✓ Adaptive Thresholds")
        else:
            self.adaptive_thresholds = None
        
        if settings.SMART_DISCOVERY_ENABLED or settings.VALIDATION_ENABLED:
            self.wallet_db = WalletDatabase()
            print("   ✓ Wallet Database")
        else:
            self.wallet_db = None
        
        # НОВОЕ v4.2: Solana fallback RPC management
        self.solana_consecutive_failures = 0
        self.solana_backoff_until = 0
        self.solana_max_consecutive_failures = 3
        self.solana_backoff_seconds = 120
        
        self.solana_rpc_endpoints = [
            f"https://mainnet.helius-rpc.com/?api-key={settings.HELIUS_API_KEY}",
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana",
            "https://solana-api.projectserum.com"
        ]
        self.current_solana_rpc_index = 0
        
        print("   ✓ Solana Fallback RPC (4 endpoints)")
        
        # ====================================================================
        # TRADING SYSTEM COMPONENTS (НОВОЕ)
        # ====================================================================
        print("\n📦 [2/3] Инициализация Trading System...")
        
        self.trading_enabled = False
        if TRADING_AVAILABLE:
            try:
                coingecko_key = getattr(settings, 'COINGECKO_API_KEY', None)
                
                self.signal_generator = SignalGenerator(coingecko_key)
                self.trading_enabled = True
                
                print("   ✓ Signal Generator")
                print("   ✓ Technical Analysis")
                print("   ✓ Fundamental Analysis")
                print("   ✓ Hot Wallet Tracker")
                print("   ✓ ML Predictor")
                print("   ✓ Position Tracker")
                print("   ✓ Performance Stats")
            except Exception as e:
                print(f"   ✗ Trading System Error: {e}")
                self.trading_enabled = False
        else:
            print("   ✗ Trading System не доступен")
        
        # ====================================================================
        # OPTIONAL FEATURES
        # ====================================================================
        print("\n📦 [3/3] Инициализация Optional Features...")
        
        # Multi-Chain Support
        self.chains_enabled = False
        if CHAINS_AVAILABLE and hasattr(settings, 'ETHERSCAN_API_KEY'):
            try:
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
                
                print(f"   ✓ Multi-Chain: {', '.join(self.supported_chains)}")
            except Exception as e:
                print(f"   ✗ Multi-Chain Error: {e}")
                self.chains_enabled = False
        
        # Advanced Analytics
        self.analytics_enabled = False
        if ANALYTICS_AVAILABLE:
            try:
                self.analytics_engine = get_analytics_engine()
                self.analytics_enabled = True
                print("   ✓ Analytics Engine")
            except Exception as e:
                print(f"   ✗ Analytics Error: {e}")
        
        # Mining System
        self.mining_system = None
        if MINING_AVAILABLE and self.wallet_db:
            try:
                self.mining_system = create_mining_system(self.wallet_db)
                print("   ✓ Mining System")
            except Exception as e:
                print(f"   ✗ Mining Error: {e}")
        
        # Smart Money Discovery
        self.smart_discovery = None
        if SMART_DISCOVERY_AVAILABLE and settings.SMART_DISCOVERY_ENABLED:
            if hasattr(settings, 'ETHERSCAN_API_KEY') and settings.ETHERSCAN_API_KEY:
                self.smart_discovery = SmartMoneyDiscovery(
                    etherscan_key=settings.ETHERSCAN_API_KEY,
                    coingecko_key=getattr(settings, 'COINGECKO_API_KEY', None)
                )
                print("   ✓ Smart Discovery")
            else:
                print("   ✗ Smart Discovery (no API key)")
        
        # Алерты
        if ALERTS_AVAILABLE:
            self.alert_manager = get_alert_manager_sync(settings.ADMIN_CHAT_ID)
            print("   ✓ Alert Manager")
        else:
            self.alert_manager = None
        
        # ====================================================================
        # STATE & QUEUES
        # ====================================================================
        
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
            "trading_signals_generated": 0,
            "trading_signals_sent": 0,
            "positions_opened": 0,
            "positions_closed": 0,
            "trading_pnl_total": 0.0,
            "last_cycle_time": None,
            "last_discovery_run": None,
            "last_validation_run": None,
            "last_smart_discovery_run": None,
            "last_trading_signal": None,
            "start_time": datetime.utcnow(),
            "analytics_calls": 0,
            "chains_events": defaultdict(int),
            "solana_rpc_switches": 0,
            "solana_backoffs": 0
        }
        
        if settings.PERFORMANCE_TRACKING_ENABLED:
            self.pending_verification = deque(maxlen=settings.PERFORMANCE_HISTORY_SIZE)
        else:
            self.pending_verification = None
        
        self._shutdown_flag = False
        
        self._load_state()
        
        print("\n" + "="*80)
        print("✅ INITIALIZATION COMPLETE")
        print("="*80 + "\n")
    
    async def run(self):
        """Главный цикл с полной интеграцией всех систем"""
        
        self._print_banner()
        
        if self.alert_manager and settings.SEND_STARTUP_NOTIFICATION:
            try:
                await self.alert_manager.send_startup_notification()
            except Exception as e:
                print(f"⚠️ Не удалось отправить startup notification: {e}")
        
        tasks = []
        
        tasks.extend([
            asyncio.create_task(self._whale_monitor_loop(), name="whale_monitor"),
            asyncio.create_task(self._stats_reporter_loop(), name="stats"),
            asyncio.create_task(self._health_check_loop(), name="health"),
        ])
        
        if settings.ASSETS == '*':
            tasks.append(asyncio.create_task(self._discovery_loop(), name="discovery"))
        
        if settings.ADAPTIVE_THRESHOLDS_ENABLED:
            tasks.append(asyncio.create_task(self._market_regime_updater_loop(), name="regime_updater"))
        
        if settings.PERFORMANCE_TRACKING_ENABLED:
            tasks.append(asyncio.create_task(self._performance_tracker_loop(), name="performance"))
        
        if settings.VALIDATION_ENABLED and self.wallet_db:
            tasks.append(asyncio.create_task(self._validation_loop(), name="validation"))
        
        if settings.SMART_DISCOVERY_ENABLED and self.smart_discovery:
            tasks.append(asyncio.create_task(self._smart_discovery_loop(), name="smart_discovery"))
        
        if self.mining_system and MINING_AVAILABLE:
            tasks.append(asyncio.create_task(self._mining_loop(), name="mining"))
        
        if self.trading_enabled:
            tasks.extend([
                asyncio.create_task(self._trading_signal_loop(), name="trading_signals"),
                asyncio.create_task(self._position_management_loop(), name="position_management"),
            ])
        
        try:
            print(f"\n🚀 [SCHEDULER] Запущено {len(tasks)} циклов:")
            for task in tasks:
                print(f"   • {task.get_name()}")
            print()
            
            await asyncio.gather(*tasks)
        
        except asyncio.CancelledError:
            print("\n⏹️ [SCHEDULER] Получен сигнал остановки")
        
        except Exception as e:
            print(f"\n❌ [SCHEDULER] Критическая ошибка: {e}")
            traceback.print_exc()
        
        finally:
            await self.shutdown()
    
    async def run_cycle(self):
        """
        Выполнить один цикл whale monitoring
        
        Этот метод вызывается из main.py в бесконечном цикле
        """
        try:
            self.stats["last_cycle_time"] = datetime.utcnow()
            
            start_time = datetime.utcnow() - timedelta(seconds=settings.POLL_SECONDS)
            
            events = []
            async with BlockchainMonitor() as monitor:
                # НОВОЕ v4.2: Устанавливаем текущий Solana RPC
                if "solana" in settings.ENABLED_CHAINS:
                    monitor.apis["solana"]["url"] = self.solana_rpc_endpoints[self.current_solana_rpc_index]
                
                events = await monitor.fetch_events(start_time)
                self.stats["events_collected"] += len(events)
                
                # НОВОЕ v4.2: Проверяем Solana статус
                solana_stats = monitor.get_stats()
                await self._handle_solana_status(solana_stats)
                
                if not events:
                    print("👍 [WHALE] Новых перемещений не найдено")
                else:
                    print(f"🔄 [WHALE] Найдено {len(events)} событий")
                    await self._process_whale_events(events)
            
            await self._publish_from_queue()
            
            return {
                'success': True,
                'events_collected': len(events),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.stats["errors"] += 1
            print(f"❌ [WHALE] Ошибка в run_cycle: {e}")
            raise
    
    # ========================================================================
    # НОВОЕ v4.2: SOLANA FALLBACK MANAGEMENT
    # ========================================================================
    
    async def _handle_solana_status(self, monitor_stats: Dict):
        """
        НОВОЕ v4.2: Обработка статуса Solana и управление fallback RPC
        """
        
        if "solana" not in settings.ENABLED_CHAINS:
            return
        
        solana_errors = monitor_stats.get("errors", {}).get("solana", 0)
        solana_retries = monitor_stats.get("retries_429", {}).get("solana", 0)
        
        current_time = time.time()
        
        if solana_errors > 0 or solana_retries >= 3:
            self.solana_consecutive_failures += 1
            print(f"⚠️  [SOLANA] Неудача #{self.solana_consecutive_failures} (errors={solana_errors}, retries={solana_retries})")
            
            if self.solana_consecutive_failures >= self.solana_max_consecutive_failures:
                self.solana_backoff_until = current_time + self.solana_backoff_seconds
                self.stats["solana_backoffs"] += 1
                print(f"🔄 [SOLANA] Backoff на {self.solana_backoff_seconds}s")
                
                # Переключаем на следующий RPC
                old_index = self.current_solana_rpc_index
                self.current_solana_rpc_index = (self.current_solana_rpc_index + 1) % len(self.solana_rpc_endpoints)
                self.stats["solana_rpc_switches"] += 1
                
                next_rpc = self.solana_rpc_endpoints[self.current_solana_rpc_index]
                print(f"🔄 [SOLANA] RPC switch: endpoint {old_index} → {self.current_solana_rpc_index}")
                print(f"   New RPC: {next_rpc[:50]}...")
                
                self.solana_consecutive_failures = 0
        else:
            # Успех - сбрасываем счетчик
            if self.solana_consecutive_failures > 0:
                print(f"✅ [SOLANA] Восстановление после {self.solana_consecutive_failures} неудач")
            self.solana_consecutive_failures = 0
    
    def _should_skip_solana(self) -> bool:
        """Проверяет нужно ли пропустить Solana из-за backoff"""
        current_time = time.time()
        
        if current_time < self.solana_backoff_until:
            remaining = int(self.solana_backoff_until - current_time)
            if remaining % 30 == 0:  # Логируем каждые 30 секунд
                print(f"⏸️  [SOLANA] В backoff режиме, осталось {remaining}s")
            return True
        
        return False
    
    # ========================================================================
    # WHALE MONITORING LOOPS
    # ========================================================================
    
    async def _whale_monitor_loop(self):
        """Основной цикл мониторинга крупных перемещений"""
        
        start_time = datetime.utcnow() - timedelta(minutes=settings.START_FROM_MINUTES_AGO)
        consecutive_errors = 0
        
        while not self._shutdown_flag:
            try:
                print(f"\n📊 [WHALE] Цикл: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
                self.stats["last_cycle_time"] = datetime.utcnow()
                
                # НОВОЕ v4.2: Определяем chains с учетом Solana backoff
                chains_to_scan = settings.ENABLED_CHAINS.copy()
                
                if "solana" in chains_to_scan and self._should_skip_solana():
                    chains_to_scan.remove("solana")
                
                async with BlockchainMonitor() as monitor:
                    # НОВОЕ v4.2: Устанавливаем текущий Solana RPC
                    if "solana" in chains_to_scan:
                        monitor.apis["solana"]["url"] = self.solana_rpc_endpoints[self.current_solana_rpc_index]
                    
                    events = await monitor.fetch_events(start_time, chains=chains_to_scan)
                    self.stats["events_collected"] += len(events)
                    
                    # НОВОЕ v4.2: Обработка Solana статуса
                    solana_stats = monitor.get_stats()
                    await self._handle_solana_status(solana_stats)
                    
                    if not events:
                        print("👍 [WHALE] Новых перемещений не найдено")
                    else:
                        await self._process_whale_events(events)
                
                start_time = datetime.utcnow()
                await self._publish_from_queue()
                
                consecutive_errors = 0
                
                print(f"⏰ [WHALE] Следующая проверка через {settings.POLL_SECONDS}с")
                await asyncio.sleep(settings.POLL_SECONDS)
                
            except Exception as e:
                consecutive_errors += 1
                self.stats["errors"] += 1
                
                print(f"❌ [WHALE] Ошибка ({consecutive_errors}/3): {e}")
                traceback.print_exc()
                
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
    
    async def _process_whale_events(self, events: List[WhaleEvent]):
        """Обработка whale событий с полной интеграцией analytics и multi-chain"""
        
        print(f"🔄 [PIPELINE] Обработка {len(events)} событий")
        
        if self.adaptive_thresholds:
            thresholds = self.adaptive_thresholds.get_current_thresholds()
            print(f"⚙️ [THRESHOLDS] Confidence≥{thresholds['min_confidence']}, "
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
                    dedup_key = event.get_dedup_key()
                    if dedup_key in self.seen_keys:
                        filter_stats["dedup"] += 1
                        continue
                    
                    if not self._is_asset_allowed(event):
                        filter_stats["asset_not_allowed"] += 1
                        continue
                    
                    if event.is_internal or event.is_bridge or event.is_reorg:
                        filter_stats["internal_bridge"] += 1
                        continue
                    
                    await self.price_provider.enrich_event_with_market_data(event, session)
                    
                    if event.amount_usd < event.min_usd_threshold:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if confidence < thresholds["min_confidence"]:
                        filter_stats["confidence_too_low"] += 1
                        continue
                    
                    size_rel = event.amount_usd / event.market.volume_24h_usd if event.market.volume_24h_usd else 0
                    
                    if size_rel < thresholds["min_size_rel"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    if event.market.volume_24h_usd < thresholds["min_volume_24h"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    if self.analytics_enabled:
                        try:
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
                            
                            analytics_result = self.analytics_engine.analyze_signal(
                                signal_data,
                                check_correlations=True,
                                check_anomalies=True
                            )
                            
                            self.stats["analytics_calls"] += 1
                            
                            risk_score = analytics_result["risk"]["risk_score"]
                            
                            if risk_score > 85:
                                filter_stats["risk_too_high"] += 1
                                print(f"⚠️ [RISK] Пропускаю {event.asset} - риск {risk_score}/100")
                                continue
                            
                            event.analytics = analytics_result
                            event.final_score = analytics_result["final_score"]
                            
                            print(f"📊 [ANALYTICS] {event.asset}: "
                                  f"Score={analytics_result['final_score']}/100, "
                                  f"Risk={risk_score}/100, "
                                  f"Sentiment={analytics_result['sentiment']['label']}")
                        
                        except Exception as e:
                            print(f"⚠️ [ANALYTICS] Ошибка анализа: {e}")
                    
                    if self.chains_enabled and hasattr(event, 'from_address'):
                        try:
                            cross_chain_analysis = await self.unified_api.analyze_wallet_cross_chain(
                                event.from_address
                            )
                            
                            if cross_chain_analysis["active_chains_count"] >= 3:
                                print(f"🏆 [CROSS-CHAIN] Sophisticated trader: "
                                      f"{event.from_address[:10]}... "
                                      f"({cross_chain_analysis['active_chains_count']} chains)")
                                
                                event.cross_chain_score = cross_chain_analysis["risk_score"]
                        
                        except Exception as e:
                            print(f"⚠️ [CROSS-CHAIN] Ошибка: {e}")
                    
                    filter_stats["passed"] += 1
                    qualified_events.append(event)
                    self.seen_keys.add(dedup_key)
                    
                    self.stats["chains_events"][event.chain] += 1
                
                except Exception as e:
                    print(f"⚠️ [FILTER] Ошибка обработки: {e}")
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
            
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            for event in qualified_events:
                try:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if not self.scorer.should_publish(event, verdict, confidence):
                        continue
                    
                    history_hint = await self.history_manager.find_similar_event(event, session)
                    if history_hint:
                        event.history_hint = history_hint
                    
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
                    print(f"⚠️ [SCORE] Ошибка оценки: {e}")
                    continue
            
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикация из очереди с tracking"""
        
        now = datetime.utcnow()
        
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
        if len(self.recent_publications) >= settings.POSTS_PER_HOUR_CAP:
            print(f"⏸️ [RATE] Лимит {settings.POSTS_PER_HOUR_CAP}/час достигнут")
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
    
    # ========================================================================
    # TRADING SYSTEM LOOPS
    # ========================================================================
    
    async def _trading_signal_loop(self):
        """Цикл генерации торговых сигналов"""
        
        if not self.trading_enabled:
            print("⏭️ [TRADING] Отключен")
            return
        
        print("📊 [TRADING] Запущен цикл генерации сигналов")
        
        monitored_assets = getattr(settings, 'TRADING_MONITORED_ASSETS', [
            'BTC', 'ETH', 'SOL', 'BNB', 'XRP',
            'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK',
            'UNI', 'AAVE', 'ARB', 'OP'
        ])
        
        check_interval = getattr(settings, 'TRADING_SIGNAL_INTERVAL_HOURS', 1) * 3600
        
        await asyncio.sleep(300)
        
        while not self._shutdown_flag:
            try:
                print(f"\n{'='*80}")
                print(f"📈 [TRADING] Генерация сигналов: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
                print(f"{'='*80}")
                
                async with aiohttp.ClientSession() as session:
                    signals_generated = 0
                    signals_sent = 0
                    
                    for asset in monitored_assets:
                        try:
                            print(f"\n🔍 [TRADING] Анализ {asset}...")
                            
                            price_data = await self._fetch_ohlcv(asset, session)
                            
                            if price_data is None or len(price_data) < 50:
                                print(f"   ⚠️ Недостаточно данных для {asset}")
                                continue
                            
                            signal = await self.signal_generator.generate_signal(
                                asset=asset,
                                price_data=price_data,
                                session=session
                            )
                            
                            if not signal:
                                print(f"   ⚠️ Не удалось сгенерировать сигнал для {asset}")
                                continue
                            
                            signals_generated += 1
                            self.stats["trading_signals_generated"] += 1
                            
                            if signal.signal in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']:
                                await self._send_trading_signal(signal)
                                signals_sent += 1
                                self.stats["trading_signals_sent"] += 1
                                self.stats["last_trading_signal"] = datetime.utcnow()
                            else:
                                print(f"   ⏸️ {asset}: {signal.signal} (не отправляем)")
                            
                            await asyncio.sleep(10)
                            
                        except Exception as e:
                            print(f"❌ [TRADING] Ошибка для {asset}: {e}")
                            traceback.print_exc()
                            continue
                
                print(f"\n{'='*80}")
                print(f"✅ [TRADING] Цикл завершён")
                print(f"   Сигналов сгенерировано: {signals_generated}")
                print(f"   Сигналов отправлено: {signals_sent}")
                print(f"{'='*80}\n")
                
                print(f"⏰ [TRADING] Следующая проверка через {check_interval//3600}ч")
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                print(f"❌ [TRADING] Критическая ошибка в signal loop: {e}")
                traceback.print_exc()
                await asyncio.sleep(600)
    
    async def _position_management_loop(self):
        """Цикл управления позициями"""
        
        if not self.trading_enabled:
            return
        
        print("💼 [POSITIONS] Запущен цикл управления позициями")
        
        update_interval = getattr(settings, 'POSITION_UPDATE_INTERVAL_SECONDS', 60)
        
        await asyncio.sleep(60)
        
        while not self._shutdown_flag:
            try:
                open_positions = self.signal_generator.positions.get_open_positions()
                
                if not open_positions:
                    await asyncio.sleep(update_interval)
                    continue
                
                print(f"\n💼 [POSITIONS] Обновление {len(open_positions)} позиций...")
                
                async with aiohttp.ClientSession() as session:
                    prices = {}
                    
                    for position in open_positions:
                        try:
                            price = await self._fetch_current_price(position.asset, session)
                            if price:
                                prices[position.asset] = price
                                
                                old_price = position.current_price
                                if old_price:
                                    change_pct = ((price - old_price) / old_price) * 100
                                    if abs(change_pct) > 1:
                                        print(f"   {position.asset}: ${old_price:,.2f} → ${price:,.2f} ({change_pct:+.2f}%)")
                        
                        except Exception as e:
                            print(f"⚠️ [POSITIONS] Ошибка получения цены {position.asset}: {e}")
                    
                    if prices:
                        await self.signal_generator.positions.update_prices(prices)
                
                closed_count = self.stats["positions_closed"]
                new_closed = await self._count_closed_positions()
                
                if new_closed > closed_count:
                    closed_diff = new_closed - closed_count
                    self.stats["positions_closed"] = new_closed
                    print(f"   ✅ Закрыто позиций: {closed_diff}")
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                print(f"❌ [POSITIONS] Ошибка в management loop: {e}")
                traceback.print_exc()
                await asyncio.sleep(60)
    
    async def _fetch_ohlcv(self, asset: str, session: aiohttp.ClientSession) -> Optional[pd.DataFrame]:
        """Получение OHLCV данных для актива"""
        
        try:
            symbol = f"{asset}USDT"
            
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'limit': 200
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if not data:
                    return None
                
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
                return df
                
        except Exception as e:
            print(f"⚠️ [OHLCV] Ошибка для {asset}: {e}")
            return None
    
    async def _fetch_current_price(self, asset: str, session: aiohttp.ClientSession) -> Optional[float]:
        """Получение текущей цены актива"""
        
        try:
            symbol = f"{asset}USDT"
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                return float(data.get('price', 0))
                
        except Exception as e:
            print(f"⚠️ [PRICE] Ошибка для {asset}: {e}")
            return None
    
    async def _send_trading_signal(self, signal):
        """Отправка торгового сигнала в Telegram"""
        
        try:
            message = self.signal_generator.format_signal_message(signal)
            
            import telegram
            bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            await bot.send_message(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode='HTML'
            )
            
            print(f"✅ [TRADING] Сигнал отправлен: {signal.asset} - {signal.signal}")
            
        except Exception as e:
            print(f"❌ [TRADING] Ошибка отправки сигнала: {e}")
            traceback.print_exc()
    
    async def _count_closed_positions(self) -> int:
        """Подсчёт закрытых позиций"""
        try:
            closed = await self.signal_generator.positions.get_closed_positions(limit=1000)
            return len(closed)
        except:
            return 0
    
    # ========================================================================
    # OPTIONAL LOOPS
    # ========================================================================
    
    async def _discovery_loop(self):
        """Обновление watchlist"""
        
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
    
    async def _mining_loop(self):
        """Цикл mining system (discovery + validation)"""
        
        if not self.mining_system:
            return
        
        await asyncio.sleep(3600)
        
        while not self._shutdown_flag:
            try:
                print(f"\n{'='*80}")
                print(f"⛏️ [MINING] Запуск mining cycle")
                print(f"{'='*80}")
                
                if not self.stats.get("last_mining_discovery") or \
                   (datetime.utcnow() - self.stats["last_mining_discovery"]).total_seconds() > 21600:
                    
                    result = await self.mining_system.run_discovery_cycle(
                        chains=self.supported_chains if self.chains_enabled else None,
                        max_wallets=settings.SMART_DISCOVERY_MAX_NEW_WALLETS
                    )
                    
                    self.stats["wallets_discovered"] += result["added"]
                    self.stats["last_mining_discovery"] = datetime.utcnow()
                
                if not self.stats.get("last_mining_validation") or \
                   (datetime.utcnow() - self.stats["last_mining_validation"]).total_seconds() > 86400:
                    
                    result = await self.mining_system.run_validation_cycle()
                    
                    self.stats["wallets_removed"] += result["removed"]
                    self.stats["last_mining_validation"] = datetime.utcnow()
                
                self.mining_system.print_stats()
            
            except Exception as e:
                print(f"❌ [MINING] Ошибка: {e}")
                traceback.print_exc()
            
            await asyncio.sleep(3600)
    
    async def _smart_discovery_loop(self):
        """Автоматический поиск успешных трейдеров"""
        
        if not self.smart_discovery or not self.wallet_db:
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
                traceback.print_exc()
            
            wait_hours = settings.SMART_DISCOVERY_INTERVAL_HOURS
            print(f"⏰ [SMART_DISCOVERY] Следующий запуск через {wait_hours}ч")
            await asyncio.sleep(wait_hours * 3600)
    
    async def _performance_tracker_loop(self):
        """Отслеживание результатов опубликованных сигналов"""
        
        if not self.pending_verification:
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
                            print(f"   ⚠️ Ошибка проверки {event.asset}: {e}")
                    
                    if hours_passed > 48:
                        to_remove.append(item)
                
                for item in to_remove:
                    self.pending_verification.remove(item)
                
                if checked_count > 0 and self.adaptive_thresholds:
                    stats = self.adaptive_thresholds.get_stats()
                    print(f"\n   📈 Текущая точность: {stats.get('accuracy', 0):.1%} ({stats['signals_tracked']} сигналов)")
                    print(f"   🎯 Режим рынка: {stats['regime']}")
                    print(f"   ⚙️ Текущие пороги: confidence≥{stats['current_thresholds']['min_confidence']}\n")
            
            except Exception as e:
                print(f"❌ [PERFORMANCE] Ошибка: {e}")
            
            await asyncio.sleep(3600)
    
    def _evaluate_signal_success(self, verdict: str, price_change: float) -> bool:
        """Оценка успешности сигнала"""
        
        threshold = getattr(settings, 'PERFORMANCE_SUCCESS_THRESHOLD', 0.05)
        
        if verdict == "bearish":
            return price_change < -threshold
        elif verdict == "bullish":
            return price_change > threshold
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
                traceback.print_exc()
            
            print(f"⏰ [VALIDATION] Следующая проверка через {settings.VALIDATION_INTERVAL_DAYS} дней")
            await asyncio.sleep(settings.VALIDATION_INTERVAL_DAYS * 86400)
    
    async def _market_regime_updater_loop(self):
        """Обновление режима рынка"""
        
        if not self.adaptive_thresholds:
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
                print(f"⚠️ [REGIME] Ошибка: {e}")
            
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
                    
                    if self.trading_enabled:
                        try:
                            positions_summary = self.signal_generator.positions.get_summary()
                            extended_stats["trading"] = {
                                "signals_generated": self.stats.get("trading_signals_generated", 0),
                                "signals_sent": self.stats.get("trading_signals_sent", 0),
                                "positions_open": positions_summary["total_open"],
                                "positions_closed": self.stats.get("positions_closed", 0),
                                "unrealized_pnl": positions_summary["total_unrealized_pnl_usd"]
                            }
                        except:
                            pass
                    
                    # НОВОЕ v4.2: Solana stats
                    extended_stats["solana"] = {
                        "rpc_switches": self.stats.get("solana_rpc_switches", 0),
                        "backoffs": self.stats.get("solana_backoffs", 0),
                        "current_rpc_index": self.current_solana_rpc_index,
                        "consecutive_failures": self.solana_consecutive_failures
                    }
                    
                    await self.alert_manager.send_daily_stats({"integrated": extended_stats})
                
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
                self.stats["trading_signals_generated"] = 0
                self.stats["trading_signals_sent"] = 0
            
            except Exception as e:
                print(f"⚠️ [STATS] Ошибка: {e}")
            
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
                                f"⚠️ Последний цикл был {silence//60} минут назад",
                                alert_type="health_check"
                            )
            
            except Exception as e:
                print(f"⚠️ [HEALTH] Ошибка: {e}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
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
            print(f"⚠️ [STATE] Ошибка загрузки: {e}")
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
            print(f"⚠️ [STATE] Ошибка: {e}")
    
    def _print_banner(self):
        """Вывод баннера при запуске"""
        print("\n" + "="*80)
        print("🐋 INTEGRATED SCHEDULER v4.2")
        print("="*80)
        print(f"Режим: {'DISCOVERY' if settings.ASSETS == '*' else 'ALLOWLIST'}")
        print(f"Канал: {settings.CHAT_ID}")
        print(f"Лимит: {settings.POSTS_PER_HOUR_CAP}/час")
        
        print(f"\n🐋 WHALE MONITORING:")
        print(f"  Smart Discovery: {'✅ каждые ' + str(settings.SMART_DISCOVERY_INTERVAL_HOURS) + 'ч' if settings.SMART_DISCOVERY_ENABLED and self.smart_discovery else '❌'}")
        print(f"  Adaptive Thresholds: {'✅' if settings.ADAPTIVE_THRESHOLDS_ENABLED else '❌'}")
        print(f"  Performance Tracking: {'✅' if settings.PERFORMANCE_TRACKING_ENABLED else '❌'}")
        print(f"  Validation: {'✅ каждые ' + str(settings.VALIDATION_INTERVAL_DAYS) + 'д' if settings.VALIDATION_ENABLED else '❌'}")
        print(f"  Mining System: {'✅' if self.mining_system else '❌'}")
        
        print(f"\n🌊 SOLANA (v4.2):")
        print(f"  Fallback RPC: ✅ {len(self.solana_rpc_endpoints)} endpoints")
        print(f"  Current RPC: {self.solana_rpc_endpoints[self.current_solana_rpc_index][:50]}...")
        print(f"  Intelligent Backoff: ✅")
        
        print(f"\n📈 TRADING SYSTEM:")
        if self.trading_enabled:
            print(f"  Status: ✅ Enabled")
            print(f"  Signal Generation: Every {getattr(settings, 'TRADING_SIGNAL_INTERVAL_HOURS', 1)}h")
            print(f"  Position Management: Real-time")
            print(f"  ML Predictions: 1h, 4h, 24h, 7d")
            print(f"  Risk Management: Auto SL/TP")
        else:
            print(f"  Status: ❌ Disabled")
        
        print(f"\n🌐 MULTI-CHAIN:")
        if self.chains_enabled:
            print(f"  Status: ✅ Enabled")
            print(f"  Chains: {', '.join(self.supported_chains)}")
        else:
            print(f"  Status: ❌ Disabled")
        
        print(f"\n📊 ANALYTICS:")
        if self.analytics_enabled:
            print(f"  Status: ✅ Enabled")
            print(f"  Modules: Sentiment, Risk, Correlation, Anomaly")
        else:
            print(f"  Status: ❌ Disabled")
        
        if self.wallet_db:
            print(f"\n💾 Tracked Wallets: {len(self.wallet_db.get_active_wallets())}")
        
        if self.adaptive_thresholds:
            thresholds = self.adaptive_thresholds.get_current_thresholds()
            print(f"\n⚙️ Стартовые пороги:")
            print(f"  Confidence: ≥{thresholds['min_confidence']}")
            print(f"  Size Rel: ≥{thresholds['min_size_rel']:.2%}")
            print(f"  Volume: ≥${thresholds['min_volume_24h']:,}")
        
        print("="*80 + "\n")
    
    async def shutdown(self):
        """Graceful shutdown"""
        print("\n⏹️ [SCHEDULER] Shutdown initiated...")
        self._shutdown_flag = True
        self._save_state()
        
        print("\n" + "="*80)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("="*80)
        
        print(f"\n🐋 WHALE MONITORING:")
        print(f"  События собрано: {self.stats['events_collected']}")
        print(f"  Прошло фильтры: {self.stats['events_qualified']}")
        print(f"  Опубликовано: {self.stats['events_published']}")
        
        if self.stats['events_successful'] + self.stats['events_failed'] > 0:
            total = self.stats['events_successful'] + self.stats['events_failed']
            accuracy = (self.stats['events_successful'] / total) * 100
            print(f"  Успешных: {self.stats['events_successful']}/{total} ({accuracy:.1f}%)")
        
        print(f"\n🌊 SOLANA:")
        print(f"  RPC Switches: {self.stats.get('solana_rpc_switches', 0)}")
        print(f"  Backoffs: {self.stats.get('solana_backoffs', 0)}")
        print(f"  Final RPC Index: {self.current_solana_rpc_index}")
        
        if self.trading_enabled:
            print(f"\n📈 TRADING SYSTEM:")
            print(f"  Сигналов сгенерировано: {self.stats.get('trading_signals_generated', 0)}")
            print(f"  Сигналов отправлено: {self.stats.get('trading_signals_sent', 0)}")
            print(f"  Позиций открыто: {self.stats.get('positions_opened', 0)}")
            print(f"  Позиций закрыто: {self.stats.get('positions_closed', 0)}")
            
            try:
                positions_summary = self.signal_generator.positions.get_summary()
                print(f"  Открытых позиций: {positions_summary['total_open']}")
                print(f"  Unrealized P&L: ${positions_summary['total_unrealized_pnl_usd']:,.2f}")
                
                metrics = await self.signal_generator.performance.calculate_metrics(period_days=30)
                if metrics.total_trades > 0:
                    print(f"\n  📊 Производительность (30д):")
                    print(f"     Сделок: {metrics.total_trades}")
                    print(f"     Win Rate: {metrics.win_rate:.1f}%")
                    print(f"     Total P&L: ${metrics.total_pnl_usd:,.2f}")
                    print(f"     Profit Factor: {metrics.profit_factor:.2f}")
            except:
                pass
        
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
        print(f"\n⏱️ Uptime: {uptime_hours:.1f}h")
        
        print("\n" + "="*80)
        print("✅ SHUTDOWN COMPLETE")
        print("="*80 + "\n")


scheduler = IntegratedScheduler()