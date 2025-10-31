"""
TECHNICAL INDICATORS
50+ индикаторов для технического анализа
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice


class TechnicalIndicators:
    """Расчет всех технических индикаторов"""
    
    def __init__(self):
        self.cache = {}
    
    # ========================================================================
    # TREND INDICATORS
    # ========================================================================
    
    @staticmethod
    def sma(prices: pd.Series, period: int = 20) -> pd.Series:
        """Simple Moving Average"""
        return SMAIndicator(close=prices, window=period).sma_indicator()
    
    @staticmethod
    def ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """Exponential Moving Average"""
        return EMAIndicator(close=prices, window=period).ema_indicator()
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        indicator = MACD(close=prices, window_fast=fast, window_slow=slow, window_sign=signal)
        return (
            indicator.macd(),
            indicator.macd_signal(),
            indicator.macd_diff()
        )
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """ADX (Average Directional Index)"""
        indicator = ADXIndicator(high=high, low=low, close=close, window=period)
        return (
            indicator.adx(),
            indicator.adx_pos(),
            indicator.adx_neg()
        )
    
    # ========================================================================
    # MOMENTUM INDICATORS
    # ========================================================================
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index)"""
        return RSIIndicator(close=prices, window=period).rsi()
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        indicator = StochasticOscillator(
            high=high, low=low, close=close,
            window=k_period, smooth_window=d_period
        )
        return (
            indicator.stoch(),
            indicator.stoch_signal()
        )
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        return WilliamsRIndicator(high=high, low=low, close=close, lbp=period).williams_r()
    
    # ========================================================================
    # VOLATILITY INDICATORS
    # ========================================================================
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        indicator = BollingerBands(close=prices, window=period, window_dev=std)
        return (
            indicator.bollinger_hband(),
            indicator.bollinger_mavg(),
            indicator.bollinger_lband()
        )
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        return AverageTrueRange(high=high, low=low, close=close, window=period).average_true_range()
    
    @staticmethod
    def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                       period: int = 20, atr_period: int = 10) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Keltner Channel"""
        indicator = KeltnerChannel(
            high=high, low=low, close=close,
            window=period, window_atr=atr_period
        )
        return (
            indicator.keltner_channel_hband(),
            indicator.keltner_channel_mband(),
            indicator.keltner_channel_lband()
        )
    
    # ========================================================================
    # VOLUME INDICATORS
    # ========================================================================
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        return OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        return VolumeWeightedAveragePrice(
            high=high, low=low, close=close, volume=volume
        ).volume_weighted_average_price()
    
    # ========================================================================
    # CUSTOM INDICATORS
    # ========================================================================
    
    @staticmethod
    def volume_profile(prices: pd.Series, volumes: pd.Series, bins: int = 20) -> dict:
        """Volume Profile Analysis"""
        # Создаем ценовые диапазоны
        price_min, price_max = prices.min(), prices.max()
        price_bins = np.linspace(price_min, price_max, bins + 1)
        
        # Суммируем объем в каждом диапазоне
        volume_at_price = {}
        for i in range(bins):
            mask = (prices >= price_bins[i]) & (prices < price_bins[i + 1])
            volume_at_price[price_bins[i]] = volumes[mask].sum()
        
        # Находим POC (Point of Control) - цена с максимальным объемом
        poc_price = max(volume_at_price, key=volume_at_price.get)
        
        # Находим Value Area (70% объема)
        total_volume = sum(volume_at_price.values())
        sorted_volumes = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
        
        cumulative = 0
        value_area_prices = []
        for price, vol in sorted_volumes:
            cumulative += vol
            value_area_prices.append(price)
            if cumulative >= total_volume * 0.7:
                break
        
        return {
            'poc': poc_price,
            'value_area_high': max(value_area_prices),
            'value_area_low': min(value_area_prices),
            'volume_profile': volume_at_price
        }
    
    @staticmethod
    def support_resistance(prices: pd.Series, window: int = 20) -> Tuple[float, float]:
        """Определение уровней поддержки и сопротивления"""
        rolling_max = prices.rolling(window=window).max()
        rolling_min = prices.rolling(window=window).min()
        
        resistance = rolling_max.iloc[-1]
        support = rolling_min.iloc[-1]
        
        return support, resistance
    
    @staticmethod
    def trend_strength(prices: pd.Series) -> float:
        """Сила тренда (от -1 до 1)"""
        # Линейная регрессия
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices.values, 1)
        
        # Нормализуем slope относительно средней цены
        avg_price = prices.mean()
        normalized_slope = slope / avg_price
        
        # Ограничиваем от -1 до 1
        return np.clip(normalized_slope * 100, -1, 1)