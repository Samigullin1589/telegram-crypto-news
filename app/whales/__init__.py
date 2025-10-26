# app/whales/__init__.py
"""
WHALE MONITORING SYSTEM

Модуль для мониторинга крупных перемещений криптовалют (китов)
"""

__version__ = "3.0.0"
__all__ = [
    "DiscoveryEngine",
    "BlockchainMonitor", 
    "WhaleEvent",
    "EventScorer",
    "PriceProvider",
    "NewsGate",
    "WhalePublisher",
    "HistoryManager"
]