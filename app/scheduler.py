# app/scheduler.py (РЕВОЛЮЦИОННАЯ ВЕРСИЯ - с самообучением и адаптацией)
"""
INTELLIGENT WHALE SCHEDULER v3.0

НОВЫЕ ВОЗМОЖНОСТИ:
✅ Smart Money Discovery - автопоиск успешных трейдеров
✅ Validation Engine - автоочистка базы от мусора
✅ Performance Tracking - отслеживание результатов
✅ Adaptive Thresholds - подстройка под рынок
✅ Learning System - самообучение на ошибках
✅ Market Regime Detection - определение bull/bear
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque
import statistics

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

# НОВЫЕ ИМПОРТЫ
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
        self.performance_history = deque(maxlen=100)  # последние 100 сигналов
        
        # Базовые пороги
        self.base_thresholds = {
            "min_confidence": 30,
            "min_size_rel": 0.10,
            "min_volume_24h": 1_000_000
        }
        
        # Модификаторы для разных режимов
        self.regime_modifiers = {
            "bull": {
                "min_confidence": +10,  # Строже в bull
                "min_size_rel": +0.05,
                "min_volume_24h": 1.5
            },
            "bear": {
                "min_confidence": -5,  # Мягче в bear
                "min_size_rel": -0.03,
                "min_volume_24h": 0.7
            },
            "sideways": {
                "min_confidence": 0,
                "min_size_rel": 0,
                "min_volume_24h": 1.0
            }
        }
    
    def detect_market_regime(self, btc_change_7d: float) -> str:
        """
        Определяет режим рынка на основе изменения BTC
        
        Args:
            btc_change_7d: Изменение BTC за 7 дней (%)
        
        Returns:
            "bull" / "bear" / "sideways"
        """
        
        if btc_change_7d > 10:
            return "bull"
        elif btc_change_7d < -10:
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
        """
        Возвращает текущие пороги с учётом режима рынка и производительности
        """
        
        modifiers = self.regime_modifiers[self.market_regime]
        
        thresholds = {
            "min_confidence": self.base_thresholds["min_confidence"] + modifiers["min_confidence"],
            "min_size_rel": self.base_thresholds["min_size_rel"] + modifiers["min_size_rel"],
            "min_volume_24h": int(self.base_thresholds["min_volume_24h"] * modifiers["min_volume_24h"])
        }
        
        # Адаптация на основе производительности
        if len(self.performance_history) >= 20:
            recent_accuracy = self._calculate_recent_accuracy()
            
            if recent_accuracy < 0.60:  # Точность <60% - ужесточаем
                thresholds["min_confidence"] += 10
                print(f"⚠️  [ADAPTIVE] Точность низкая ({recent_accuracy:.1%}), повышаю min_confidence до {thresholds['min_confidence']}")
            
            elif recent_accuracy > 0.80:  # Точность >80% - ослабляем
                thresholds["min_confidence"] = max(30, thresholds["min_confidence"] - 5)
                print(f"✅ [ADAPTIVE] Точность высокая ({recent_accuracy:.1%}), понижаю min_confidence до {thresholds['min_confidence']}")
        
        return thresholds
    
    def add_performance_result(self, signal_data: Dict):
        """
        Добавляет результат сигнала для обучения
        
        Args:
            signal_data: {
                "success": bool,
                "confidence": int,
                "verdict": str,
                "price_change_24h": float
            }
        """
        self.performance_history.append(signal_data)
    
    def _calculate_recent_accuracy(self) -> float:
        """Считает точность последних 20 сигналов"""
        if len(self.performance_history) < 20:
            return 0.5
        
        recent = list(self.performance_history)[-20:]
        successful = sum(1 for s in recent if s.get("success", False))
        
        return successful / len(recent)
    
    def get_stats(self) -> Dict:
        """Статистика адаптивной системы"""
        
        if not self.performance_history:
            return {
                "regime": self.market_regime,
                "signals_tracked": 0,
                "accuracy": 0.0
            }
        
        successful = sum(1 for s in self.performance_history if s.get("success", False))
        
        return {
            "regime": self.market_regime,
            "signals_tracked": len(self.performance_history),
            "accuracy": successful / len(self.performance_history) if self.performance_history else 0.0,
            "current_thresholds": self.get_current_thresholds()
        }


class WalletDatabase:
    """
    Простая база данных отслеживаемых кошельков (если нет SQLite)
    """
    
    def __init__(self, db_path: str = "data/tracked_wallets.json"):
        self.db_path = db_path
        self.wallets = []
        self._load()
    
    def _load(self):
        """Загружает кошельки из файла"""
        try:
            with open(self.db_path, 'r') as f:
                self.wallets = json.load(f)
            print(f"📂 [WALLET_DB] Загружено {len(self.wallets)} кошельков")
        except FileNotFoundError:
            print("📂 [WALLET_DB] Новая база данных")
            self.wallets = []
        except Exception as e:
            print(f"⚠️  [WALLET_DB] Ошибка загрузки: {e}")
            self.wallets = []
    
    def _save(self):
        """Сохраняет кошельки в файл"""
        try:
            import os
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with open(self.db_path, 'w') as f:
                json.dump(self.wallets, f, indent=2)
        except Exception as e:
            print(f"⚠️  [WALLET_DB] Ошибка сохранения: {e}")
    
    def add_wallet(self, wallet_stats):
        """Добавляет новый кошелёк"""
        
        # Проверяем дубликаты
        existing = self.get_wallet(wallet_stats.address, wallet_stats.chain)
        if existing:
            print(f"⚠️  [WALLET_DB] Кошелёк уже существует: {wallet_stats.address[:10]}...")
            return False
        
        wallet_data = {
            "address": wallet_stats.address,
            "chain": wallet_stats.chain,
            "roi_30d": wallet_stats.roi_30d,
            "roi_90d": wallet_stats.roi_90d,
            "win_rate": wallet_stats.win_rate,
            "total_trades": wallet_stats.total_trades,
            "specialization": wallet_stats.specialization,
            "discovered_at": datetime.utcnow().isoformat(),
            "discovered_via": wallet_stats.best_trades[0]["token"] if wallet_stats.best_trades else "unknown",
            "last_trade_at": wallet_stats.last_trade_at.isoformat(),
            "is_active": True,
            "score": 50  # начальный скор
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
            print(f"❌ [WALLET_DB] Деактивирован: {address[:10]}... (причина: {reason})")
    
    def update_wallet_score(self, address: str, chain: str, new_score: int):
        """Обновляет скор кошелька"""
        wallet = self.get_wallet(address, chain)
        if wallet:
            old_score = wallet.get("score", 50)
            wallet["score"] = new_score
            wallet["score_updated_at"] = datetime.utcnow().isoformat()
            self._save()
            
            if abs(new_score - old_score) > 10:
                print(f"📊 [WALLET_DB] Скор обновлён: {address[:10]}... {old_score} → {new_score}")


class WhaleScheduler:
    """
    РЕВОЛЮЦИОННЫЙ КООРДИНАТОР с самообучением и адаптацией
    """
    
    def __init__(self):
        # Существующие компоненты
        self.discovery = DiscoveryEngine()
        self.scorer = EventScorer()
        self.price_provider = PriceProvider()
        self.news_gate = NewsGate()
        self.publisher = WhalePublisher()
        self.chart_renderer = SparklineRenderer()
        self.history_manager = HistoryManager()
        self.alert_manager = get_alert_manager()
        
        # НОВЫЕ компоненты
        self.adaptive_thresholds = AdaptiveThresholds()
        self.wallet_db = WalletDatabase()
        self.smart_discovery = None  # Инициализируем позже
        
        # Очереди и кэши
        self.publication_queue: List[Dict] = []
        self.seen_keys: set = set()
        self.recent_publications = deque(maxlen=settings.POSTS_PER_HOUR_CAP)
        
        # Расширенная статистика
        self.stats = {
            "events_collected": 0,
            "events_qualified": 0,
            "events_published": 0,
            "events_successful": 0,  # НОВОЕ
            "events_failed": 0,  # НОВОЕ
            "wallets_discovered": 0,  # НОВОЕ
            "wallets_removed": 0,  # НОВОЕ
            "errors": 0,
            "last_cycle_time": None,
            "last_discovery_run": None,  # НОВОЕ
            "last_validation_run": None,  # НОВОЕ
            "start_time": datetime.utcnow()
        }
        
        # Очередь для проверки результатов
        self.pending_verification = deque(maxlen=200)  # НОВОЕ
        
        self._load_state()
    
    async def run(self):
        """Главный цикл с НОВЫМИ компонентами"""
        print("=" * 80)
        print("🧠 INTELLIGENT WHALE MONITOR v3.0 [SELF-LEARNING]")
        print("=" * 80)
        print(f"Режим: {'DISCOVERY (весь рынок)' if settings.ASSETS == '*' else 'ALLOWLIST'}")
        print(f"Канал: {settings.CHAT_ID}")
        print(f"Лимит публикаций: {settings.POSTS_PER_HOUR_CAP}/час")
        print(f"🧠 Smart Discovery: {'✅ Включен' if SMART_DISCOVERY_AVAILABLE else '❌ Отключен'}")
        print(f"🔄 Adaptive Thresholds: ✅ Включен")
        print(f"📊 Performance Tracking: ✅ Включен")
        print(f"👛 Tracked Wallets: {len(self.wallet_db.get_active_wallets())}")
        print("=" * 80)
        
        # Инициализируем Smart Discovery
        if SMART_DISCOVERY_AVAILABLE and hasattr(settings, 'ETHERSCAN_API_KEY'):
            self.smart_discovery = SmartMoneyDiscovery(
                etherscan_key=settings.ETHERSCAN_API_KEY,
                coingecko_key=getattr(settings, 'COINGECKO_API_KEY', None)
            )
        
        # Отправляем уведомление о запуске
        try:
            await self.alert_manager.send_startup_notification()
        except Exception as e:
            print(f"⚠️  Не удалось отправить уведомление о запуске: {e}")
        
        tasks = [
            self._discovery_loop(),  # Обновление watchlist
            self._smart_discovery_loop(),  # НОВОЕ: Поиск умных трейдеров
            self._validation_loop(),  # НОВОЕ: Очистка базы
            self._whale_monitor_loop(),  # Основной мониторинг
            self._performance_tracker_loop(),  # НОВОЕ: Проверка результатов
            self._market_regime_updater_loop(),  # НОВОЕ: Обновление режима рынка
            self._stats_reporter_loop(),
            self._health_check_loop(),
        ]
        
        await asyncio.gather(*tasks)
    
    # ========================================================================
    # НОВЫЙ ЦИКЛ: SMART MONEY DISCOVERY
    # ========================================================================
    
    async def _smart_discovery_loop(self):
        """
        НОВОЕ: Автоматически находит успешных трейдеров
        
        Запускается каждые 6 часов (настраивается)
        """
        
        if not SMART_DISCOVERY_AVAILABLE or not self.smart_discovery:
            print("⏭️  [SMART_DISCOVERY] Отключен")
            return
        
        # Первый запуск через 30 минут после старта
        await asyncio.sleep(1800)
        
        while True:
            try:
                print(f"\n{'=' * 80}")
                print(f"🔍 [SMART_DISCOVERY] Запуск поиска успешных трейдеров")
                print(f"{'=' * 80}")
                
                start_time = datetime.utcnow()
                
                async with self.smart_discovery:
                    wallets = await self.smart_discovery.discover_new_wallets()
                
                # Добавляем найденных трейдеров в базу
                added_count = 0
                for wallet_stats in wallets:
                    if self.wallet_db.add_wallet(wallet_stats):
                        added_count += 1
                
                self.stats["wallets_discovered"] += added_count
                self.stats["last_discovery_run"] = datetime.utcnow()
                
                elapsed = (datetime.utcnow() - start_time).seconds
                
                print(f"\n{'=' * 80}")
                print(f"✅ [SMART_DISCOVERY] Завершён за {elapsed}с")
                print(f"   Найдено: {len(wallets)} кошельков")
                print(f"   Добавлено: {added_count} новых")
                print(f"   Всего в базе: {len(self.wallet_db.get_active_wallets())} активных")
                print(f"{'=' * 80}\n")
                
                # Уведомление если нашли много
                if added_count > 5:
                    await self.alert_manager.send_notification(
                        f"🎉 Smart Discovery нашёл {added_count} новых успешных трейдеров!"
                    )
                
            except Exception as e:
                print(f"❌ [SMART_DISCOVERY] Ошибка: {e}")
                import traceback
                traceback.print_exc()
                
                await self.alert_manager.send_critical_alert(
                    "Smart Discovery Error",
                    "Ошибка в цикле поиска трейдеров",
                    str(e)
                )
            
            # Следующий запуск через 6 часов
            wait_hours = getattr(settings, 'SMART_DISCOVERY_INTERVAL_HOURS', 6)
            print(f"⏰ [SMART_DISCOVERY] Следующий запуск через {wait_hours}ч")
            await asyncio.sleep(wait_hours * 3600)
    
    # ========================================================================
    # НОВЫЙ ЦИКЛ: VALIDATION ENGINE
    # ========================================================================
    
    async def _validation_loop(self):
        """
        НОВОЕ: Автоматически очищает базу от неактуальных кошельков
        
        Запускается каждую неделю
        """
        
        # Первая проверка через 24 часа после старта
        await asyncio.sleep(86400)
        
        while True:
            try:
                print(f"\n{'=' * 80}")
                print(f"🧹 [VALIDATION] Запуск очистки базы данных")
                print(f"{'=' * 80}")
                
                active_wallets = self.wallet_db.get_active_wallets()
                
                print(f"   Проверяю {len(active_wallets)} активных кошельков...")
                
                removed_count = 0
                
                for wallet in active_wallets:
                    address = wallet["address"]
                    chain = wallet["chain"]
                    
                    # Проверка 1: Неактивность >60 дней
                    last_trade = datetime.fromisoformat(wallet.get("last_trade_at", datetime.utcnow().isoformat()))
                    days_inactive = (datetime.utcnow() - last_trade).days
                    
                    if days_inactive > 60:
                        self.wallet_db.deactivate_wallet(address, chain, f"Неактивен {days_inactive} дней")
                        removed_count += 1
                        continue
                    
                    # Проверка 2: Низкий скор <30
                    score = wallet.get("score", 50)
                    if score < 30:
                        self.wallet_db.deactivate_wallet(address, chain, f"Низкий скор ({score})")
                        removed_count += 1
                        continue
                    
                    # Проверка 3: ROI отрицательный (если есть данные)
                    roi_30d = wallet.get("roi_30d", 0)
                    if roi_30d < -0.20:  # -20%
                        self.wallet_db.deactivate_wallet(address, chain, f"Отрицательный ROI ({roi_30d:.1%})")
                        removed_count += 1
                        continue
                
                self.stats["wallets_removed"] += removed_count
                self.stats["last_validation_run"] = datetime.utcnow()
                
                remaining = len(self.wallet_db.get_active_wallets())
                
                print(f"\n{'=' * 80}")
                print(f"✅ [VALIDATION] Очистка завершена")
                print(f"   Проверено: {len(active_wallets)} кошельков")
                print(f"   Удалено: {removed_count}")
                print(f"   Осталось активных: {remaining}")
                print(f"{'=' * 80}\n")
                
                # Уведомление если удалили много
                if removed_count > 10:
                    await self.alert_manager.send_notification(
                        f"🧹 Validation удалил {removed_count} неактуальных кошельков из базы"
                    )
                
            except Exception as e:
                print(f"❌ [VALIDATION] Ошибка: {e}")
                import traceback
                traceback.print_exc()
            
            # Следующая проверка через 7 дней
            print(f"⏰ [VALIDATION] Следующая проверка через 7 дней")
            await asyncio.sleep(7 * 86400)
    
    # ========================================================================
    # НОВЫЙ ЦИКЛ: PERFORMANCE TRACKER
    # ========================================================================
    
    async def _performance_tracker_loop(self):
        """
        НОВОЕ: Отслеживает результаты опубликованных сигналов
        
        Проверяет изменение цены через 1ч, 6ч, 24ч
        """
        
        # Ждём первые публикации
        await asyncio.sleep(3600)
        
        while True:
            try:
                if not self.pending_verification:
                    await asyncio.sleep(600)
                    continue
                
                print(f"\n📊 [PERFORMANCE] Проверка результатов {len(self.pending_verification)} сигналов...")
                
                now = datetime.utcnow()
                checked_count = 0
                
                # Проверяем сигналы готовые к верификации
                to_remove = []
                
                for item in list(self.pending_verification):
                    event = item["event"]
                    verdict = item["verdict"]
                    confidence = item["confidence"]
                    published_at = item["published_at"]
                    
                    hours_passed = (now - published_at).total_seconds() / 3600
                    
                    # Проверяем через 24 часа
                    if hours_passed >= 24 and not item.get("checked_24h"):
                        try:
                            # Получаем текущую цену
                            async with aiohttp.ClientSession() as session:
                                price_change = await self._get_price_change(event.asset, session)
                            
                            if price_change is not None:
                                # Оцениваем успешность
                                success = self._evaluate_signal_success(verdict, price_change)
                                
                                # Сохраняем результат
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
                                
                                item["checked_24h"] = True
                                checked_count += 1
                                
                                print(f"   {'✅' if success else '❌'} {event.asset}: {verdict} → {price_change:+.1%} "
                                      f"({'успех' if success else 'провал'})")
                        
                        except Exception as e:
                            print(f"   ⚠️  Ошибка проверки {event.asset}: {e}")
                    
                    # Удаляем проверенные >48ч назад
                    if hours_passed > 48:
                        to_remove.append(item)
                
                # Удаляем старые
                for item in to_remove:
                    self.pending_verification.remove(item)
                
                if checked_count > 0:
                    # Показываем текущую точность
                    stats = self.adaptive_thresholds.get_stats()
                    accuracy = stats.get("accuracy", 0)
                    
                    print(f"\n   📈 Текущая точность: {accuracy:.1%} ({stats['signals_tracked']} сигналов)")
                    print(f"   🎯 Режим рынка: {stats['regime']}")
                    print(f"   ⚙️  Текущие пороги: {stats['current_thresholds']}\n")
                
            except Exception as e:
                print(f"❌ [PERFORMANCE] Ошибка: {e}")
            
            await asyncio.sleep(3600)  # Проверяем каждый час
    
    def _evaluate_signal_success(self, verdict: str, price_change: float) -> bool:
        """
        Оценивает успешность сигнала
        
        Логика:
        - bearish (приток на биржу) → успех если цена упала >2%
        - bullish (отток) → успех если цена выросла >2%
        - neutral → всегда успех (не учитываем)
        """
        
        if verdict == "bearish":
            return price_change < -0.02
        elif verdict == "bullish":
            return price_change > 0.02
        else:
            return True  # neutral не учитываем
    
    async def _get_price_change(self, asset: str, session: aiohttp.ClientSession) -> Optional[float]:
        """Получает изменение цены за 24ч с CoinGecko"""
        
        try:
            # Маппинг символов в CoinGecko IDs
            symbol_to_id = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "BNB": "binancecoin",
                "SOL": "solana",
                "MATIC": "matic-network",
                "AVAX": "avalanche-2",
                "ARB": "arbitrum",
                "OP": "optimism"
            }
            
            coin_id = symbol_to_id.get(asset)
            if not coin_id:
                return None
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if coin_id in data and "usd_24h_change" in data[coin_id]:
                    return data[coin_id]["usd_24h_change"] / 100
        
        except Exception:
            pass
        
        return None
    
    # ========================================================================
    # НОВЫЙ ЦИКЛ: MARKET REGIME UPDATER
    # ========================================================================
    
    async def _market_regime_updater_loop(self):
        """
        НОВОЕ: Обновляет режим рынка каждые 4 часа
        """
        
        while True:
            try:
                # Получаем изменение BTC за 7 дней
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
                print(f"⚠️  [REGIME] Ошибка обновления режима: {e}")
            
            await asyncio.sleep(14400)  # Каждые 4 часа
    
    # ========================================================================
    # УЛУЧШЕННЫЙ ОСНОВНОЙ ЦИКЛ
    # ========================================================================
    
    async def _whale_monitor_loop(self):
        """Мониторинг крупных перемещений (УЛУЧШЕННЫЙ)"""
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
                        # УЛУЧШЕНО: Используем адаптивные пороги
                        await self._process_events_with_adaptive_thresholds(events)
                
                start_time = datetime.utcnow()
                await self._publish_from_queue()
                
                consecutive_errors = 0
                
                print(f"⏰ [WHALE] Следующая проверка через {settings.POLL_SECONDS}с")
                await asyncio.sleep(settings.POLL_SECONDS)
                
            except Exception as e:
                consecutive_errors += 1
                self.stats["errors"] += 1
                
                print(f"❌ [WHALE] Критическая ошибка ({consecutive_errors}/3): {e}")
                
                if consecutive_errors >= 3:
                    await self.alert_manager.send_critical_alert(
                        "Monitor Loop Error",
                        f"Критическая ошибка в цикле мониторинга (подряд: {consecutive_errors})",
                        str(e)
                    )
                
                await asyncio.sleep(300)
    
    async def _process_events_with_adaptive_thresholds(self, events: List[WhaleEvent]):
        """
        УЛУЧШЕНО: Обработка событий с использованием адаптивных порогов
        """
        
        print(f"🔄 [PIPELINE] Обработка {len(events)} событий (адаптивный режим)")
        
        # Получаем текущие пороги
        thresholds = self.adaptive_thresholds.get_current_thresholds()
        
        print(f"⚙️  [THRESHOLDS] "
              f"Confidence≥{thresholds['min_confidence']}, "
              f"SizeRel≥{thresholds['min_size_rel']:.2%}, "
              f"Volume≥${thresholds['min_volume_24h']:,}")
        
        async with aiohttp.ClientSession() as session:
            qualified_events = []
            
            filter_stats = {
                "dedup": 0,
                "asset_not_allowed": 0,
                "internal_bridge": 0,
                "price_failed": 0,
                "below_threshold": 0,
                "confidence_too_low": 0,  # НОВОЕ
                "passed": 0
            }
            
            for event in events:
                try:
                    # Стандартные фильтры
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
                    
                    # Обогащение
                    await self.price_provider.enrich_event_with_market_data(event, session)
                    
                    # Проверка базового порога
                    if event.amount_usd < event.min_usd_threshold:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    # НОВОЕ: Ранняя проверка confidence
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if confidence < thresholds["min_confidence"]:
                        filter_stats["confidence_too_low"] += 1
                        continue
                    
                    # НОВОЕ: Проверка size_rel и volume
                    size_rel = event.amount_usd / event.market.volume_24h_usd if event.market.volume_24h_usd else 0
                    
                    if size_rel < thresholds["min_size_rel"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    if event.market.volume_24h_usd < thresholds["min_volume_24h"]:
                        filter_stats["below_threshold"] += 1
                        continue
                    
                    # ✅ Прошло адаптивные фильтры!
                    filter_stats["passed"] += 1
                    qualified_events.append(event)
                    self.seen_keys.add(dedup_key)
                
                except Exception as e:
                    print(f"⚠️  [FILTER] Ошибка обработки: {e}")
                    self.stats["errors"] += 1
                    continue
            
            self.stats["events_qualified"] += len(qualified_events)
            
            print(f"✅ [QUALIFY] Прошло адаптивные фильтры: {len(qualified_events)} событий")
            print(f"📊 [STATS] "
                  f"Дубл: {filter_stats['dedup']}, "
                  f"LowConf: {filter_stats['confidence_too_low']}, "
                  f"Ниже: {filter_stats['below_threshold']}, "
                  f"✅: {filter_stats['passed']}")
            
            if not qualified_events:
                return
            
            # Определение фаз
            qualified_events = self.scorer.detect_phase(qualified_events)
            
            # Добавление в очередь
            for event in qualified_events:
                try:
                    verdict, confidence = self.scorer.calculate_verdict_and_confidence(event)
                    
                    if not self.scorer.should_publish(event, verdict, confidence):
                        continue
                    
                    # История
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
                    print(f"⚠️  [SCORE] Ошибка оценки: {e}")
                    continue
            
            self.publication_queue.sort(key=lambda x: x["priority"], reverse=True)
            print(f"📋 [QUEUE] В очереди: {len(self.publication_queue)} событий")
    
    async def _publish_from_queue(self):
        """Публикация с добавлением в очередь верификации"""
        
        now = datetime.utcnow()
        
        while self.recent_publications and (now - self.recent_publications[0]).seconds > 3600:
            self.recent_publications.popleft()
        
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
                        
                        # НОВОЕ: Добавляем в очередь верификации
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
                await self.alert_manager.send_critical_alert(
                    "Publish Error",
                    f"Не удалось опубликовать событие {event.asset}",
                    str(e)
                )
    
    # ========================================================================
    # ОСТАЛЬНЫЕ ЦИКЛЫ (без изменений, но с улучшенной статистикой)
    # ========================================================================
    
    async def _discovery_loop(self):
        """Обновление watchlist (без изменений)"""
        if settings.ASSETS != '*':
            print("⏭️  Discovery отключен (ALLOWLIST режим)")
            return
        
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
    
    async def _stats_reporter_loop(self):
        """Отправка расширенной статистики"""
        
        await asyncio.sleep(86400)
        
        while True:
            try:
                # УЛУЧШЕНО: Добавляем статистику обучения
                adaptive_stats = self.adaptive_thresholds.get_stats()
                
                extended_stats = {
                    **self.stats,
                    "adaptive": adaptive_stats,
                    "wallet_db": {
                        "total": len(self.wallet_db.wallets),
                        "active": len(self.wallet_db.get_active_wallets())
                    }
                }
                
                await self.alert_manager.send_daily_stats(extended_stats)
                
                # Сброс счётчиков
                self.stats["events_collected"] = 0
                self.stats["events_qualified"] = 0
                self.stats["events_published"] = 0
                self.stats["events_successful"] = 0
                self.stats["events_failed"] = 0
                self.stats["wallets_discovered"] = 0
                self.stats["wallets_removed"] = 0
                self.stats["errors"] = 0
                
            except Exception as e:
                print(f"⚠️  [STATS] Ошибка отправки статистики: {e}")
            
            await asyncio.sleep(86400)
    
    async def _health_check_loop(self):
        """Проверка здоровья (без изменений)"""
        
        while True:
            try:
                await asyncio.sleep(300)
                
                now = datetime.utcnow()
                
                if self.stats["last_cycle_time"]:
                    time_since_cycle = (now - self.stats["last_cycle_time"]).seconds
                    
                    if time_since_cycle > 600:
                        await self.alert_manager.send_warning(
                            f"⚠️ Последний цикл был {time_since_cycle//60} минут назад. Возможна проблема."
                        )
                
            except Exception as e:
                print(f"⚠️  [HEALTH] Ошибка health check: {e}")
    
    def _is_asset_allowed(self, event: WhaleEvent) -> bool:
        """Проверка разрешённости актива (без изменений)"""
        if settings.ASSETS == '*':
            return self.discovery.is_in_watchlist(event.chain, event.asset)
        else:
            return event.asset in settings.ASSETS_LIST
    
    def _load_state(self):
        """Загрузка состояния (без изменений)"""
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
        """Сохранение состояния (без изменений)"""
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
        """Корректное завершение (без изменений)"""
        print("\n⏹️  [SHUTDOWN] Остановка...")
        self._save_state()
        print("✅ [SHUTDOWN] Готово")