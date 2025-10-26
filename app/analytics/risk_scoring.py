# app/analytics/risk_scoring.py
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
    volatility: float = 0.0  # 0-1
    liquidity: float = 0.0  # 0-1
    market_cap: float = 0.0  # 0-1
    wallet_reliability: float = 0.0  # 0-1
    pattern_confidence: float = 0.0  # 0-1
    market_conditions: float = 0.0  # 0-1
    sentiment: float = 0.0  # 0-1
    
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
        # Веса факторов (сумма = 1.0)
        self.weights = {
            "volatility": 0.20,
            "liquidity": 0.20,
            "market_cap": 0.15,
            "wallet_reliability": 0.20,
            "pattern_confidence": 0.15,
            "market_conditions": 0.05,
            "sentiment": 0.05
        }
        
        # Пороги для классификации
        self.risk_levels = {
            "low": (0, 30),
            "medium": (30, 60),
            "high": (60, 85),
            "extreme": (85, 100)
        }
    
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
            signal_data: Данные сигнала {
                "confidence": int,
                "size_usd": float,
                "dex": str,
                ...
            }
            wallet_data: Данные кошелька {
                "score": int,
                "roi_30d": float,
                "win_rate": float,
                ...
            }
            market_data: Рыночные данные {
                "price": float,
                "volume_24h": float,
                "market_cap": float,
                "volatility": float,
                ...
            }
        
        Returns:
            {
                "risk_score": int (0-100),
                "risk_level": str,
                "factors": RiskFactors,
                "warnings": List[str],
                "recommendation": str
            }
        """
        
        # Рассчитываем факторы риска
        factors = self._calculate_risk_factors(
            asset, signal_data, wallet_data, market_data
        )
        
        # Взвешенная сумма
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
        
        # Определяем уровень риска
        risk_level = self._get_risk_level(risk_score)
        
        # Генерируем предупреждения
        warnings = self._generate_warnings(factors, signal_data, wallet_data, market_data)
        
        # Рекомендация
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
        
        # ====================================================================
        # 1. VOLATILITY RISK (чем выше волатильность - тем рискованнее)
        # ====================================================================
        
        if market_data and "volatility" in market_data:
            # Предполагаем volatility в процентах (0-100)
            volatility = market_data["volatility"]
            
            # Нормализуем: >50% = max risk
            factors.volatility = min(1.0, volatility / 50)
        else:
            # Дефолт: средний риск
            factors.volatility = 0.5
        
        # ====================================================================
        # 2. LIQUIDITY RISK (низкая ликвидность = высокий риск)
        # ====================================================================
        
        if market_data and "volume_24h" in market_data:
            volume_24h = market_data["volume_24h"]
            
            # Классификация ликвидности
            if volume_24h > 10_000_000:  # >$10M
                liquidity_risk = 0.1  # Очень низкий риск
            elif volume_24h > 1_000_000:  # >$1M
                liquidity_risk = 0.3
            elif volume_24h > 100_000:  # >$100K
                liquidity_risk = 0.6
            else:
                liquidity_risk = 0.9  # Высокий риск
            
            factors.liquidity = liquidity_risk
        else:
            factors.liquidity = 0.5
        
        # ====================================================================
        # 3. MARKET CAP RISK (низкий market cap = высокий риск)
        # ====================================================================
        
        if market_data and "market_cap" in market_data:
            market_cap = market_data["market_cap"]
            
            # Классификация
            if market_cap > 1_000_000_000:  # >$1B
                mc_risk = 0.1
            elif market_cap > 100_000_000:  # >$100M
                mc_risk = 0.3
            elif market_cap > 10_000_000:  # >$10M
                mc_risk = 0.6
            else:
                mc_risk = 0.9
            
            factors.market_cap = mc_risk
        else:
            factors.market_cap = 0.5
        
        # ====================================================================
        # 4. WALLET RELIABILITY (плохая история = высокий риск)
        # ====================================================================
        
        if wallet_data:
            score = wallet_data.get("score", 50)
            roi_30d = wallet_data.get("roi_30d", 0)
            win_rate = wallet_data.get("win_rate", 0.5)
            
            # Низкий score = высокий риск
            score_risk = 1.0 - (score / 100)
            
            # Отрицательный ROI = высокий риск
            roi_risk = 0.0 if roi_30d > 0.5 else (0.5 if roi_30d > 0 else 1.0)
            
            # Низкий winrate = высокий риск
            winrate_risk = 1.0 - win_rate
            
            # Комбинируем
            factors.wallet_reliability = (score_risk * 0.5 + roi_risk * 0.3 + winrate_risk * 0.2)
        else:
            # Нет данных о кошельке = средний риск
            factors.wallet_reliability = 0.5
        
        # ====================================================================
        # 5. PATTERN CONFIDENCE (низкий confidence = высокий риск)
        # ====================================================================
        
        confidence = signal_data.get("confidence", 50)
        
        # Инвертируем: низкий confidence = высокий риск
        factors.pattern_confidence = 1.0 - (confidence / 100)
        
        # ====================================================================
        # 6. MARKET CONDITIONS (медвежий рынок = высокий риск)
        # ====================================================================
        
        # TODO: Получить актуальный market regime (bull/bear/sideways)
        # Пока дефолт
        factors.market_conditions = 0.3
        
        # ====================================================================
        # 7. SENTIMENT (негативный sentiment = высокий риск)
        # ====================================================================
        
        # TODO: Интеграция с sentiment analyzer
        # Пока дефолт
        factors.sentiment = 0.3
        
        return factors
    
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
        
        # Volatility
        if factors.volatility > 0.7:
            warnings.append("⚠️ Высокая волатильность актива")
        
        # Liquidity
        if factors.liquidity > 0.7:
            warnings.append("⚠️ Низкая ликвидность - возможны проблемы с выходом")
        
        # Market cap
        if factors.market_cap > 0.7:
            warnings.append("⚠️ Низкий market cap - высокий риск манипуляций")
        
        # Wallet
        if factors.wallet_reliability > 0.7:
            warnings.append("⚠️ Ненадёжный кошелёк - плохая история торговли")
        
        # Pattern confidence
        if factors.pattern_confidence > 0.7:
            warnings.append("⚠️ Низкий confidence сигнала")
        
        # Size vs liquidity
        if market_data and signal_data:
            volume_24h = market_data.get("volume_24h", 0)
            size_usd = signal_data.get("size_usd", 0)
            
            if volume_24h > 0 and size_usd > volume_24h * 0.05:
                warnings.append("⚠️ Размер сделки >5% от дневного объёма")
        
        return warnings
    
    def _get_recommendation(self, risk_score: int, factors: RiskFactors) -> str:
        """Генерирует рекомендацию"""
        
        if risk_score < 30:
            return "✅ Низкий риск. Можно входить с обычной позицией."
        
        elif risk_score < 60:
            return "⚠️ Средний риск. Рекомендуется уменьшить размер позиции."
        
        elif risk_score < 85:
            return "🚨 Высокий риск. Только для опытных трейдеров с малой позицией."
        
        else:
            return "🔴 ЭКСТРЕМАЛЬНЫЙ РИСК. Не рекомендуется входить."
    
    # ========================================================================
    # BATCH SCORING
    # ========================================================================
    
    def score_multiple_signals(
        self,
        signals: List[Dict]
    ) -> List[Dict]:
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
            
            # Добавляем risk данные к сигналу
            signal_with_risk = signal.copy()
            signal_with_risk["risk_score"] = risk_result["risk_score"]
            signal_with_risk["risk_level"] = risk_result["risk_level"]
            signal_with_risk["risk_warnings"] = risk_result["warnings"]
            
            results.append(signal_with_risk)
        
        return results
    
    # ========================================================================
    # OPTIMIZATION
    # ========================================================================
    
    def optimize_weights(self, historical_signals: List[Dict]):
        """
        Оптимизирует веса факторов на основе исторических данных
        
        Использует backtest для определения оптимальных весов
        """
        # TODO: Реализовать ML оптимизацию весов
        pass


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
    
    # Тестовые сигналы
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
                "market_cap": 800_000_000_000
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
                "market_cap": 5_000_000
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
                "market_cap": 200_000_000_000
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