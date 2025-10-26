# app/analytics/__init__.py
"""
ADVANCED ANALYTICS SUITE

Интеграция всех аналитических модулей:
- Sentiment Analysis
- Risk Scoring
- Correlation Detection
- Anomaly Detection

Usage:
    from app.analytics import AnalyticsEngine
    
    engine = AnalyticsEngine()
    
    # Полный анализ сигнала
    analysis = engine.analyze_signal(signal_data)
"""

from typing import Dict, List, Optional
from datetime import datetime

from app.analytics.sentiment import SentimentAnalyzer
from app.analytics.risk_scoring import RiskScorer
from app.analytics.correlation import CorrelationDetector, AnomalyDetector


class AnalyticsEngine:
    """
    Главный движок аналитики
    
    Объединяет все аналитические модули в единый интерфейс
    """
    
    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self.risk = RiskScorer()
        self.correlation = CorrelationDetector()
        self.anomaly = AnomalyDetector(sensitivity=2.0)
    
    # ========================================================================
    # COMPREHENSIVE ANALYSIS
    # ========================================================================
    
    def analyze_signal(
        self,
        signal_data: Dict,
        texts: Optional[List[str]] = None,
        check_correlations: bool = True,
        check_anomalies: bool = True
    ) -> Dict:
        """
        Полный анализ сигнала со всех сторон
        
        Args:
            signal_data: Данные сигнала {
                "asset": str,
                "confidence": int,
                "size_usd": float,
                "wallet_data": Dict,
                "market_data": Dict,
                ...
            }
            texts: Тексты для sentiment analysis (опционально)
            check_correlations: Проверять корреляции
            check_anomalies: Проверять аномалии
        
        Returns:
            {
                "sentiment": Dict,
                "risk": Dict,
                "correlations": List,
                "anomalies": List,
                "final_score": int (0-100),
                "recommendation": str
            }
        """
        
        asset = signal_data.get("asset", "UNKNOWN")
        
        # ====================================================================
        # 1. SENTIMENT ANALYSIS
        # ====================================================================
        
        sentiment_result = {"sentiment": 0.0, "label": "neutral", "confidence": 0.0}
        
        if texts:
            sentiment_result = self.sentiment.analyze_batch(texts, asset)
        
        # ====================================================================
        # 2. RISK SCORING
        # ====================================================================
        
        risk_result = self.risk.calculate_risk_score(
            asset=asset,
            signal_data=signal_data,
            wallet_data=signal_data.get("wallet_data"),
            market_data=signal_data.get("market_data")
        )
        
        # ====================================================================
        # 3. CORRELATIONS
        # ====================================================================
        
        correlations = []
        
        if check_correlations:
            correlated_assets = self.correlation.find_correlated_assets(asset)
            correlations = [
                {"asset": a, "correlation": c} for a, c in correlated_assets[:5]
            ]
        
        # ====================================================================
        # 4. ANOMALIES
        # ====================================================================
        
        anomalies = []
        
        if check_anomalies and "market_data" in signal_data:
            market_data = signal_data["market_data"]
            
            # Проверяем volume
            if "volume_24h" in market_data:
                vol_anomaly = self.anomaly.detect_anomaly(
                    f"{asset}_volume",
                    market_data["volume_24h"]
                )
                
                if vol_anomaly["is_anomaly"]:
                    anomalies.append({
                        "type": "volume",
                        "severity": vol_anomaly["severity"],
                        "explanation": vol_anomaly["explanation"]
                    })
            
            # Проверяем price change
            if "price_change_24h" in market_data:
                price_anomaly = self.anomaly.detect_anomaly(
                    f"{asset}_price_change",
                    abs(market_data["price_change_24h"])
                )
                
                if price_anomaly["is_anomaly"]:
                    anomalies.append({
                        "type": "price_movement",
                        "severity": price_anomaly["severity"],
                        "explanation": price_anomaly["explanation"]
                    })
        
        # ====================================================================
        # 5. FINAL SCORE & RECOMMENDATION
        # ====================================================================
        
        # Комбинируем все факторы
        final_score = self._calculate_final_score(
            sentiment_result,
            risk_result,
            signal_data.get("confidence", 50)
        )
        
        recommendation = self._generate_recommendation(
            final_score,
            risk_result,
            sentiment_result,
            anomalies
        )
        
        return {
            "sentiment": sentiment_result,
            "risk": risk_result,
            "correlations": correlations,
            "anomalies": anomalies,
            "final_score": final_score,
            "recommendation": recommendation,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def analyze_multiple_signals(
        self,
        signals: List[Dict]
    ) -> List[Dict]:
        """
        Анализирует несколько сигналов параллельно
        
        Returns:
            Список сигналов с добавленной аналитикой
        """
        
        results = []
        
        for signal in signals:
            analysis = self.analyze_signal(signal)
            
            signal_with_analysis = signal.copy()
            signal_with_analysis["analytics"] = analysis
            
            results.append(signal_with_analysis)
        
        # Сортируем по final_score (лучшие первые)
        results.sort(key=lambda x: x["analytics"]["final_score"], reverse=True)
        
        return results
    
    # ========================================================================
    # SCORING HELPERS
    # ========================================================================
    
    def _calculate_final_score(
        self,
        sentiment: Dict,
        risk: Dict,
        signal_confidence: int
    ) -> int:
        """
        Рассчитывает финальный комплексный score
        
        Учитывает:
        - Signal confidence (40%)
        - Risk score (inverted, 30%)
        - Sentiment (30%)
        
        Returns:
            Score 0-100 (выше = лучше)
        """
        
        # Signal confidence component
        confidence_score = signal_confidence
        
        # Risk score component (инвертируем - низкий риск = высокий score)
        risk_score_raw = risk.get("risk_score", 50)
        risk_score = 100 - risk_score_raw
        
        # Sentiment component (конвертируем -1..+1 в 0..100)
        sentiment_value = sentiment.get("sentiment", 0.0)
        sentiment_score = (sentiment_value + 1) * 50
        
        # Weighted average
        final = (
            confidence_score * 0.40 +
            risk_score * 0.30 +
            sentiment_score * 0.30
        )
        
        return int(final)
    
    def _generate_recommendation(
        self,
        final_score: int,
        risk: Dict,
        sentiment: Dict,
        anomalies: List[Dict]
    ) -> str:
        """Генерирует финальную рекомендацию"""
        
        # Базовая рекомендация по score
        if final_score >= 75:
            base = "🟢 STRONG BUY"
        elif final_score >= 60:
            base = "🟡 BUY"
        elif final_score >= 40:
            base = "⚪ NEUTRAL"
        elif final_score >= 25:
            base = "🟠 AVOID"
        else:
            base = "🔴 STRONG AVOID"
        
        # Модификаторы
        modifiers = []
        
        # High risk warning
        if risk.get("risk_score", 0) > 70:
            modifiers.append("⚠️ High Risk")
        
        # Negative sentiment
        if sentiment.get("label") == "bearish":
            modifiers.append("📉 Bearish Sentiment")
        
        # Anomalies
        if anomalies:
            severe_anomalies = [a for a in anomalies if a["severity"] > 0.7]
            if severe_anomalies:
                modifiers.append(f"🚨 {len(severe_anomalies)} Anomalies")
        
        # Комбинируем
        if modifiers:
            return f"{base} ({', '.join(modifiers)})"
        else:
            return base
    
    # ========================================================================
    # MARKET OVERVIEW
    # ========================================================================
    
    def get_market_overview(self) -> Dict:
        """
        Обзор всего рынка на основе накопленных данных
        
        Returns:
            {
                "overall_sentiment": str,
                "high_correlation_pairs": List,
                "detected_anomalies": List,
                "risk_distribution": Dict
            }
        """
        
        # Overall sentiment
        # TODO: Агрегировать sentiment по всем активам
        
        # High correlation pairs
        correlation_pairs = []
        # TODO: Собрать топ корреляций
        
        # Anomalies
        anomalies = self.anomaly.scan_for_anomalies()
        
        return {
            "overall_sentiment": "neutral",
            "high_correlation_pairs": correlation_pairs,
            "detected_anomalies": anomalies,
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global instance
_engine = None

def get_analytics_engine() -> AnalyticsEngine:
    """
    Получает глобальный instance аналитического движка
    
    Usage:
        from app.analytics import get_analytics_engine
        
        engine = get_analytics_engine()
        analysis = engine.analyze_signal(signal_data)
    """
    global _engine
    
    if _engine is None:
        _engine = AnalyticsEngine()
    
    return _engine


def analyze_signal(signal_data: Dict) -> Dict:
    """
    Quick signal analysis
    
    Usage:
        from app.analytics import analyze_signal
        
        analysis = analyze_signal({
            "asset": "BTC",
            "confidence": 75,
            ...
        })
    """
    engine = get_analytics_engine()
    return engine.analyze_signal(signal_data)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Main engine
    "AnalyticsEngine",
    "get_analytics_engine",
    
    # Quick functions
    "analyze_signal",
    
    # Individual modules
    "SentimentAnalyzer",
    "RiskScorer",
    "CorrelationDetector",
    "AnomalyDetector"
]