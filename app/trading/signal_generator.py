"""
SIGNAL GENERATOR
Главный компонент для генерации торговых сигналов
Объединяет технический анализ, фундаментальный анализ, hot wallet tracking и ML
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np

from .technical_analysis import TechnicalAnalyzer, TechnicalSignal
from .fundamental_analysis import FundamentalAnalyzer, FundamentalData
from .hot_wallet_tracker import HotWalletTracker, WalletMovement
from .ml_predictor import MLPredictor, MLPrediction
from .position_tracker import PositionTracker
from .performance_stats import PerformanceStats


@dataclass
class TradingSignal:
    """Комплексный торговый сигнал"""
    asset: str
    timestamp: datetime
    
    # Общий сигнал
    signal: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
    confidence: float  # 0-100
    
    # Компоненты
    technical: Optional[TechnicalSignal]
    fundamental: Optional[FundamentalData]
    wallet: Optional[Dict]
    ml: Optional[MLPrediction]
    
    # Рекомендации
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size_pct: float  # % от капитала
    
    # Reasoning
    reasons: List[str]
    warnings: List[str]
    
    def to_dict(self) -> dict:
        return {
            'asset': self.asset,
            'timestamp': self.timestamp.isoformat(),
            'signal': self.signal,
            'confidence': self.confidence,
            'technical': self.technical.to_dict() if self.technical else None,
            'fundamental': self.fundamental.to_dict() if self.fundamental else None,
            'wallet': self.wallet,
            'ml': self.ml.to_dict() if self.ml else None,
            'recommendations': {
                'entry_price': self.entry_price,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'position_size_pct': self.position_size_pct
            },
            'reasons': self.reasons,
            'warnings': self.warnings
        }


class SignalGenerator:
    """
    Главный генератор торговых сигналов
    
    Объединяет:
    - Технический анализ (50+ индикаторов)
    - Фундаментальный анализ (токеномика, метрики)
    - Hot wallet движения (accumulation/distribution)
    - ML предсказания (4 временных интервала)
    
    Управляет:
    - Position Tracker (открытие/закрытие позиций)
    - Performance Stats (метрики эффективности)
    """
    
    def __init__(self, coingecko_key: Optional[str] = None):
        # Аналитические компоненты
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer(coingecko_key)
        self.hot_wallet = HotWalletTracker(coingecko_key)
        self.ml = MLPredictor()
        
        # Управление позициями
        self.positions = PositionTracker()
        self.performance = PerformanceStats(self.positions)
        
        print("🚀 [SIGNAL_GENERATOR] Инициализирован")
        print("   • Technical Analysis: ✓")
        print("   • Fundamental Analysis: ✓")
        print("   • Hot Wallet Tracker: ✓")
        print("   • ML Predictor: ✓")
        print("   • Position Tracker: ✓")
        print("   • Performance Stats: ✓")
    
    async def generate_signal(
        self,
        asset: str,
        price_data: pd.DataFrame,
        session: aiohttp.ClientSession
    ) -> Optional[TradingSignal]:
        """
        Генерация комплексного торгового сигнала
        
        Args:
            asset: Символ актива (BTC, ETH, etc)
            price_data: DataFrame с OHLCV данными
            session: aiohttp session
        
        Returns:
            TradingSignal или None если недостаточно данных
        """
        
        try:
            print(f"\n{'='*80}")
            print(f"🔍 [SIGNAL_GEN] Анализ {asset}")
            print(f"{'='*80}")
            
            # 1. Технический анализ
            print(f"📊 [1/4] Технический анализ...")
            technical_signal = await self.technical.analyze(asset, price_data)
            
            if not technical_signal:
                print(f"❌ [SIGNAL_GEN] Недостаточно данных для технического анализа {asset}")
                return None
            
            print(f"   ✓ Signal: {technical_signal.signal_type}")
            print(f"   ✓ Strength: {technical_signal.strength:.1f}")
            print(f"   ✓ RSI: {technical_signal.rsi:.1f}")
            print(f"   ✓ Trend: {technical_signal.trend}")
            
            # 2. Фундаментальный анализ
            print(f"📈 [2/4] Фундаментальный анализ...")
            fundamental_data = await self.fundamental.analyze(asset, session)
            
            if fundamental_data:
                print(f"   ✓ Rating: {fundamental_data.rating}")
                print(f"   ✓ Score: {fundamental_data.fundamental_score:.1f}/100")
                if fundamental_data.market_cap_rank:
                    print(f"   ✓ Rank: #{fundamental_data.market_cap_rank}")
            else:
                print(f"   ⚠️ Фундаментальные данные недоступны")
            
            # 3. Hot wallet анализ
            print(f"🔥 [3/4] Анализ wallet движений...")
            wallet_analysis = self.hot_wallet.get_cluster_analysis(asset, hours=6)
            
            if wallet_analysis:
                print(f"   ✓ Signal: {wallet_analysis['dominant_signal']}")
                print(f"   ✓ Net Flow: ${wallet_analysis['net_flow_usd']:,.0f}")
                print(f"   ✓ Movements: {wallet_analysis['total_moves']}")
            else:
                print(f"   ⚠️ Нет wallet активности")
            
            # 4. ML предсказание
            print(f"🤖 [4/4] ML предсказание...")
            ml_prediction = None
            
            if technical_signal and fundamental_data:
                ml_prediction = await self.ml.predict(
                    asset=asset,
                    technical_data=technical_signal.indicators,
                    fundamental_data=fundamental_data.to_dict(),
                    wallet_data=wallet_analysis
                )
                
                if ml_prediction:
                    print(f"   ✓ Prediction: {ml_prediction.prediction}")
                    print(f"   ✓ Confidence: {ml_prediction.confidence:.1f}%")
                    print(f"   ✓ Expected 1h: {ml_prediction.expected_change_1h:+.2f}%")
                    print(f"   ✓ Expected 24h: {ml_prediction.expected_change_24h:+.2f}%")
                    print(f"   ✓ Expected 7d: {ml_prediction.expected_change_7d:+.2f}%")
                else:
                    print(f"   ⚠️ ML предсказание недоступно")
            
            # 5. Комбинируем сигналы
            print(f"\n⚡ Комбинирование сигналов...")
            final_signal, confidence, reasons, warnings = self._combine_signals(
                technical_signal,
                fundamental_data,
                wallet_analysis,
                ml_prediction
            )
            
            print(f"   ✓ Final Signal: {final_signal}")
            print(f"   ✓ Confidence: {confidence:.1f}%")
            
            # 6. Рассчитываем рекомендации
            print(f"\n💡 Расчёт рекомендаций...")
            entry_price = technical_signal.price
            stop_loss, take_profit, position_size = self._calculate_recommendations(
                asset,
                entry_price,
                final_signal,
                technical_signal,
                ml_prediction
            )
            
            if stop_loss:
                sl_pct = abs((stop_loss - entry_price) / entry_price * 100)
                print(f"   ✓ Stop-Loss: ${stop_loss:,.2f} (-{sl_pct:.1f}%)")
            
            if take_profit:
                tp_pct = abs((take_profit - entry_price) / entry_price * 100)
                print(f"   ✓ Take-Profit: ${take_profit:,.2f} (+{tp_pct:.1f}%)")
            
            print(f"   ✓ Position Size: {position_size:.1f}% of capital")
            
            print(f"\n{'='*80}")
            print(f"✅ [SIGNAL_GEN] Сигнал сгенерирован для {asset}")
            print(f"{'='*80}\n")
            
            return TradingSignal(
                asset=asset,
                timestamp=datetime.utcnow(),
                signal=final_signal,
                confidence=confidence,
                technical=technical_signal,
                fundamental=fundamental_data,
                wallet=wallet_analysis,
                ml=ml_prediction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size_pct=position_size,
                reasons=reasons,
                warnings=warnings
            )
            
        except Exception as e:
            print(f"❌ [SIGNAL_GEN] Ошибка генерации сигнала для {asset}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _combine_signals(
        self,
        technical: TechnicalSignal,
        fundamental: Optional[FundamentalData],
        wallet: Optional[Dict],
        ml: Optional[MLPrediction]
    ) -> tuple:
        """
        Комбинирование сигналов в финальный
        
        Веса:
        - Технический анализ: 30%
        - Фундаментальный анализ: 20%
        - Hot wallet движения: 25%
        - ML предсказание: 25%
        
        Returns:
            (signal, confidence, reasons, warnings)
        """
        
        signals = []
        weights = []
        reasons = []
        warnings = []
        
        # 1. Технический сигнал (вес 30%)
        tech_score = self._signal_to_score(technical.signal_type)
        signals.append(tech_score)
        weights.append(0.3)
        
        # Берём топ-3 причины
        top_reasons = technical.reasons[:3]
        for reason in top_reasons:
            reasons.append(f"[TECH] {reason}")
        
        # Предупреждения
        for warning in technical.warnings:
            warnings.append(f"[TECH] {warning}")
        
        # 2. Фундаментальный анализ (вес 20%)
        if fundamental:
            fund_score = self._rating_to_score(fundamental.rating)
            signals.append(fund_score)
            weights.append(0.2)
            
            reasons.append(f"[FUND] Rating: {fundamental.rating}, Score: {fundamental.fundamental_score:.1f}/100")
            
            # Дополнительные фундаментальные факторы
            if fundamental.market_cap_rank and fundamental.market_cap_rank <= 20:
                reasons.append(f"[FUND] Top-20 asset by market cap (#{fundamental.market_cap_rank})")
            
            if fundamental.developer_score and fundamental.developer_score > 70:
                reasons.append(f"[FUND] Strong developer activity ({fundamental.developer_score:.0f}/100)")
            
            if fundamental.price_change_7d and abs(fundamental.price_change_7d) > 10:
                reasons.append(f"[FUND] Strong 7d momentum ({fundamental.price_change_7d:+.1f}%)")
        
        # 3. Hot wallet движения (вес 25%)
        if wallet:
            wallet_score = 0
            
            if wallet.get('dominant_signal') == 'ACCUMULATION':
                wallet_score = 1.0
                net_flow = wallet.get('net_flow_usd', 0)
                acc_signals = wallet.get('accumulation_signals', 0)
                reasons.append(f"[WALLET] 🔥 Accumulation detected: ${net_flow:,.0f} net inflow ({acc_signals} signals)")
                
                if net_flow > 5_000_000:
                    reasons.append(f"[WALLET] 🐋 MASSIVE accumulation: $5M+ inflow")
                    wallet_score = 1.2  # Boost score
            
            elif wallet.get('dominant_signal') == 'DISTRIBUTION':
                wallet_score = -1.0
                net_flow = wallet.get('net_flow_usd', 0)
                dist_signals = wallet.get('distribution_signals', 0)
                reasons.append(f"[WALLET] ⚠️ Distribution detected: ${abs(net_flow):,.0f} net outflow ({dist_signals} signals)")
                
                if abs(net_flow) > 5_000_000:
                    reasons.append(f"[WALLET] 🚨 MASSIVE distribution: $5M+ outflow")
                    wallet_score = -1.2  # Boost score
            
            else:
                wallet_score = 0
                reasons.append(f"[WALLET] Neutral flow")
            
            signals.append(wallet_score)
            weights.append(0.25)
        
        # 4. ML предсказание (вес 25%)
        if ml:
            ml_score = self._signal_to_score(ml.prediction)
            signals.append(ml_score)
            weights.append(0.25)
            
            reasons.append(f"[ML] {ml.prediction} (confidence: {ml.confidence:.1f}%)")
            
            # Детализация по временным интервалам
            if abs(ml.expected_change_1h) > 1:
                reasons.append(f"[ML] Short-term 1h: {ml.expected_change_1h:+.2f}%")
            
            if abs(ml.expected_change_24h) > 3:
                reasons.append(f"[ML] Medium-term 24h: {ml.expected_change_24h:+.2f}%")
            
            if abs(ml.expected_change_7d) > 10:
                reasons.append(f"[ML] Long-term 7d: {ml.expected_change_7d:+.2f}%")
            
            # Качество модели
            if ml.model_accuracy < 0.6:
                warnings.append(f"[ML] Low model accuracy ({ml.model_accuracy:.1%})")
        
        # Нормализуем веса
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Взвешенная сумма
        weighted_score = sum(s * w for s, w in zip(signals, weights))
        
        # Конвертируем в сигнал и confidence
        if weighted_score > 0.6:
            final_signal = 'STRONG_BUY'
            confidence = min(95, 50 + weighted_score * 50)
        elif weighted_score > 0.2:
            final_signal = 'BUY'
            confidence = min(85, 50 + weighted_score * 40)
        elif weighted_score < -0.6:
            final_signal = 'STRONG_SELL'
            confidence = min(95, 50 + abs(weighted_score) * 50)
        elif weighted_score < -0.2:
            final_signal = 'SELL'
            confidence = min(85, 50 + abs(weighted_score) * 40)
        else:
            final_signal = 'HOLD'
            confidence = 50
            reasons.append("Mixed signals - recommend waiting for clearer confirmation")
        
        return final_signal, confidence, reasons, warnings
    
    def _signal_to_score(self, signal: str) -> float:
        """Конвертация сигнала в числовой score (-1 до 1)"""
        mapping = {
            'STRONG_BUY': 1.0,
            'BUY': 0.5,
            'HOLD': 0.0,
            'SELL': -0.5,
            'STRONG_SELL': -1.0
        }
        return mapping.get(signal, 0.0)
    
    def _rating_to_score(self, rating: str) -> float:
        """Конвертация фундаментального рейтинга в score (-1 до 1)"""
        mapping = {
            'STRONG_BUY': 1.0,
            'BUY': 0.5,
            'NEUTRAL': 0.0,
            'SELL': -0.5,
            'STRONG_SELL': -1.0
        }
        return mapping.get(rating, 0.0)
    
    def _calculate_recommendations(
        self,
        asset: str,
        entry_price: float,
        signal: str,
        technical: TechnicalSignal,
        ml: Optional[MLPrediction]
    ) -> tuple:
        """
        Расчёт stop-loss, take-profit и размера позиции
        
        Stop-Loss:
        - Основан на ATR (Average True Range)
        - Учитывает уровни поддержки
        - Минимум 2% для волатильных активов
        
        Take-Profit:
        - Основан на уровнях сопротивления
        - Учитывает ML предсказания
        - Risk/Reward минимум 2:1
        
        Position Size:
        - STRONG_BUY/SELL: 10% капитала
        - BUY/SELL: 5% капитала
        - HOLD: 0%
        
        Returns:
            (stop_loss, take_profit, position_size_pct)
        """
        
        # ATR для волатильности
        atr = technical.indicators.get('atr', entry_price * 0.02)
        atr_pct = (atr / entry_price) * 100
        
        # Уровни поддержки/сопротивления
        support = technical.support_level
        resistance = technical.resistance_level
        
        stop_loss = None
        take_profit = None
        position_size = 0.0
        
        if signal in ['BUY', 'STRONG_BUY']:
            # LONG позиция
            
            # Stop-Loss: чуть ниже поддержки или 2 ATR
            stop_loss_atr = entry_price - (2 * atr)
            stop_loss_support = support * 0.98  # 2% ниже поддержки
            
            # Берём более консервативный вариант
            stop_loss = max(stop_loss_atr, stop_loss_support)
            
            # Минимальный stop-loss 2%
            min_stop_loss = entry_price * 0.98
            stop_loss = min(stop_loss, min_stop_loss)
            
            # Take-Profit: сопротивление или ML target
            take_profit_resistance = resistance * 0.98  # 2% ниже сопротивления для безопасности
            
            if ml and ml.expected_change_24h > 0:
                # Используем ML предсказание
                ml_target = entry_price * (1 + ml.expected_change_24h / 100)
                
                # Учитываем диапазон неопределённости
                ml_range = ml.change_24h_range
                if ml_range:
                    # Берём среднее между предсказанием и нижней границей диапазона
                    conservative_target = (ml_target + entry_price * (1 + ml_range[0] / 100)) / 2
                    take_profit = min(take_profit_resistance, conservative_target)
                else:
                    take_profit = min(take_profit_resistance, ml_target)
            else:
                take_profit = take_profit_resistance
            
            # Проверяем Risk/Reward ratio (минимум 2:1)
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
            
            if reward < risk * 2:
                # Увеличиваем take-profit для достижения 2:1
                take_profit = entry_price + (risk * 2)
            
            # Position size
            if signal == 'STRONG_BUY':
                position_size = 10.0
            else:
                position_size = 5.0
        
        elif signal in ['SELL', 'STRONG_SELL']:
            # SHORT позиция
            
            # Stop-Loss: чуть выше сопротивления или 2 ATR
            stop_loss_atr = entry_price + (2 * atr)
            stop_loss_resistance = resistance * 1.02  # 2% выше сопротивления
            
            # Берём более консервативный вариант
            stop_loss = min(stop_loss_atr, stop_loss_resistance)
            
            # Максимальный stop-loss 2%
            max_stop_loss = entry_price * 1.02
            stop_loss = max(stop_loss, max_stop_loss)
            
            # Take-Profit: поддержка или ML target
            take_profit_support = support * 1.02  # 2% выше поддержки для безопасности
            
            if ml and ml.expected_change_24h < 0:
                # Используем ML предсказание
                ml_target = entry_price * (1 + ml.expected_change_24h / 100)
                
                # Учитываем диапазон неопределённости
                ml_range = ml.change_24h_range
                if ml_range:
                    # Берём среднее между предсказанием и верхней границей диапазона
                    conservative_target = (ml_target + entry_price * (1 + ml_range[1] / 100)) / 2
                    take_profit = max(take_profit_support, conservative_target)
                else:
                    take_profit = max(take_profit_support, ml_target)
            else:
                take_profit = take_profit_support
            
            # Проверяем Risk/Reward ratio (минимум 2:1)
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
            
            if reward < risk * 2:
                # Увеличиваем take-profit для достижения 2:1
                take_profit = entry_price - (risk * 2)
            
            # Position size
            if signal == 'STRONG_SELL':
                position_size = 10.0
            else:
                position_size = 5.0
        
        else:
            # HOLD - не открываем позицию
            stop_loss = None
            take_profit = None
            position_size = 0.0
        
        return stop_loss, take_profit, position_size
    
    def format_signal_message(self, signal: TradingSignal) -> str:
        """
        Форматирование сигнала для Telegram
        
        Включает все компоненты анализа и disclaimer
        """
        
        # Эмодзи для сигналов
        signal_emoji = {
            'STRONG_BUY': '🟢🔥',
            'BUY': '🟢',
            'HOLD': '⚪',
            'SELL': '🔴',
            'STRONG_SELL': '🔴🔥'
        }
        
        emoji = signal_emoji.get(signal.signal, '⚪')
        
        # Заголовок
        message = f"""
{emoji} <b>TRADING SIGNAL: {signal.asset}</b>

