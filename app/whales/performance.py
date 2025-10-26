# app/whales/performance_tracker.py
"""
PERFORMANCE TRACKER v1.0

Отслеживает результаты опубликованных сигналов и обучает систему.

Функции:
- Проверка изменения цены через 1ч/6ч/24ч/7д
- Оценка успешности сигналов (bullish/bearish)
- Обновление скоров кошельков
- Расчёт точности по типам сигналов
- Генерация отчётов производительности
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from collections import defaultdict

from app import settings


class SignalOutcome(Enum):
    """Результат сигнала"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    NEUTRAL = "neutral"


@dataclass
class SignalPerformance:
    """Производительность сигнала"""
    signal_id: str
    asset: str
    chain: str
    verdict: str  # bullish/bearish/neutral
    confidence: int
    
    # Данные публикации
    published_at: datetime
    initial_price: float
    
    # Изменения цены
    price_change_1h: Optional[float] = None
    price_change_6h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_7d: Optional[float] = None
    
    # Экстремумы
    max_gain: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    # Результат
    outcome: SignalOutcome = SignalOutcome.PENDING
    outcome_checked_at: Optional[datetime] = None
    
    # Дополнительно
    wallets_involved: List[str] = None
    signal_type: str = "smart_money"  # smart_money, mining, onchain, social
    
    # Mining данные (для mining сигналов)
    mining_data: Optional[Dict] = None  # {"difficulty_change": 15.2, "hashrate_change": 8.5, etc}
    
    def to_dict(self):
        """Конвертация в словарь для сохранения"""
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        if self.outcome_checked_at:
            data["outcome_checked_at"] = self.outcome_checked_at.isoformat()
        data["outcome"] = self.outcome.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Создание из словаря"""
        data["published_at"] = datetime.fromisoformat(data["published_at"])
        if data.get("outcome_checked_at"):
            data["outcome_checked_at"] = datetime.fromisoformat(data["outcome_checked_at"])
        data["outcome"] = SignalOutcome(data["outcome"])
        return cls(**data)


class PerformanceTracker:
    """
    Отслеживает и анализирует производительность сигналов
    """
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or settings.PERFORMANCE_LOG_FILE
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Параметры из settings
        self.check_intervals = settings.PERFORMANCE_CHECK_INTERVALS
        self.success_threshold_bullish = settings.PERFORMANCE_SUCCESS_THRESHOLD_BULLISH
        self.success_threshold_bearish = settings.PERFORMANCE_SUCCESS_THRESHOLD_BEARISH
        self.history_size = settings.PERFORMANCE_HISTORY_SIZE
        
        # Внутреннее хранилище
        self.tracked_signals: List[SignalPerformance] = []
        self._load_history()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ========================================================================
    # TRACKING
    # ========================================================================
    
    def track_signal(
        self,
        signal_id: str,
        asset: str,
        chain: str,
        verdict: str,
        confidence: int,
        initial_price: float,
        wallets_involved: List[str] = None,
        signal_type: str = "smart_money",
        mining_data: Dict = None
    ):
        """
        Начинает отслеживание нового сигнала
        
        Args:
            signal_id: Уникальный ID сигнала
            asset: Актив (BTC, ETH, etc)
            chain: Блокчейн
            verdict: bullish/bearish/neutral
            confidence: Уверенность 0-100
            initial_price: Цена на момент публикации
            wallets_involved: Список адресов кошельков
            signal_type: Тип сигнала (smart_money, mining, onchain, social)
            mining_data: Данные майнинга для mining сигналов
        """
        
        performance = SignalPerformance(
            signal_id=signal_id,
            asset=asset,
            chain=chain,
            verdict=verdict,
            confidence=confidence,
            published_at=datetime.utcnow(),
            initial_price=initial_price,
            wallets_involved=wallets_involved or [],
            signal_type=signal_type,
            mining_data=mining_data
        )
        
        self.tracked_signals.append(performance)
        
        # Ограничиваем размер истории
        if len(self.tracked_signals) > self.history_size:
            self.tracked_signals = self.tracked_signals[-self.history_size:]
        
        self._save_history()
        
        print(f"📊 [TRACKING] Начато отслеживание: {asset} ({verdict}, conf: {confidence})")
    
    # ========================================================================
    # CHECKING
    # ========================================================================
    
    async def check_pending_signals(self) -> Dict:
        """
        Проверяет все ожидающие сигналы
        
        Returns:
            {
                "checked": int,
                "success": int,
                "failure": int,
                "pending": int
            }
        """
        
        print(f"\n{'=' * 80}")
        print(f"📊 PERFORMANCE TRACKER - Проверка сигналов")
        print(f"{'=' * 80}")
        
        checked = 0
        success = 0
        failure = 0
        pending = 0
        
        now = datetime.utcnow()
        
        for signal in self.tracked_signals:
            # Пропускаем уже проверенные
            if signal.outcome != SignalOutcome.PENDING:
                continue
            
            hours_passed = (now - signal.published_at).total_seconds() / 3600
            
            # Проверяем через 24 часа
            if hours_passed >= 24 and not signal.price_change_24h:
                try:
                    print(f"   Проверяю {signal.asset} (24ч)...", end=" ")
                    
                    # Получаем текущую цену
                    current_price = await self._get_current_price(signal.asset)
                    
                    if current_price:
                        # Рассчитываем изменение
                        price_change = (current_price - signal.initial_price) / signal.initial_price
                        signal.price_change_24h = price_change
                        
                        # Оцениваем результат
                        outcome = self._evaluate_signal(signal.verdict, price_change)
                        signal.outcome = outcome
                        signal.outcome_checked_at = datetime.utcnow()
                        
                        checked += 1
                        
                        if outcome == SignalOutcome.SUCCESS:
                            success += 1
                            print(f"✅ SUCCESS ({price_change:+.1%})")
                        elif outcome == SignalOutcome.FAILURE:
                            failure += 1
                            print(f"❌ FAILURE ({price_change:+.1%})")
                        else:
                            print(f"⚪ NEUTRAL ({price_change:+.1%})")
                        
                        # Обновляем скоры кошельков
                        if settings.PERFORMANCE_UPDATE_WALLET_SCORES and signal.wallets_involved:
                            await self._update_wallet_scores(signal)
                    
                    else:
                        print(f"⚠️  Цена не найдена")
                        pending += 1
                
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                    pending += 1
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            else:
                pending += 1
        
        # Сохраняем обновлённые данные
        self._save_history()
        
        print(f"\n{'=' * 80}")
        print(f"📈 ИТОГИ ПРОВЕРКИ")
        print(f"{'=' * 80}")
        print(f"Проверено: {checked} сигналов")
        print(f"✅ Успешных: {success}")
        print(f"❌ Неудачных: {failure}")
        print(f"⏳ Ожидают: {pending}")
        
        if checked > 0:
            accuracy = success / checked * 100
            print(f"🎯 Точность: {accuracy:.1f}%")
        
        print(f"{'=' * 80}\n")
        
        return {
            "checked": checked,
            "success": success,
            "failure": failure,
            "pending": pending
        }
    
    def _evaluate_signal(self, verdict: str, price_change: float) -> SignalOutcome:
        """
        Оценивает успешность сигнала
        
        Args:
            verdict: bullish/bearish/neutral
            price_change: Изменение цены (0.05 = +5%)
        
        Returns:
            SignalOutcome
        """
        
        if verdict == "bullish":
            # Bullish сигнал успешен если цена выросла >2%
            if price_change >= self.success_threshold_bullish:
                return SignalOutcome.SUCCESS
            elif price_change <= -self.success_threshold_bullish:
                return SignalOutcome.FAILURE
            else:
                return SignalOutcome.NEUTRAL
        
        elif verdict == "bearish":
            # Bearish сигнал успешен если цена упала >2%
            if price_change <= self.success_threshold_bearish:
                return SignalOutcome.SUCCESS
            elif price_change >= -self.success_threshold_bearish:
                return SignalOutcome.FAILURE
            else:
                return SignalOutcome.NEUTRAL
        
        else:
            # Neutral всегда neutral
            return SignalOutcome.NEUTRAL
    
    async def _get_current_price(self, asset: str) -> Optional[float]:
        """Получает текущую цену актива с CoinGecko"""
        
        # Маппинг символов в CoinGecko IDs
        symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "ARB": "arbitrum",
            "OP": "optimism",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "AAVE": "aave",
            "XRP": "ripple",
            "DOGE": "dogecoin",
            "TRX": "tron"
        }
        
        coin_id = symbol_to_id.get(asset)
        if not coin_id:
            return None
        
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd"
            }
            
            if settings.COINGECKO_API_KEY:
                params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                if coin_id in data and "usd" in data[coin_id]:
                    return data[coin_id]["usd"]
        
        except Exception:
            pass
        
        return None
    
    async def _update_wallet_scores(self, signal: SignalPerformance):
        """
        Обновляет скоры кошельков на основе результата сигнала
        
        Args:
            signal: Сигнал с результатом
        """
        
        # Это будет интеграция с WalletDatabase
        # Пока просто логируем
        adjustment = settings.PERFORMANCE_SCORE_ADJUSTMENT
        
        if signal.outcome == SignalOutcome.SUCCESS:
            print(f"      💎 Кошельки получают +{adjustment} к скору")
        elif signal.outcome == SignalOutcome.FAILURE:
            print(f"      ⚠️  Кошельки получают -{adjustment} к скору")
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_accuracy_stats(self) -> Dict:
        """
        Рассчитывает статистику точности
        
        Returns:
            {
                "overall": float,
                "by_verdict": {"bullish": float, "bearish": float},
                "by_signal_type": {"smart_money": float, ...},
                "total_signals": int,
                "checked_signals": int
            }
        """
        
        # Только завершённые сигналы
        completed = [s for s in self.tracked_signals if s.outcome != SignalOutcome.PENDING]
        
        if not completed:
            return {
                "overall": 0.0,
                "by_verdict": {},
                "by_signal_type": {},
                "total_signals": len(self.tracked_signals),
                "checked_signals": 0
            }
        
        # Общая точность
        successful = sum(1 for s in completed if s.outcome == SignalOutcome.SUCCESS)
        overall_accuracy = successful / len(completed)
        
        # По verdict
        by_verdict = {}
        for verdict in ["bullish", "bearish", "neutral"]:
            verdict_signals = [s for s in completed if s.verdict == verdict]
            if verdict_signals:
                verdict_success = sum(1 for s in verdict_signals if s.outcome == SignalOutcome.SUCCESS)
                by_verdict[verdict] = verdict_success / len(verdict_signals)
        
        # По типу сигнала
        by_signal_type = {}
        for signal_type in ["smart_money", "mining", "onchain", "social"]:
            type_signals = [s for s in completed if s.signal_type == signal_type]
            if type_signals:
                type_success = sum(1 for s in type_signals if s.outcome == SignalOutcome.SUCCESS)
                by_signal_type[signal_type] = type_success / len(type_signals)
        
        return {
            "overall": overall_accuracy,
            "by_verdict": by_verdict,
            "by_signal_type": by_signal_type,
            "total_signals": len(self.tracked_signals),
            "checked_signals": len(completed)
        }
    
    def get_recent_performance(self, days: int = 7) -> Dict:
        """
        Производительность за последние N дней
        
        Returns:
            {
                "period_start": datetime,
                "period_end": datetime,
                "signals_published": int,
                "signals_successful": int,
                "accuracy": float,
                "average_confidence": float
            }
        """
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [s for s in self.tracked_signals if s.published_at >= cutoff]
        
        if not recent:
            return {
                "period_start": cutoff,
                "period_end": datetime.utcnow(),
                "signals_published": 0,
                "signals_successful": 0,
                "accuracy": 0.0,
                "average_confidence": 0.0
            }
        
        completed = [s for s in recent if s.outcome != SignalOutcome.PENDING]
        successful = sum(1 for s in completed if s.outcome == SignalOutcome.SUCCESS)
        
        return {
            "period_start": cutoff,
            "period_end": datetime.utcnow(),
            "signals_published": len(recent),
            "signals_successful": successful,
            "accuracy": successful / len(completed) if completed else 0.0,
            "average_confidence": sum(s.confidence for s in recent) / len(recent)
        }
    
    def generate_report(self) -> str:
        """
        Генерирует текстовый отчёт производительности
        
        Returns:
            Форматированный отчёт
        """
        
        stats = self.get_accuracy_stats()
        recent = self.get_recent_performance(7)
        
        lines = [
            "=" * 80,
            "📊 PERFORMANCE REPORT",
            "=" * 80,
            "",
            f"📈 ОБЩАЯ СТАТИСТИКА",
            f"   Всего сигналов: {stats['total_signals']}",
            f"   Проверено: {stats['checked_signals']}",
            f"   Точность: {stats['overall']:.1%}",
            "",
            f"🎯 ПО ТИПАМ СИГНАЛОВ",
        ]
        
        for verdict, accuracy in stats['by_verdict'].items():
            lines.append(f"   {verdict.capitalize()}: {accuracy:.1%}")
        
        lines.extend([
            "",
            f"🔧 ПО ИСТОЧНИКАМ",
        ])
        
        for signal_type, accuracy in stats['by_signal_type'].items():
            lines.append(f"   {signal_type}: {accuracy:.1%}")
        
        lines.extend([
            "",
            f"📅 ПОСЛЕДНИЕ 7 ДНЕЙ",
            f"   Опубликовано: {recent['signals_published']} сигналов",
            f"   Успешных: {recent['signals_successful']}",
            f"   Точность: {recent['accuracy']:.1%}",
            f"   Средний confidence: {recent['average_confidence']:.0f}/100",
            "",
            "=" * 80
        ])
        
        return "\n".join(lines)
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _save_history(self):
        """Сохраняет историю в файл"""
        try:
            # Создаём директорию если нужно
            import os
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "signals": [s.to_dict() for s in self.tracked_signals[-self.history_size:]]
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️  Ошибка сохранения истории: {e}")
    
    def _load_history(self):
        """Загружает историю из файла"""
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
            
            self.tracked_signals = [
                SignalPerformance.from_dict(s) for s in data.get("signals", [])
            ]
            
            print(f"📂 [PERFORMANCE] Загружено {len(self.tracked_signals)} сигналов из истории")
        
        except FileNotFoundError:
            print("📂 [PERFORMANCE] Новая история")
            self.tracked_signals = []
        
        except Exception as e:
            print(f"⚠️  Ошибка загрузки истории: {e}")
            self.tracked_signals = []


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def check_all_pending() -> Dict:
    """
    Convenience function для проверки всех ожидающих сигналов
    
    Usage:
        from app.whales.performance_tracker import check_all_pending
        
        result = await check_all_pending()
        print(f"Точность: {result['success'] / result['checked']:.1%}")
    """
    
    async with PerformanceTracker() as tracker:
        return await tracker.check_pending_signals()


def get_performance_report() -> str:
    """
    Convenience function для получения отчёта
    
    Usage:
        from app.whales.performance_tracker import get_performance_report
        
        report = get_performance_report()
        print(report)
    """
    
    tracker = PerformanceTracker()
    return tracker.generate_report()


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        print("🧪 TESTING PERFORMANCE TRACKER\n")
        
        async with PerformanceTracker() as tracker:
            # Добавляем тестовые сигналы
            tracker.track_signal(
                signal_id="test_1",
                asset="BTC",
                chain="bitcoin",
                verdict="bullish",
                confidence=85,
                initial_price=110000,
                wallets_involved=["0x1234..."],
                signal_type="smart_money"
            )
            
            tracker.track_signal(
                signal_id="test_2",
                asset="ETH",
                chain="ethereum",
                verdict="bearish",
                confidence=72,
                initial_price=3870,
                wallets_involved=["0x5678..."],
                signal_type="onchain"
            )
            
            # Проверяем
            result = await tracker.check_pending_signals()
            
            # Отчёт
            print("\n" + tracker.generate_report())
        
        print("\n✅ Тестирование завершено!")
    
    asyncio.run(main())