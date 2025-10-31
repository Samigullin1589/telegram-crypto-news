"""
TECHNICAL ANALYSIS ENGINE
Комплексный технический анализ с генерацией сигналов
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .indicators import TechnicalIndicators


@dataclass
class TechnicalSignal:
    """Технический торговый сигнал"""
    asset: str
    timestamp: datetime
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-100
    confidence: float  # 0-100
    
    # Основные индикаторы
    price: float
    rsi: float
    macd_signal: str
    bollinger_position: str  # 'upper', 'middle', 'lower'
    
    # Дополнительная информация
    trend: str  # 'bullish', 'bearish', 'sideways'
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    support_level: float
    resistance_level: float
    
    # Детали для анализа
    indicators: Dict
    reasons: List[str]
    warnings: List[str]
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'asset': self.asset,
            'timestamp': self.timestamp.isoformat(),
            'signal_type': self.signal_type,
            'strength': self.strength,
            'confidence': self.confidence,
            'price': self.price,
            'rsi': self.rsi,
            'macd_signal': self.macd_signal,
            'bollinger_position': self.bollinger_position,
            'trend': self.trend,
            'volume_trend': self.volume_trend,
            'support': self.support_level,
            'resistance': self.resistance_level,
            'reasons': self.reasons,
            'warnings': self.warnings,
            'indicators': self.indicators
        }


class TechnicalAnalyzer:
    """
    Полный технический анализ с генерацией сигналов
    
    Использует:
    - Трендовые индикаторы (SMA, EMA, MACD, ADX)
    - Моментум индикаторы (RSI, Stochastic, Williams %R)
    - Волатильность (Bollinger Bands, ATR, Keltner)
    - Объем (OBV, VWAP, Volume Profile)
    """
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        
        # Пороги для сигналов
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70
        self.RSI_EXTREME_OVERSOLD = 20
        self.RSI_EXTREME_OVERBOUGHT = 80
        
        print("📊 [TECH_ANALYSIS] Инициализирован")
    
    async def analyze(
        self,
        asset: str,
        df: pd.DataFrame
    ) -> Optional[TechnicalSignal]:
        """
        Полный технический анализ актива
        
        Args:
            asset: Символ актива
            df: DataFrame с колонками [timestamp, open, high, low, close, volume]
        
        Returns:
            TechnicalSignal или None
        """
        
        if df is None or len(df) < 50:
            return None
        
        try:
            # Подготовка данных
            df = df.copy()
            df = df.sort_values('timestamp')
            
            # Расчет всех индикаторов
            indicators_data = self._calculate_all_indicators(df)
            
            # Определение тренда
            trend = self._determine_trend(df, indicators_data)
            
            # Анализ объема
            volume_trend = self._analyze_volume(df)
            
            # Уровни поддержки/сопротивления
            support, resistance = self.indicators.support_resistance(df['close'])
            
            # Генерация сигнала
            signal_type, strength, confidence, reasons = self._generate_signal(
                df, indicators_data, trend, volume_trend
            )
            
            # Предупреждения
            warnings = self._check_warnings(df, indicators_data)
            
            # Текущие значения
            current = df.iloc[-1]
            
            return TechnicalSignal(
                asset=asset,
                timestamp=datetime.utcnow(),
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                price=current['close'],
                rsi=indicators_data['rsi'].iloc[-1],
                macd_signal=indicators_data['macd_signal'],
                bollinger_position=indicators_data['bollinger_position'],
                trend=trend,
                volume_trend=volume_trend,
                support_level=support,
                resistance_level=resistance,
                indicators=self._extract_current_indicators(indicators_data),
                reasons=reasons,
                warnings=warnings
            )
            
        except Exception as e:
            print(f"❌ [TECH_ANALYSIS] Ошибка анализа {asset}: {e}")
            return None
    
    def _calculate_all_indicators(self, df: pd.DataFrame) -> Dict:
        """Расчет всех индикаторов"""
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        indicators = {}
        
        # Трендовые индикаторы
        indicators['sma_20'] = self.indicators.sma(close, 20)
        indicators['sma_50'] = self.indicators.sma(close, 50)
        indicators['sma_200'] = self.indicators.sma(close, 200)
        indicators['ema_12'] = self.indicators.ema(close, 12)
        indicators['ema_26'] = self.indicators.ema(close, 26)
        
        macd, macd_signal, macd_hist = self.indicators.macd(close)
        indicators['macd'] = macd
        indicators['macd_signal_line'] = macd_signal
        indicators['macd_histogram'] = macd_hist
        
        # MACD сигнал
        if macd.iloc[-1] > macd_signal.iloc[-1]:
            indicators['macd_signal'] = 'bullish'
        else:
            indicators['macd_signal'] = 'bearish'
        
        adx, adx_pos, adx_neg = self.indicators.adx(high, low, close)
        indicators['adx'] = adx
        indicators['adx_pos'] = adx_pos
        indicators['adx_neg'] = adx_neg
        
        # Моментум
        indicators['rsi'] = self.indicators.rsi(close, 14)
        
        stoch_k, stoch_d = self.indicators.stochastic(high, low, close)
        indicators['stoch_k'] = stoch_k
        indicators['stoch_d'] = stoch_d
        
        indicators['williams_r'] = self.indicators.williams_r(high, low, close)
        
        # Волатильность
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(close)
        indicators['bb_upper'] = bb_upper
        indicators['bb_middle'] = bb_middle
        indicators['bb_lower'] = bb_lower
        
        # Bollinger position
        current_price = close.iloc[-1]
        bb_width = bb_upper.iloc[-1] - bb_lower.iloc[-1]
        if current_price >= bb_upper.iloc[-1]:
            indicators['bollinger_position'] = 'upper'
        elif current_price <= bb_lower.iloc[-1]:
            indicators['bollinger_position'] = 'lower'
        else:
            indicators['bollinger_position'] = 'middle'
        
        indicators['atr'] = self.indicators.atr(high, low, close)
        
        # Объем
        indicators['obv'] = self.indicators.obv(close, volume)
        indicators['vwap'] = self.indicators.vwap(high, low, close, volume)
        
        # Volume Profile
        indicators['volume_profile'] = self.indicators.volume_profile(close, volume)
        
        # Сила тренда
        indicators['trend_strength'] = self.indicators.trend_strength(close)
        
        return indicators
    
    def _determine_trend(self, df: pd.DataFrame, indicators: Dict) -> str:
        """Определение тренда"""
        
        close = df['close'].iloc[-1]
        sma_20 = indicators['sma_20'].iloc[-1]
        sma_50 = indicators['sma_50'].iloc[-1]
        sma_200 = indicators['sma_200'].iloc[-1]
        
        adx = indicators['adx'].iloc[-1]
        adx_pos = indicators['adx_pos'].iloc[-1]
        adx_neg = indicators['adx_neg'].iloc[-1]
        
        # Сильный восходящий тренд
        if (close > sma_20 > sma_50 > sma_200 and 
            adx > 25 and adx_pos > adx_neg):
            return 'strong_bullish'
        
        # Восходящий тренд
        elif close > sma_20 > sma_50:
            return 'bullish'
        
        # Сильный нисходящий тренд
        elif (close < sma_20 < sma_50 < sma_200 and 
              adx > 25 and adx_neg > adx_pos):
            return 'strong_bearish'
        
        # Нисходящий тренд
        elif close < sma_20 < sma_50:
            return 'bearish'
        
        # Боковик
        else:
            return 'sideways'
    
    def _analyze_volume(self, df: pd.DataFrame) -> str:
        """Анализ объема"""
        
        volume = df['volume'].tail(20)
        recent_avg = volume.tail(5).mean()
        overall_avg = volume.mean()
        
        if recent_avg > overall_avg * 1.5:
            return 'increasing'
        elif recent_avg < overall_avg * 0.7:
            return 'decreasing'
        else:
            return 'stable'
    
    def _generate_signal(
        self,
        df: pd.DataFrame,
        indicators: Dict,
        trend: str,
        volume_trend: str
    ) -> Tuple[str, float, float, List[str]]:
        """
        Генерация торгового сигнала
        
        Returns:
            (signal_type, strength, confidence, reasons)
        """
        
        reasons = []
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        
        # Текущие значения
        close = df['close'].iloc[-1]
        rsi = indicators['rsi'].iloc[-1]
        macd_signal = indicators['macd_signal']
        bollinger_pos = indicators['bollinger_position']
        
        # 1. RSI Analysis
        total_signals += 1
        if rsi < self.RSI_OVERSOLD:
            bullish_signals += 1
            reasons.append(f"RSI перепродан ({rsi:.1f})")
        elif rsi < self.RSI_EXTREME_OVERSOLD:
            bullish_signals += 2
            reasons.append(f"RSI экстремально перепродан ({rsi:.1f})")
        elif rsi > self.RSI_OVERBOUGHT:
            bearish_signals += 1
            reasons.append(f"RSI перекуплен ({rsi:.1f})")
        elif rsi > self.RSI_EXTREME_OVERBOUGHT:
            bearish_signals += 2
            reasons.append(f"RSI экстремально перекуплен ({rsi:.1f})")
        
        # 2. MACD Analysis
        total_signals += 1
        if macd_signal == 'bullish':
            bullish_signals += 1
            reasons.append("MACD бычий кроссовер")
        else:
            bearish_signals += 1
            reasons.append("MACD медвежий кроссовер")
        
        # 3. Bollinger Bands
        total_signals += 1
        if bollinger_pos == 'lower':
            bullish_signals += 1
            reasons.append("Цена у нижней полосы Боллинджера")
        elif bollinger_pos == 'upper':
            bearish_signals += 1
            reasons.append("Цена у верхней полосы Боллинджера")
        
        # 4. Trend Analysis
        total_signals += 1
        if 'bullish' in trend:
            bullish_signals += 2 if 'strong' in trend else 1
            reasons.append(f"Тренд: {trend}")
        elif 'bearish' in trend:
            bearish_signals += 2 if 'strong' in trend else 1
            reasons.append(f"Тренд: {trend}")
        
        # 5. Volume Confirmation
        total_signals += 1
        if volume_trend == 'increasing':
            if bullish_signals > bearish_signals:
                bullish_signals += 1
                reasons.append("Объем растет (подтверждение)")
            elif bearish_signals > bullish_signals:
                bearish_signals += 1
                reasons.append("Объем растет (давление продаж)")
        
        # 6. Moving Average Crossovers
        sma_20 = indicators['sma_20'].iloc[-1]
        sma_50 = indicators['sma_50'].iloc[-1]
        
        if close > sma_20 and sma_20 > sma_50:
            bullish_signals += 1
            reasons.append("Бычье выравнивание MA")
        elif close < sma_20 and sma_20 < sma_50:
            bearish_signals += 1
            reasons.append("Медвежье выравнивание MA")
        
        # 7. Stochastic
        stoch_k = indicators['stoch_k'].iloc[-1]
        if stoch_k < 20:
            bullish_signals += 1
            reasons.append(f"Stochastic перепродан ({stoch_k:.1f})")
        elif stoch_k > 80:
            bearish_signals += 1
            reasons.append(f"Stochastic перекуплен ({stoch_k:.1f})")
        
        # Определение сигнала
        if bullish_signals > bearish_signals * 1.5:
            signal_type = 'BUY'
            strength = min(100, (bullish_signals / (total_signals + 5)) * 100)
            confidence = min(100, (bullish_signals / (bullish_signals + bearish_signals)) * 100)
        elif bearish_signals > bullish_signals * 1.5:
            signal_type = 'SELL'
            strength = min(100, (bearish_signals / (total_signals + 5)) * 100)
            confidence = min(100, (bearish_signals / (bullish_signals + bearish_signals)) * 100)
        else:
            signal_type = 'HOLD'
            strength = 50
            confidence = 50
            reasons.append("Смешанные сигналы - ожидание")
        
        return signal_type, strength, confidence, reasons
    
    def _check_warnings(self, df: pd.DataFrame, indicators: Dict) -> List[str]:
        """Проверка предупреждений"""
        
        warnings = []
        
        # Дивергенции RSI
        rsi = indicators['rsi'].tail(20)
        close = df['close'].tail(20)
        
        if close.iloc[-1] > close.iloc[-10] and rsi.iloc[-1] < rsi.iloc[-10]:
            warnings.append("⚠️ Медвежья дивергенция RSI")
        elif close.iloc[-1] < close.iloc[-10] and rsi.iloc[-1] > rsi.iloc[-10]:
            warnings.append("⚠️ Бычья дивергенция RSI")
        
        # Низкая волатильность
        atr = indicators['atr'].iloc[-1]
        atr_avg = indicators['atr'].tail(20).mean()
        
        if atr < atr_avg * 0.5:
            warnings.append("⚠️ Низкая волатильность - возможен прорыв")
        
        # Экстремальные значения
        rsi_current = indicators['rsi'].iloc[-1]
        if rsi_current > 90:
            warnings.append("⚠️ RSI > 90 - экстремальная перекупленность")
        elif rsi_current < 10:
            warnings.append("⚠️ RSI < 10 - экстремальная перепроданность")
        
        # Volume spike
        volume = df['volume'].tail(20)
        if volume.iloc[-1] > volume.mean() * 3:
            warnings.append("⚠️ Аномальный всплеск объема")
        
        return warnings
    
    def _extract_current_indicators(self, indicators: Dict) -> Dict:
        """Извлечение текущих значений индикаторов"""
        
        return {
            'rsi': float(indicators['rsi'].iloc[-1]),
            'macd': float(indicators['macd'].iloc[-1]),
            'macd_signal': float(indicators['macd_signal_line'].iloc[-1]),
            'macd_histogram': float(indicators['macd_histogram'].iloc[-1]),
            'adx': float(indicators['adx'].iloc[-1]),
            'sma_20': float(indicators['sma_20'].iloc[-1]),
            'sma_50': float(indicators['sma_50'].iloc[-1]),
            'sma_200': float(indicators['sma_200'].iloc[-1]),
            'stoch_k': float(indicators['stoch_k'].iloc[-1]),
            'stoch_d': float(indicators['stoch_d'].iloc[-1]),
            'bb_upper': float(indicators['bb_upper'].iloc[-1]),
            'bb_middle': float(indicators['bb_middle'].iloc[-1]),
            'bb_lower': float(indicators['bb_lower'].iloc[-1]),
            'atr': float(indicators['atr'].iloc[-1]),
            'vwap': float(indicators['vwap'].iloc[-1]),
            'volume_profile_poc': float(indicators['volume_profile']['poc']),
            'trend_strength': float(indicators['trend_strength'])
        }