<b>📊 OVERALL SIGNAL: {signal.signal}</b>
<b>Confidence:</b> {signal.confidence:.1f}%
<b>Entry Price:</b> ${signal.entry_price:,.2f}
<b>Timestamp:</b> {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}

"""
        
        # Рекомендации
        if signal.stop_loss or signal.take_profit or signal.position_size_pct > 0:
            message += "<b>💡 TRADE RECOMMENDATIONS:</b>\n"
            
            if signal.stop_loss:
                sl_pct = abs((signal.stop_loss - signal.entry_price) / signal.entry_price * 100)
                message += f"<b>Stop-Loss:</b> ${signal.stop_loss:,.2f} (-{sl_pct:.2f}%)\n"
            
            if signal.take_profit:
                tp_pct = abs((signal.take_profit - signal.entry_price) / signal.entry_price * 100)
                message += f"<b>Take-Profit:</b> ${signal.take_profit:,.2f} (+{tp_pct:.2f}%)\n"
            
            if signal.position_size_pct > 0:
                message += f"<b>Position Size:</b> {signal.position_size_pct:.1f}% of capital\n"
            
            # Risk/Reward
            if signal.stop_loss and signal.take_profit:
                risk = abs(signal.entry_price - signal.stop_loss)
                reward = abs(signal.take_profit - signal.entry_price)
                rr_ratio = reward / risk if risk > 0 else 0
                message += f"<b>Risk/Reward Ratio:</b> 1:{rr_ratio:.2f}\n"
            
            message += "\n"
        
        # Технический анализ
        if signal.technical:
            t = signal.technical
            message += f"""<b>📈 TECHNICAL ANALYSIS:</b>
