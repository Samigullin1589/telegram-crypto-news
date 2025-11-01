"""
INTELLIGENT TRADING SYSTEM v1.0

Полная система для анализа и генерации торговых сигналов:
- Технический анализ (50+ индикаторов)
- Фундаментальный анализ
- ML предсказания
- Hot wallet tracking
- Position tracking
- Performance statistics
"""

from .indicators import TechnicalIndicators
from .technical_analysis import TechnicalAnalyzer
from .fundamental_analysis import FundamentalAnalyzer
from .hot_wallet_tracker import HotWalletTracker
from .ml_predictor import MLPredictor
from .position_tracker import PositionTracker
from .performance_stats import PerformanceStats
from .signal_generator import SignalGenerator

__version__ = "1.0.0"

__all__ = [
    'TechnicalIndicators',
    'TechnicalAnalyzer',
    'FundamentalAnalyzer',
    'HotWalletTracker',
    'MLPredictor',
    'PositionTracker',
    'PerformanceStats',
    'SignalGenerator'
]


def create_trading_system():
    """Factory для создания полной trading системы"""
    return SignalGenerator()