# app/whales/monitor/__init__.py
"""
Blockchain Monitor System v5.0
Модульная мультичейн система мониторинга whale событий
"""

from app.whales.monitor.core import BlockchainMonitor
from app.whales.monitor.evm_provider import EVMProvider
from app.whales.monitor.solana_provider import SolanaProvider
from app.whales.monitor.dex_detector import DEXDetector

__all__ = [
    'BlockchainMonitor',
    'EVMProvider',
    'SolanaProvider',
    'DEXDetector'
]

__version__ = '5.0.0'