"""
RISK SCORING MODULE

Оценивает риск каждого сигнала по множеству факторов:
- Volatility актива
- Liquidity на DEX
- Market cap
- Wallet history
- Pattern reliability
- Market conditions

Возвращает risk score 0-100 (чем выше - тем рискованнее)
"""

import statistics
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class RiskFactors:
    """Факторы риска"""
    volatility: float = 0.0
    liquidity: float = 0.0
    market_cap: float = 0.0
    wallet_reliability: float = 0.0
    pattern_confidence: float = 0.0
    market_conditions: float = 0.0
    sentiment: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "volatility": self.volatility,
            "liquidity": self.liquidity,
            "market_cap": self.market_cap,
            "wallet_reliability": self.wallet_reliability,
            "pattern_confidence": self.pattern_confidence,
            "market_conditions": self.market_conditions,
            "sentiment": self.sentiment
        }


class RiskScorer:
    """
    Оценщик рисков для крипто-сигналов
    
    Комбинирует несколько факторов риска в единый score
    """
    
    def __init__(self):
        self.weights = {
            "volatility": 0.20,
            "liquidity": 0.20,
            "market_cap": 0.15,
            "wallet_reliability": 0.20,
            "pattern_confidence": 0.15,
            "market_conditions": 0.05,
            "sentiment": 0.05
        }
        
        self.risk_levels = {
            "low": (0, 30),
            "medium": (30, 60),
            "high": (60, 85),
            "extreme": (85, 100)
        }
        
        # История волатильности для market conditions
        self.volatility_history: Dict[str, List[float]] = {}
        self.price_history: Dict[str, List[tuple]] = {}
    
    # ========================================================================
    # MAIN SCORING
    # ========================================================================
    
    def calculate_risk_score(
        self,
        asset: str,
        signal_data: Dict,
        wallet_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """
        Рассчитывает комплексный risk score для сигнала
        
        Args:
            asset: Название актива
            signal_data: Данные сигнала
            wallet_data: Данные кошелька
            market_data: Рыночные данные
        
        Returns:
            Полный отчёт о рисках
        """
        
        factors = self._calculate_risk_factors(
            asset, signal_data, wallet_data, market_data
        )
        
        risk_score = (
            factors.volatility * self.weights["volatility"] +
            factors.liquidity * self.weights["liquidity"] +
            factors.market_cap * self.weights["market_cap"] +
            factors.wallet_reliability * self.weights["wallet_reliability"] +
            factors.pattern_confidence * self.weights["pattern_confidence"] +
            factors.market_conditions * self.weights["market_conditions"] +
            factors.sentiment * self.weights["sentiment"]
        ) * 100
        
        risk_score = int(risk_score)
        
        risk_level = self._get_risk_level(risk_score)
        
        warnings = self._generate_warnings(factors, signal_data, wallet_data, market_data)
        
        recommendation = self._get_recommendation(risk_score, factors)
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": factors.to_dict(),
            "warnings": warnings,
            "recommendation": recommendation,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # FACTOR CALCULATION
    # ========================================================================
    
    def _calculate_risk_factors(
        self,
        asset: str,
        signal_data: Dict,
        wallet_data: Optional[Dict],
        market_data: Optional[Dict]
    ) -> RiskFactors:
        """Рассчитывает все факторы риска (0-1 для каждого)"""
        
        factors = RiskFactors()
        
        # VOLATILITY RISK
        if market_data and "volatility" in market_data:
            volatility = market_data["volatility"]
            factors.volatility = min(1.0, volatility / 50)
        else:
            factors.volatility = 0.5
        
        # LIQUIDITY RISK
        if market_data and "volume_24h" in market_data:
            volume_24h = market_data["volume_24h"]
            
            if volume_24h > 10_000_000:
                liquidity_risk = 0.1
            elif volume_24h > 1_000_000:
                liquidity_risk = 0.3
            elif volume_24h > 100_000:
                liquidity_risk = 0.6
            else:
                liquidity_risk = 0.9
            
            factors.liquidity = liquidity_risk
        else:
            factors.liquidity = 0.5
        
        # MARKET CAP RISK
        if market_data and "market_cap" in market_data:
            market_cap = market_data["market_cap"]
            
            if market_cap > 1_000_000_000:
                mc_risk = 0.1
            elif market_cap > 100_000_000:
                mc_risk = 0.3
            elif market_cap > 10_000_000:
                mc_risk = 0.6
            else:
                mc_risk = 0.9
            
            factors.market_cap = mc_risk
        else:
            factors.market_cap = 0.5
        
        # WALLET RELIABILITY
        if wallet_data:
            score = wallet_data.get("score", 50)
            roi_30d = wallet_data.get("roi_30d", 0)
            win_rate = wallet_data.get("win_rate", 0.5)
            
            score_risk = 1.0 - (score / 100)
            roi_risk = 0.0 if roi_30d > 0.5 else (0.5 if roi_30d > 0 else 1.0)
            winrate_risk = 1.0 - win_rate
            
            factors.wallet_reliability = (score_risk * 0.5 + roi_risk * 0.3 + winrate_risk * 0.2)
        else:
            factors.wallet_reliability = 0.5
        
        # PATTERN CONFIDENCE
        confidence = signal_data.get("confidence", 50)
        factors.pattern_confidence = 1.0 - (confidence / 100)
        
        # MARKET CONDITIONS
        market_condition_risk = self._calculate_market_conditions(asset, market_data)
        factors.market_conditions = market_condition_risk
        
        # SENTIMENT
        sentiment_risk = self._calculate_sentiment_risk(asset, signal_data)
        factors.sentiment = sentiment_risk
        
        return factors
    
    def _calculate_market_conditions(self, asset: str, market_data: Optional[Dict]) -> float:
        """
        Рассчитывает риск на основе текущих рыночных условий
        
        Returns:
            0.0-1.0 (0 = безопасно, 1 = опасно)
        """
        
        if not market_data:
            return 0.3
        
        risk_score = 0.0
        
        # Проверяем тренд
        price_change_24h = market_data.get("price_change_24h", 0)
        price_change_7d = market_data.get("price_change_7d", 0)
        
        # Сильное падение = высокий риск
        if price_change_24h < -10:
            risk_score += 0.3
        elif price_change_24h < -5:
            risk_score += 0.15
        
        if price_change_7d < -20:
            risk_score += 0.3
        elif price_change_7d < -10:
            risk_score += 0.15
        
        # Экстремальный рост = риск коррекции
        if price_change_24h > 30:
            risk_score += 0.2
        elif price_change_24h > 20:
            risk_score += 0.1
        
        # Проверяем объёмы
        volume_24h = market_data.get("volume_24h", 0)
        market_cap = market_data.get("market_cap", 1)
        
        if market_cap > 0:
            volume_to_mc = volume_24h / market_cap
            
            # Аномально низкие объёмы = риск
            if volume_to_mc < 0.01:
                risk_score += 0.2
            # Аномально высокие объёмы = возможная манипуляция
            elif volume_to_mc > 1.0:
                risk_score += 0.2
        
        return min(1.0, risk_score)
    
    def _calculate_sentiment_risk(self, asset: str, signal_data: Dict) -> float:
        """
        Рассчитывает риск на основе sentiment
        
        Returns:
            0.0-1.0
        """
        
        sentiment_data = signal_data.get("sentiment")
        
        if not sentiment_data:
            return 0.3
        
        sentiment_score = sentiment_data.get("sentiment", 0)
        
        # Экстремально позитивный или негативный sentiment = риск
        # (может быть FOMO или паника)
        abs_sentiment = abs(sentiment_score)
        
        if abs_sentiment > 0.8:
            return 0.7
        elif abs_sentiment > 0.6:
            return 0.5
        else:
            return 0.2
    
    # ========================================================================
    # RISK CLASSIFICATION
    # ========================================================================
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Определяет уровень риска"""
        for level, (min_score, max_score) in self.risk_levels.items():
            if min_score <= risk_score < max_score:
                return level
        return "extreme"
    
    def _generate_warnings(
        self,
        factors: RiskFactors,
        signal_data: Dict,
        wallet_data: Optional[Dict],
        market_data: Optional[Dict]
    ) -> List[str]:
        """Генерирует предупреждения на основе факторов риска"""
        
        warnings = []
        
        if factors.volatility > 0.7:
            warnings.append("⚠️ Высокая волатильность актива")
        
        if factors.liquidity > 0.7:
            warnings.append("⚠️ Низкая ликвидность - возможны проблемы с выходом")
        
        if factors.market_cap > 0.7:
            warnings.append("⚠️ Низкий market cap - высокий риск манипуляций")
        
        if factors.wallet_reliability > 0.7:
            warnings.append("⚠️ Ненадёжный кошелёк - плохая история торговли")
        
        if factors.pattern_confidence > 0.7:
            warnings.append("⚠️ Низкий confidence сигнала")
        
        if factors.market_conditions > 0.6:
            warnings.append("⚠️ Неблагоприятные рыночные условия")
        
        if factors.sentiment > 0.6:
            warnings.append("⚠️ Экстремальный sentiment - возможна коррекция")
        
        # Размер сделки относительно ликвидности
        if market_data and signal_data:
            volume_24h = market_data.get("volume_24h", 0)
            size_usd = signal_data.get("size_usd", 0)
            
            if volume_24h > 0 and size_usd > volume_24h * 0.05:
                warnings.append("⚠️ Размер сделки >5% от дневного объёма")
            
            if volume_24h > 0 and size_usd > volume_24h * 0.10:
                warnings.append("🚨 КРИТИЧНО: Размер сделки >10% от дневного объёма")
        
        # Проверка на pump & dump паттерн
        if market_data:
            price_change_1h = market_data.get("price_change_1h", 0)
            volume_change_1h = market_data.get("volume_change_1h", 0)
            
            if price_change_1h > 20 and volume_change_1h > 500:
                warnings.append("🚨 КРИТИЧНО: Возможный pump & dump паттерн")
        
        return warnings
    
    def _get_recommendation(self, risk_score: int, factors: RiskFactors) -> str:
        """Генерирует рекомендацию"""
        
        if risk_score < 30:
            return "✅ Низкий риск. Можно входить с обычной позицией."
        
        elif risk_score < 60:
            base_rec = "⚠️ Средний риск. Рекомендуется уменьшить размер позиции."
            
            # Добавляем специфичные советы
            if factors.liquidity > 0.5:
                base_rec += " Особое внимание на ликвидность при выходе."
            
            if factors.volatility > 0.5:
                base_rec += " Установите широкий stop-loss из-за волатильности."
            
            return base_rec
        
        elif risk_score < 85:
            return "🚨 Высокий риск. Только для опытных трейдеров с малой позицией. Используйте строгий risk management."
        
        else:
            return "🔴 ЭКСТРЕМАЛЬНЫЙ РИСК. Настоятельно не рекомендуется входить. Вероятность потери капитала очень высока."
    
    # ========================================================================
    # BATCH SCORING
    # ========================================================================
    
    def score_multiple_signals(self, signals: List[Dict]) -> List[Dict]:
        """
        Оценивает риск для нескольких сигналов
        
        Args:
            signals: Список сигналов с данными
        
        Returns:
            Список сигналов с добавленным risk_score
        """
        
        results = []
        
        for signal in signals:
            risk_result = self.calculate_risk_score(
                asset=signal.get("asset", "UNKNOWN"),
                signal_data=signal,
                wallet_data=signal.get("wallet_data"),
                market_data=signal.get("market_data")
            )
            
            signal_with_risk = signal.copy()
            signal_with_risk["risk_score"] = risk_result["risk_score"]
            signal_with_risk["risk_level"] = risk_result["risk_level"]
            signal_with_risk["risk_warnings"] = risk_result["warnings"]
            signal_with_risk["risk_recommendation"] = risk_result["recommendation"]
            
            results.append(signal_with_risk)
        
        # Сортируем по риску (от низкого к высокому)
        results.sort(key=lambda x: x["risk_score"])
        
        return results
    
    # ========================================================================
    # OPTIMIZATION
    # ========================================================================
    
    def optimize_weights(self, historical_signals: List[Dict]):
        """
        Оптимизирует веса факторов на основе исторических данных
        
        Использует простой метод корреляции между факторами и результатами
        """
        
        if len(historical_signals) < 50:
            print("⚠️ Недостаточно данных для оптимизации (нужно минимум 50 сигналов)")
            return
        
        # Собираем данные
        factor_values = {key: [] for key in self.weights.keys()}
        outcomes = []  # 1 для успешных, 0 для неудачных
        
        for signal in historical_signals:
            if "risk_factors" not in signal or "outcome" not in signal:
                continue
            
            factors = signal["risk_factors"]
            outcome = 1 if signal["outcome"] == "success" else 0
            
            for key in self.weights.keys():
                factor_values[key].append(factors.get(key, 0.5))
            
            outcomes.append(outcome)
        
        if len(outcomes) < 50:
            print("⚠️ Недостаточно валидных данных")
            return
        
        # Рассчитываем корреляцию каждого фактора с исходом
        correlations = {}
        
        for key, values in factor_values.items():
            if len(values) != len(outcomes):
                continue
            
            # Простая корреляция Пирсона
            mean_factor = statistics.mean(values)
            mean_outcome = statistics.mean(outcomes)
            
            numerator = sum((v - mean_factor) * (o - mean_outcome) 
                          for v, o in zip(values, outcomes))
            
            denominator_factor = sum((v - mean_factor) ** 2 for v in values) ** 0.5
            denominator_outcome = sum((o - mean_outcome) ** 2 for o in outcomes) ** 0.5
            
            if denominator_factor > 0 and denominator_outcome > 0:
                correlation = numerator / (denominator_factor * denominator_outcome)
                correlations[key] = abs(correlation)  # Используем абсолютное значение
            else:
                correlations[key] = 0.0
        
        # Нормализуем корреляции в веса
        total_correlation = sum(correlations.values())
        
        if total_correlation > 0:
            new_weights = {
                key: corr / total_correlation 
                for key, corr in correlations.items()
            }
            
            print("🎯 Оптимизированные веса:")
            for key, old_weight in self.weights.items():
                new_weight = new_weights.get(key, old_weight)
                change = new_weight - old_weight
                print(f"   {key}: {old_weight:.3f} -> {new_weight:.3f} ({change:+.3f})")
            
            self.weights = new_weights


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def calculate_signal_risk(signal_data: Dict) -> Dict:
    """
    Quick risk calculation
    
    Usage:
        from app.analytics.risk_scoring import calculate_signal_risk
        
        signal = {
            "asset": "SHIB",
            "confidence": 45,
            "size_usd": 50000,
            "wallet_data": {"score": 35, "roi_30d": -0.15}
        }
        
        risk = calculate_signal_risk(signal)
        print(f"Risk: {risk['risk_score']}/100 ({risk['risk_level']})")
    """
    
    scorer = RiskScorer()
    
    return scorer.calculate_risk_score(
        asset=signal_data.get("asset", "UNKNOWN"),
        signal_data=signal_data,
        wallet_data=signal_data.get("wallet_data"),
        market_data=signal_data.get("market_data")
    )


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 TESTING RISK SCORER\n")
    
    scorer = RiskScorer()
    
    test_signals = [
        {
            "name": "Low Risk Signal",
            "asset": "BTC",
            "confidence": 85,
            "size_usd": 100000,
            "wallet_data": {
                "score": 85,
                "roi_30d": 0.85,
                "win_rate": 0.75
            },
            "market_data": {
                "volatility": 15,
                "volume_24h": 50_000_000_000,
                "market_cap": 800_000_000_000,
                "price_change_24h": 2.5,
                "price_change_7d": 8.3
            }
        },
        {
            "name": "High Risk Signal",
            "asset": "SHIB",
            "confidence": 35,
            "size_usd": 10000,
            "wallet_data": {
                "score": 25,
                "roi_30d": -0.25,
                "win_rate": 0.35
            },
            "market_data": {
                "volatility": 65,
                "volume_24h": 50_000,
                "market_cap": 5_000_000,
                "price_change_24h": -15.2,
                "price_change_7d": -28.5
            }
        },
        {
            "name": "Medium Risk Signal",
            "asset": "ETH",
            "confidence": 60,
            "size_usd": 50000,
            "wallet_data": {
                "score": 55,
                "roi_30d": 0.15,
                "win_rate": 0.58
            },
            "market_data": {
                "volatility": 30,
                "volume_24h": 10_000_000_000,
                "market_cap": 200_000_000_000,
                "price_change_24h": 3.2,
                "price_change_7d": 5.8
            }
        }
    ]
    
    print("=" * 80)
    print("RISK ANALYSIS")
    print("=" * 80)
    
    for signal in test_signals:
        print(f"\n📊 {signal['name']} - {signal['asset']}")
        print("-" * 80)
        
        result = scorer.calculate_risk_score(
            asset=signal["asset"],
            signal_data=signal,
            wallet_data=signal.get("wallet_data"),
            market_data=signal.get("market_data")
        )
        
        print(f"Risk Score: {result['risk_score']}/100")
        print(f"Risk Level: {result['risk_level'].upper()}")
        print(f"\nFactors:")
        for factor, value in result['factors'].items():
            bar = "█" * int(value * 20)
            print(f"  {factor:20s}: {bar:20s} {value:.2f}")
        
        if result['warnings']:
            print(f"\nWarnings:")
            for warning in result['warnings']:
                print(f"  {warning}")
        
        print(f"\n{result['recommendation']}")
    
    print("\n" + "=" * 80)
    print("✅ Testing complete!")