<b>Signal:</b> {t.signal_type} (Strength: {t.strength:.1f}/100)
<b>Trend:</b> {t.trend.replace('_', ' ').title()}
<b>Volume Trend:</b> {t.volume_trend.title()}

<b>Key Indicators:</b>
- RSI: {t.rsi:.1f} ({self._rsi_interpretation(t.rsi)})
- MACD: {t.macd_signal.title()}
- Bollinger Bands: {t.bollinger_position.title()}

<b>Support/Resistance:</b>
- Support: ${t.support_level:,.2f}
- Resistance: ${t.resistance_level:,.2f}

"""
        
        # ML предсказание
        if signal.ml:
            ml = signal.ml
            message += f"""<b>🤖 ML PREDICTION:</b>
<b>Direction:</b> {ml.prediction} (Confidence: {ml.confidence:.1f}%)

<b>Expected Price Changes:</b>
- 1 Hour: {ml.expected_change_1h:+.2f}% (range: {ml.change_1h_range[0]:+.2f}% to {ml.change_1h_range[1]:+.2f}%)
- 4 Hours: {ml.expected_change_4h:+.2f}% (range: {ml.change_4h_range[0]:+.2f}% to {ml.change_4h_range[1]:+.2f}%)
- 24 Hours: {ml.expected_change_24h:+.2f}% (range: {ml.change_24h_range[0]:+.2f}% to {ml.change_24h_range[1]:+.2f}%)
- 7 Days: {ml.expected_change_7d:+.2f}% (range: {ml.change_7d_range[0]:+.2f}% to {ml.change_7d_range[1]:+.2f}%)

