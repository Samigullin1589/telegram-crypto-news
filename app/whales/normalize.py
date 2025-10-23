# app/whales/normalize.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class AddressLabel:
    """Метка адреса (биржа, фонд, кастоди и т.д.)"""
    provider: str  # etherscan, helius, manual
    name: str  # exchange, fund, custodian, mm, unknown, bridge, internal
    confidence: int  # 0-100
    details: Optional[str] = None  # например, "Binance Hot Wallet 8"

@dataclass
class ClusterInfo:
    """Информация о кластере транзакций"""
    tx_in_window: int
    window_minutes: int
    related_txs: List[str] = field(default_factory=list)

@dataclass
class MarketInfo:
    """Рыночные данные актива"""
    price: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    price_change_1h: Optional[float] = None
    price_change_4h: Optional[float] = None
    price_change_24h: Optional[float] = None

@dataclass
class HistoryHint:
    """Подсказка 'в прошлый раз'"""
    d1h: Optional[float] = None  # delta % через 1 час
    d4h: Optional[float] = None  # delta % через 4 часа
    d24h: Optional[float] = None  # delta % через 24 часа
    comparable_ts: Optional[str] = None  # ISO timestamp сравниваемого события

@dataclass
class WhaleEvent:
    """Единое представление события перемещения"""
    # Основные данные
    asset: str  # BTC, ETH, SOL, USDT и т.д.
    amount_native: float  # количество в нативных единицах
    amount_usd: float  # оценка в USD
    chain: str  # bitcoin, ethereum, solana, tron, bsc, polygon, arbitrum, base, avalanche
    
    # Направление и классификация
    direction: str  # inflow_to_exchange, outflow_to_cold, bridge, internal, unknown
    phase: str  # activation, transfer_cluster, deposit_confirmed, execution
    
    # Транзакция
    tx_hash: str
    from_address: str
    to_address: str
    
    # Метки адресов
    labels: Dict[str, List[AddressLabel]] = field(default_factory=lambda: {"from": [], "to": []})
    
    # Кластер
    cluster: Optional[ClusterInfo] = None
    
    # Рыночные данные
    market: MarketInfo = field(default_factory=MarketInfo)
    
    # История
    history_hint: HistoryHint = field(default_factory=HistoryHint)
    
    # Ссылки
    links: Dict[str, str] = field(default_factory=dict)
    
    # Временные метки
    tx_time_utc: datetime = field(default_factory=datetime.utcnow)
    detected_at_utc: datetime = field(default_factory=datetime.utcnow)
    
    # Метаданные
    min_usd_threshold: float = 0.0  # какой порог применялся
    is_internal: bool = False
    is_bridge: bool = False
    is_reorg: bool = False
    
    def to_dict(self) -> dict:
        """Конвертация в dict для JSON сериализации"""
        return {
            "asset": self.asset,
            "amount_native": self.amount_native,
            "amount_usd": self.amount_usd,
            "chain": self.chain,
            "direction": self.direction,
            "phase": self.phase,
            "tx_hash": self.tx_hash,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "labels": {
                "from": [{"provider": l.provider, "name": l.name, "confidence": l.confidence, "details": l.details} for l in self.labels.get("from", [])],
                "to": [{"provider": l.provider, "name": l.name, "confidence": l.confidence, "details": l.details} for l in self.labels.get("to", [])]
            },
            "cluster": {
                "tx_in_window": self.cluster.tx_in_window,
                "window_minutes": self.cluster.window_minutes,
                "related_txs": self.cluster.related_txs
            } if self.cluster else None,
            "market": {
                "price": self.market.price,
                "volume_24h_usd": self.market.volume_24h_usd,
                "price_change_1h": self.market.price_change_1h,
                "price_change_4h": self.market.price_change_4h,
                "price_change_24h": self.market.price_change_24h
            },
            "history_hint": {
                "d1h": self.history_hint.d1h,
                "d4h": self.history_hint.d4h,
                "d24h": self.history_hint.d24h,
                "comparable_ts": self.history_hint.comparable_ts
            },
            "links": self.links,
            "timestamps": {
                "tx_time_utc": self.tx_time_utc.isoformat(),
                "detected_at_utc": self.detected_at_utc.isoformat()
            },
            "limits": {
                "min_usd": self.min_usd_threshold
            }
        }
    
    def get_dedup_key(self) -> str:
        """Ключ для дедупликации: (chain, tx_hash, from, to, округлённое время)"""
        # Округляем до 2 минут
        rounded_ts = int(self.tx_time_utc.timestamp() // 120) * 120
        return f"{self.chain}:{self.tx_hash}:{self.from_address}:{self.to_address}:{rounded_ts}"