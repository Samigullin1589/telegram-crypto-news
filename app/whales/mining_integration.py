# app/whales/mining_integration.py
"""
MINING INTEGRATION MODULE v1.0

Интеграция майнинг-данных с системой самообучения.

Функции:
- Преобразование mining событий в формат learning system
- Расчёт performance mining сигналов
- Оптимизация весов mining индикаторов
- Обнаружение паттернов в mining данных
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from app import settings


@dataclass
class MiningSignalData:
    """Данные mining сигнала для tracking"""
    asset: str
    chain: str
    
    # Mining метрики
    difficulty_change: float
    hashrate_change: float
    block_time_change: float
    miner_revenue_change: float
    
    # Verdict
    verdict: str  # bullish/bearish/neutral
    confidence: int
    
    # Price
    price_at_signal: float
    
    # Timing
    timestamp: datetime
    
    def to_tracker_format(self) -> Dict:
        """Конвертация в формат PerformanceTracker"""
        return {
            "signal_id": f"mining_{self.asset}_{int(self.timestamp.timestamp())}",
            "asset": self.asset,
            "chain": self.chain,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "initial_price": self.price_at_signal,
            "wallets_involved": [],
            "signal_type": "mining",
            "mining_data": {
                "difficulty_change": self.difficulty_change,
                "hashrate_change": self.hashrate_change,
                "block_time_change": self.block_time_change,
                "miner_revenue_change": self.miner_revenue_change
            }
        }


class MiningIntegration:
    """
    Интеграция майнинга с системой самообучения
    """
    
    def __init__(self):
        # Веса индикаторов (будут оптимизироваться)
        self.indicator_weights = {
            "difficulty": 0.30,
            "hashrate": 0.35,
            "block_time": 0.20,
            "miner_revenue": 0.15
        }
        
        # История для обучения
        self.mining_history: List[Dict] = []
    
    # ========================================================================
    # SIGNAL CONVERSION
    # ========================================================================
    
    def convert_mining_event(self, mining_event: Dict) -> Optional[MiningSignalData]:
        """
        Конвертирует событие из mining_tracker в формат для learning system
        
        Args:
            mining_event: Событие от mining_tracker {
                "asset": "BTC",
                "difficulty_change": 5.2,
                "hashrate_change": 3.8,
                ...
            }
        
        Returns:
            MiningSignalData или None если недостаточно данных
        """
        
        # Проверяем обязательные поля
        required = ["asset", "difficulty_change", "hashrate_change", "price"]
        if not all(k in mining_event for k in required):
            return None
        
        # Извлекаем данные
        asset = mining_event["asset"]
        diff_change = mining_event["difficulty_change"]
        hash_change = mining_event["hashrate_change"]
        block_time_change = mining_event.get("block_time_change", 0)
        revenue_change = mining_event.get("miner_revenue_change", 0)
        price = mining_event["price"]
        
        # Определяем chain
        chain = self._get_chain_for_asset(asset)
        
        # Рассчитываем verdict и confidence
        verdict, confidence = self._calculate_mining_verdict(
            diff_change, hash_change, block_time_change, revenue_change
        )
        
        # Создаём объект
        signal = MiningSignalData(
            asset=asset,
            chain=chain,
            difficulty_change=diff_change,
            hashrate_change=hash_change,
            block_time_change=block_time_change,
            miner_revenue_change=revenue_change,
            verdict=verdict,
            confidence=confidence,
            price_at_signal=price,
            timestamp=datetime.utcnow()
        )
        
        return signal
    
    def _get_chain_for_asset(self, asset: str) -> str:
        """Определяет blockchain для актива"""
        chain_mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "LTC": "litecoin",
            "BCH": "bitcoin-cash",
            "DOGE": "dogecoin",
            "ZEC": "zcash",
            "DASH": "dash"
        }
        return chain_mapping.get(asset, asset.lower())
    
    def _calculate_mining_verdict(
        self,
        diff_change: float,
        hash_change: float,
        block_time_change: float,
        revenue_change: float
    ) -> Tuple[str, int]:
        """
        Рассчитывает verdict и confidence на основе mining метрик
        
        Args:
            diff_change: Изменение сложности (%)
            hash_change: Изменение хешрейта (%)
            block_time_change: Изменение времени блока (%)
            revenue_change: Изменение дохода майнеров (%)
        
        Returns:
            (verdict, confidence)
        """
        
        # Нормализуем метрики (-1 до +1)
        def normalize(value, threshold=10):
            return max(-1, min(1, value / threshold))
        
        norm_diff = normalize(diff_change)
        norm_hash = normalize(hash_change)
        norm_block_time = normalize(block_time_change)
        norm_revenue = normalize(revenue_change)
        
        # Взвешенная сумма с весами индикаторов
        weighted_score = (
            norm_diff * self.indicator_weights["difficulty"] +
            norm_hash * self.indicator_weights["hashrate"] +
            norm_block_time * self.indicator_weights["block_time"] +
            norm_revenue * self.indicator_weights["miner_revenue"]
        )
        
        # Определяем verdict
        if weighted_score > 0.15:
            verdict = "bullish"
        elif weighted_score < -0.15:
            verdict = "bearish"
        else:
            verdict = "neutral"
        
        # Рассчитываем confidence (0-100)
        # Чем сильнее сигнал и чем больше согласованность - тем выше confidence
        
        # Сила сигнала
        strength = abs(weighted_score)
        
        # Согласованность (все ли индикаторы в одну сторону?)
        indicators = [norm_diff, norm_hash, norm_block_time, norm_revenue]
        sign = 1 if weighted_score > 0 else -1
        agreement = sum(1 for ind in indicators if ind * sign > 0) / len(indicators)
        
        # Финальный confidence
        base_confidence = int(strength * 100)
        agreement_bonus = int(agreement * 20)
        
        confidence = min(100, base_confidence + agreement_bonus)
        confidence = max(20, confidence)  # Минимум 20
        
        return verdict, confidence
    
    # ========================================================================
    # PERFORMANCE ANALYSIS
    # ========================================================================
    
    def analyze_mining_performance(self, performance_data: List[Dict]) -> Dict:
        """
        Анализирует производительность mining сигналов
        
        Args:
            performance_data: Данные от PerformanceTracker с mining сигналами
        
        Returns:
            {
                "accuracy_overall": float,
                "accuracy_by_indicator": Dict,
                "best_thresholds": Dict,
                "patterns": List[Dict]
            }
        """
        
        # Фильтруем только mining сигналы
        mining_signals = [
            p for p in performance_data 
            if p.get("signal_type") == "mining" and p.get("mining_data")
        ]
        
        if len(mining_signals) < 10:
            return {
                "accuracy_overall": 0.0,
                "accuracy_by_indicator": {},
                "best_thresholds": {},
                "patterns": [],
                "insufficient_data": True
            }
        
        # ====================================================================
        # OVERALL ACCURACY
        # ====================================================================
        
        successful = sum(1 for s in mining_signals if s.get("outcome") == "success")
        accuracy_overall = successful / len(mining_signals)
        
        # ====================================================================
        # ACCURACY BY INDICATOR
        # ====================================================================
        
        # Группируем по силе каждого индикатора
        by_difficulty = self._group_by_indicator_strength(
            mining_signals, "difficulty_change"
        )
        
        by_hashrate = self._group_by_indicator_strength(
            mining_signals, "hashrate_change"
        )
        
        accuracy_by_indicator = {
            "difficulty": self._calculate_grouped_accuracy(by_difficulty),
            "hashrate": self._calculate_grouped_accuracy(by_hashrate)
        }
        
        # ====================================================================
        # BEST THRESHOLDS
        # ====================================================================
        
        # Находим оптимальные пороги для каждого индикатора
        best_thresholds = {}
        
        for indicator in ["difficulty_change", "hashrate_change"]:
            best_threshold = self._find_optimal_threshold(mining_signals, indicator)
            best_thresholds[indicator] = best_threshold
        
        # ====================================================================
        # PATTERNS
        # ====================================================================
        
        patterns = self._detect_mining_patterns(mining_signals)
        
        return {
            "accuracy_overall": accuracy_overall,
            "accuracy_by_indicator": accuracy_by_indicator,
            "best_thresholds": best_thresholds,
            "patterns": patterns,
            "total_signals": len(mining_signals),
            "insufficient_data": False
        }
    
    def _group_by_indicator_strength(
        self, 
        signals: List[Dict], 
        indicator: str
    ) -> Dict[str, List[bool]]:
        """
        Группирует сигналы по силе индикатора
        
        Returns:
            {"weak": [True, False, ...], "medium": [...], "strong": [...]}
        """
        
        groups = {
            "weak": [],      # 0-3%
            "medium": [],    # 3-7%
            "strong": []     # >7%
        }
        
        for signal in signals:
            mining_data = signal.get("mining_data", {})
            value = abs(mining_data.get(indicator, 0))
            outcome = signal.get("outcome") == "success"
            
            if value < 3:
                groups["weak"].append(outcome)
            elif value < 7:
                groups["medium"].append(outcome)
            else:
                groups["strong"].append(outcome)
        
        return groups
    
    def _calculate_grouped_accuracy(self, groups: Dict[str, List[bool]]) -> Dict:
        """Рассчитывает accuracy для каждой группы"""
        
        result = {}
        
        for strength, outcomes in groups.items():
            if outcomes:
                accuracy = sum(outcomes) / len(outcomes)
                result[strength] = {
                    "accuracy": accuracy,
                    "count": len(outcomes)
                }
        
        return result
    
    def _find_optimal_threshold(
        self, 
        signals: List[Dict], 
        indicator: str
    ) -> float:
        """
        Находит оптимальный порог для индикатора
        
        Возвращает порог, при котором accuracy максимальна
        """
        
        # Пробуем разные пороги от 2% до 15%
        thresholds = [2, 3, 4, 5, 6, 7, 8, 10, 12, 15]
        
        best_threshold = 5.0
        best_accuracy = 0.0
        
        for threshold in thresholds:
            # Сигналы выше порога
            above = [
                s for s in signals
                if abs(s.get("mining_data", {}).get(indicator, 0)) >= threshold
            ]
            
            if len(above) < 5:  # Минимум 5 сигналов
                continue
            
            # Accuracy
            successful = sum(1 for s in above if s.get("outcome") == "success")
            accuracy = successful / len(above)
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold
        
        return best_threshold
    
    def _detect_mining_patterns(self, signals: List[Dict]) -> List[Dict]:
        """
        Обнаруживает паттерны в mining данных
        
        Например:
        - "Высокий рост хешрейта + низкий рост сложности = bullish с высокой точностью"
        - "Падение revenue + рост difficulty = bearish с высокой точностью"
        """
        
        patterns = []
        
        # ПАТТЕРН 1: Hashrate растёт быстрее difficulty
        hash_above_diff = [
            s for s in signals
            if (s.get("mining_data", {}).get("hashrate_change", 0) > 
                s.get("mining_data", {}).get("difficulty_change", 0) + 2)
        ]
        
        if len(hash_above_diff) >= 5:
            successful = sum(1 for s in hash_above_diff if s.get("outcome") == "success")
            accuracy = successful / len(hash_above_diff)
            
            if accuracy > 0.70:
                patterns.append({
                    "name": "hashrate_above_difficulty",
                    "description": "Хешрейт растёт быстрее сложности",
                    "accuracy": accuracy,
                    "sample_size": len(hash_above_diff),
                    "expected_verdict": "bullish"
                })
        
        # ПАТТЕРН 2: Падение revenue при росте difficulty
        revenue_drop = [
            s for s in signals
            if (s.get("mining_data", {}).get("miner_revenue_change", 0) < -3 and
                s.get("mining_data", {}).get("difficulty_change", 0) > 2)
        ]
        
        if len(revenue_drop) >= 5:
            successful = sum(1 for s in revenue_drop if s.get("outcome") == "success")
            accuracy = successful / len(revenue_drop)
            
            if accuracy > 0.70:
                patterns.append({
                    "name": "revenue_drop_difficulty_rise",
                    "description": "Падение дохода при росте сложности",
                    "accuracy": accuracy,
                    "sample_size": len(revenue_drop),
                    "expected_verdict": "bearish"
                })
        
        return patterns
    
    # ========================================================================
    # WEIGHT OPTIMIZATION
    # ========================================================================
    
    def optimize_indicator_weights(self, performance_data: List[Dict]) -> Dict[str, float]:
        """
        Оптимизирует веса индикаторов на основе их реальной производительности
        
        Args:
            performance_data: История mining сигналов с результатами
        
        Returns:
            Обновлённые веса
        """
        
        mining_signals = [
            p for p in performance_data 
            if p.get("signal_type") == "mining" and p.get("mining_data")
        ]
        
        if len(mining_signals) < 20:
            print("⚠️  [MINING] Недостаточно данных для оптимизации весов")
            return self.indicator_weights
        
        print(f"\n{'=' * 80}")
        print(f"⛏️  MINING INTEGRATION - Оптимизация весов индикаторов")
        print(f"{'=' * 80}")
        
        # Рассчитываем корреляцию каждого индикатора с успехом
        indicators = ["difficulty_change", "hashrate_change", "block_time_change", "miner_revenue_change"]
        correlations = {}
        
        for indicator in indicators:
            # Извлекаем значения индикатора и результаты
            values = []
            outcomes = []
            
            for signal in mining_signals:
                mining_data = signal.get("mining_data", {})
                value = mining_data.get(indicator, 0)
                outcome = 1 if signal.get("outcome") == "success" else 0
                
                values.append(value)
                outcomes.append(outcome)
            
            # Простая корреляция (можно улучшить через numpy)
            if values and outcomes:
                mean_value = statistics.mean(values)
                mean_outcome = statistics.mean(outcomes)
                
                covariance = sum(
                    (v - mean_value) * (o - mean_outcome) 
                    for v, o in zip(values, outcomes)
                ) / len(values)
                
                std_value = statistics.stdev(values) if len(values) > 1 else 1
                std_outcome = statistics.stdev(outcomes) if len(outcomes) > 1 else 1
                
                correlation = covariance / (std_value * std_outcome) if std_value > 0 and std_outcome > 0 else 0
                correlations[indicator] = abs(correlation)
        
        # Нормализуем корреляции в веса
        total_correlation = sum(correlations.values())
        
        if total_correlation > 0:
            new_weights = {
                "difficulty": correlations.get("difficulty_change", 0.25) / total_correlation,
                "hashrate": correlations.get("hashrate_change", 0.25) / total_correlation,
                "block_time": correlations.get("block_time_change", 0.25) / total_correlation,
                "miner_revenue": correlations.get("miner_revenue_change", 0.25) / total_correlation
            }
            
            # Смешиваем со старыми весами (не меняем слишком резко)
            learning_rate = 0.3
            
            final_weights = {}
            for key in ["difficulty", "hashrate", "block_time", "miner_revenue"]:
                old = self.indicator_weights[key]
                new = new_weights[key]
                final_weights[key] = old * (1 - learning_rate) + new * learning_rate
            
            # Обновляем
            old_weights = self.indicator_weights.copy()
            self.indicator_weights = final_weights
            
            print(f"\n✅ Веса индикаторов обновлены:")
            for indicator in ["difficulty", "hashrate", "block_time", "miner_revenue"]:
                old = old_weights[indicator]
                new = final_weights[indicator]
                change = new - old
                arrow = "↑" if change > 0 else "↓" if change < 0 else "="
                print(f"   {indicator}: {old:.2%} → {new:.2%} {arrow} ({change:+.2%})")
            
            print(f"{'=' * 80}\n")
            
            return final_weights
        
        return self.indicator_weights
    
    # ========================================================================
    # REPORTING
    # ========================================================================
    
    def generate_mining_report(self, performance_data: List[Dict]) -> str:
        """Генерирует отчёт по mining производительности"""
        
        analysis = self.analyze_mining_performance(performance_data)
        
        if analysis.get("insufficient_data"):
            return "⛏️  MINING REPORT: Недостаточно данных (минимум 10 сигналов)"
        
        lines = [
            "=" * 80,
            "⛏️  MINING PERFORMANCE REPORT",
            "=" * 80,
            "",
            f"📊 ОБЩАЯ СТАТИСТИКА",
            f"   Всего mining сигналов: {analysis['total_signals']}",
            f"   Общая точность: {analysis['accuracy_overall']:.1%}",
            "",
            f"📈 ТОЧНОСТЬ ПО ИНДИКАТОРАМ"
        ]
        
        for indicator, data in analysis["accuracy_by_indicator"].items():
            lines.append(f"\n   {indicator.upper()}:")
            for strength, stats in data.items():
                lines.append(f"     {strength}: {stats['accuracy']:.1%} (n={stats['count']})")
        
        lines.extend([
            "",
            f"⚙️  ОПТИМАЛЬНЫЕ ПОРОГИ"
        ])
        
        for indicator, threshold in analysis["best_thresholds"].items():
            lines.append(f"   {indicator}: {threshold}%")
        
        if analysis["patterns"]:
            lines.extend([
                "",
                f"🔍 ОБНАРУЖЕННЫЕ ПАТТЕРНЫ: {len(analysis['patterns'])}"
            ])
            
            for pattern in analysis["patterns"]:
                lines.append(f"   • {pattern['description']}: {pattern['accuracy']:.1%} (n={pattern['sample_size']})")
        
        lines.extend([
            "",
            f"⚖️  ТЕКУЩИЕ ВЕСА ИНДИКАТОРОВ"
        ])
        
        for indicator, weight in self.indicator_weights.items():
            lines.append(f"   {indicator}: {weight:.1%}")
        
        lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(lines)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def convert_mining_to_performance_format(mining_event: Dict) -> Optional[Dict]:
    """
    Convenience function для быстрой конвертации
    
    Usage:
        from app.whales.mining_integration import convert_mining_to_performance_format
        
        signal_data = convert_mining_to_performance_format(mining_event)
        if signal_data:
            tracker.track_signal(**signal_data)
    """
    
    integration = MiningIntegration()
    signal = integration.convert_mining_event(mining_event)
    
    if signal:
        return signal.to_tracker_format()
    
    return None


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    def main():
        print("🧪 TESTING MINING INTEGRATION\n")
        
        integration = MiningIntegration()
        
        # Тестовое mining событие
        test_event = {
            "asset": "BTC",
            "difficulty_change": 5.2,
            "hashrate_change": 7.8,
            "block_time_change": -2.1,
            "miner_revenue_change": 3.5,
            "price": 68500
        }
        
        print("1. Конвертация mining события...")
        signal = integration.convert_mining_event(test_event)
        
        if signal:
            print(f"   ✅ Создан сигнал: {signal.asset} {signal.verdict} (confidence: {signal.confidence})")
            print(f"   Формат для tracker:")
            import json
            print(json.dumps(signal.to_tracker_format(), indent=2, default=str))
        
        print("\n2. Тест расчёта verdict...")
        verdict, confidence = integration._calculate_mining_verdict(5.2, 7.8, -2.1, 3.5)
        print(f"   Verdict: {verdict}, Confidence: {confidence}")
        
        print("\n✅ Тестирование завершено!")
    
    main()