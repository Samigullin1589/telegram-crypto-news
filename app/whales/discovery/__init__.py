# app/whales/discovery/__init__.py
"""
DISCOVERY ENGINE v3.0

Интеллектуальное обнаружение топ-токенов для мониторинга
"""

from app.whales.discovery.engine import DiscoveryEngine
from app.whales.discovery.models import TokenData, DiscoveryStats

__all__ = ['DiscoveryEngine', 'TokenData', 'DiscoveryStats']


def create_discovery_engine() -> DiscoveryEngine:
    """Создает instance Discovery Engine"""
    return DiscoveryEngine()