<b>Model Performance:</b>
- Classification Accuracy: {ml.model_accuracy:.1%}
- MAE 1h: {ml.model_mae_1h:.3f}%
- MAE 24h: {ml.model_mae_24h:.3f}%

"""
            
            # Топ факторы влияния
            if ml.top_factors:
                message += "<b>Top Factors:</b>\n"
                for i, (factor, importance) in enumerate(ml.top_factors[:3], 1):
                    message += f"{i}. {factor.replace('_', ' ').title()}: {importance:.3f}\n"
                message += "\n"
        
        # Фундаментальный анализ
        if signal.fundamental:
            f = signal.fundamental
            message += f"""<b>📊 FUNDAMENTAL ANALYSIS:</b>
<b>Rating:</b> {f.rating}
<b>Fundamental Score:</b> {f.fundamental_score:.1f}/100
"""
            
            if f.market_cap_rank:
                message += f"<b>Market Cap Rank:</b> #{f.market_cap_rank}\n"
            
            if f.market_cap:
                if f.market_cap >= 1e9:
                    message += f"<b>Market Cap:</b> ${f.market_cap/1e9:.2f}B\n"
                else:
                    message += f"<b>Market Cap:</b> ${f.market_cap/1e6:.1f}M\n"
            
            if f.volume_24h:
                if f.volume_24h >= 1e9:
                    message += f"<b>24h Volume:</b> ${f.volume_24h/1e9:.2f}B\n"
                else:
                    message += f"<b>24h Volume:</b> ${f.volume_24h/1e6:.1f}M\n"
            
            if f.price_change_24h is not None:
                message += f"<b>24h Change:</b> {f.price_change_24h:+.2f}%\n"
            
            if f.price_change_7d is not None:
                message += f"<b>7d Change:</b> {f.price_change_7d:+.2f}%\n"
            
            # Developer & Community scores
            if f.developer_score or f.community_score:
                message += "\n<b>Activity Scores:</b>\n"
                if f.developer_score:
                    message += f"• Developer: {f.developer_score:.0f}/100\n"
                if f.community_score:
                    message += f"• Community: {f.community_score:.0f}/100\n"
            
            message += "\n"
        
        # Hot wallet движения
        if signal.wallet:
            w = signal.wallet
            message += f"""<b>🔥 HOT WALLET ACTIVITY:</b>
