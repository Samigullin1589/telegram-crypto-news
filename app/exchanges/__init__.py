# app/exchanges/__init__.py
"""
EXCHANGE MONITORING MODULE

Мониторинг централизованных и децентрализованных бирж:
- Hyperliquid DEX
- (Future: Binance, OKX, Bybit)
"""

try:
    from app.exchanges.hyperliquid import (
        HyperliquidMonitor,
        HyperliquidWhaleActivity,
        HyperliquidLiquidation,
        HyperliquidFunding,
        HyperliquidMarket
    )
    HYPERLIQUID_AVAILABLE = True
except ImportError:
    HYPERLIQUID_AVAILABLE = False
    HyperliquidMonitor = None


__all__ = [
    'HyperliquidMonitor',
    'HyperliquidWhaleActivity',
    'HyperliquidLiquidation',
    'HyperliquidFunding',
    'HyperliquidMarket',
    'HYPERLIQUID_AVAILABLE'
]