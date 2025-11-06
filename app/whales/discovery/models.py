# app/whales/discovery/models.py
"""
Data models для Discovery Engine
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class TokenData:
    """Модель данных токена"""
    symbol: str
    name: str
    chain: str
    market_cap: float = 0.0
    volume_24h: float = 0.0
    price: float = 0.0
    price_change_24h: float = 0.0
    age_days: int = 0
    added_at: Optional[datetime] = None
    manual: bool = False
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для сериализации"""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'chain': self.chain,
            'market_cap': self.market_cap,
            'volume_24h': self.volume_24h,
            'price': self.price,
            'price_change_24h': self.price_change_24h,
            'age_days': self.age_days,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'manual': self.manual
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TokenData':
        """Создание из словаря"""
        added_at = data.get('added_at')
        if added_at and isinstance(added_at, str):
            added_at = datetime.fromisoformat(added_at)
        
        return cls(
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            chain=data.get('chain', ''),
            market_cap=data.get('market_cap', 0.0),
            volume_24h=data.get('volume_24h', 0.0),
            price=data.get('price', 0.0),
            price_change_24h=data.get('price_change_24h', 0.0),
            age_days=data.get('age_days', 0),
            added_at=added_at,
            manual=data.get('manual', False)
        )


@dataclass
class DiscoveryStats:
    """Статистика Discovery Engine"""
    total_discovered: int = 0
    by_chain: Dict[str, int] = field(default_factory=dict)
    blacklisted: int = 0
    last_refresh: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'total_discovered': self.total_discovered,
            'by_chain': self.by_chain.copy(),
            'blacklisted': self.blacklisted,
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DiscoveryStats':
        """Создание из словаря"""
        last_refresh = data.get('last_refresh')
        if last_refresh and isinstance(last_refresh, str):
            last_refresh = datetime.fromisoformat(last_refresh)
        
        return cls(
            total_discovered=data.get('total_discovered', 0),
            by_chain=data.get('by_chain', {}),
            blacklisted=data.get('blacklisted', 0),
            last_refresh=last_refresh
        )