<b>Dominant Signal:</b> {w['dominant_signal']}
<b>Confidence:</b> {w['confidence']:.1f}%
<b>Net Flow (6h):</b> ${w['net_flow_usd']:,.0f}

<b>Movement Details:</b>
- Total Movements: {w['total_moves']}
- Inflows: ${w['inflow_usd']:,.0f}
- Outflows: ${w['outflow_usd']:,.0f}
- Accumulation Signals: {w['accumulation_signals']}
- Distribution Signals: {w['distribution_signals']}

"""
        
        # Ключевые причины
        if signal.reasons:
            message += "<b>📝 KEY ANALYSIS POINTS:</b>\n"
            for i, reason in enumerate(signal.reasons[:8], 1):
                message += f"{i}. {reason}\n"
            message += "\n"
        
        # Предупреждения
        if signal.warnings:
            message += "<b>⚠️ WARNINGS & CONSIDERATIONS:</b>\n"
            for i, warning in enumerate(signal.warnings[:5], 1):
                message += f"{i}. {warning}\n"
            message += "\n"
        
        # Разделитель
        message += "─" * 40 + "\n\n"
        
        # КРИТИЧЕСКИЙ ДИСКЛЕЙМЕР
        message += """<b>⚠️ IMPORTANT DISCLAIMER:</b>

<b>This is NOT financial advice.</b>

This signal is generated by an automated AI system for <b>informational and educational purposes only</b>. This is not a recommendation to buy, sell, or hold any cryptocurrency or financial instrument.

<b>Key Points:</b>
- Trading cryptocurrencies involves substantial risk
- You may lose all invested capital
- Past performance does not guarantee future results
- Always conduct your own research (DYOR)
- Consult with a licensed financial advisor before investing
- Never invest more than you can afford to lose

<b>No Guarantee:</b> The accuracy of predictions and analysis cannot be guaranteed. Markets are unpredictable and subject to rapid changes.

<b>By using this information, you acknowledge these risks and agree that you alone are responsible for your investment decisions.</b>
"""
        
        return message
    
    def _rsi_interpretation(self, rsi: float) -> str:
        """Интерпретация RSI"""
        if rsi < 20:
            return "Extremely Oversold"
        elif rsi < 30:
            return "Oversold"
        elif rsi < 40:
            return "Slightly Oversold"
        elif rsi < 60:
            return "Neutral"
        elif rsi < 70:
            return "Slightly Overbought"
        elif rsi < 80:
            return "Overbought"
        else:
            return "Extremely Overbought"