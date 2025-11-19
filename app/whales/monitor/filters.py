# app/whales/monitor/filters.py
"""
Event Filtering System
"""

from typing import Dict
from collections import defaultdict

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.addresses import AddressManager


class EventFilter:
    """Фильтрация whale событий"""
    
    def __init__(self):
        self.address_manager = AddressManager()
        self.exchange_addresses = self.address_manager.get_exchange_addresses()
        self.bridge_addresses = self.address_manager.get_bridge_addresses()
        
        self.stats = {
            "events_filtered": defaultdict(int),
            "events_below_threshold": defaultdict(int),
            "events_exchange_filtered": defaultdict(int),
            "events_bridge_filtered": defaultdict(int),
            "events_internal_filtered": defaultdict(int)
        }
    
    def should_filter(self, event: WhaleEvent, chain: str) -> bool:
        """
        Определяет нужно ли фильтровать событие
        
        Returns:
            True если событие нужно отфильтровать
        """
        reasons = []
        
        if self._is_exchange_address(event.from_address):
            reasons.append(f"from_exchange ({event.from_address[:10]}...)")
            self.stats["events_exchange_filtered"][chain] += 1
        
        if self._is_exchange_address(event.to_address):
            reasons.append(f"to_exchange ({event.to_address[:10]}...)")
            self.stats["events_exchange_filtered"][chain] += 1
        
        if not event.dex and event.is_bridge:
            reasons.append("bridge_transfer")
            self.stats["events_bridge_filtered"][chain] += 1
        
        if event.is_internal:
            reasons.append("internal_transfer")
            self.stats["events_internal_filtered"][chain] += 1

        # ИСПРАВЛЕНО: Безопасный доступ к config.features.whale.min_usd_threshold
        _features = getattr(config, 'features', None)
        _whale = getattr(_features, 'whale', None) if _features else None
        min_threshold = getattr(_whale, 'min_usd_threshold', 50000) if _whale else 50000

        if event.amount_usd < min_threshold:
            reasons.append(f"below_threshold (${event.amount_usd:,.2f} < ${min_threshold:,.0f})")
            self.stats["events_below_threshold"][chain] += 1
        
        if reasons:
            print(f"🚫 [FILTER] {chain} - Событие отфильтровано:")
            print(f"   TX: {event.tx_hash[:16]}...")
            print(f"   Amount: ${event.amount_usd:,.2f}")
            print(f"   Reasons: {', '.join(reasons)}")
            self.stats["events_filtered"][chain] += 1
            return True
        
        return False
    
    def _is_exchange_address(self, address: str) -> bool:
        """Проверяет является ли адрес биржей"""
        return address.lower() in self.exchange_addresses
    
    def _is_bridge_address(self, address: str) -> bool:
        """Проверяет является ли адрес мостом"""
        return address.lower() in self.bridge_addresses
    
    def get_stats(self) -> Dict:
        """Возвращает статистику фильтрации"""
        return {
            "events_filtered": dict(self.stats["events_filtered"]),
            "events_below_threshold": dict(self.stats["events_below_threshold"]),
            "events_exchange_filtered": dict(self.stats["events_exchange_filtered"]),
            "events_bridge_filtered": dict(self.stats["events_bridge_filtered"]),
            "events_internal_filtered": dict(self.stats["events_internal_filtered"])
        }