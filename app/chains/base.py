# app/chains/base.py
"""
BASE CHAIN CLASS

Абстрактный класс для всех блокчейнов.
Определяет единый интерфейс для парсинга и мониторинга.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ChainType(Enum):
    """Типы блокчейнов"""
    EVM = "evm"  # Ethereum, BSC, Polygon, etc
    SOLANA = "solana"
    COSMOS = "cosmos"
    BITCOIN = "bitcoin"


@dataclass
class TransactionEvent:
    """Нормализованное событие транзакции"""
    
    # Базовая информация
    chain: str  # ethereum, solana, base, etc
    tx_hash: str
    block_number: int
    timestamp: datetime
    
    # Участники
    from_address: str
    to_address: Optional[str]
    
    # DEX информация
    dex_name: str  # uniswap, raydium, etc
    dex_address: str
    
    # Токены
    token_in: str  # Адрес или symbol
    token_out: str
    amount_in: float
    amount_out: float
    amount_in_usd: float
    amount_out_usd: float
    
    # Тип события
    event_type: str  # swap, add_liquidity, remove_liquidity
    
    # Дополнительно
    gas_used: Optional[float] = None
    gas_price: Optional[float] = None
    success: bool = True
    raw_data: Optional[Dict] = None
    
    def to_whale_event(self) -> Dict:
        """Конвертация в формат WhaleEvent для системы"""
        return {
            "chain": self.chain,
            "asset": self.token_out,
            "wallet": self.from_address,
            "amount_usd": self.amount_out_usd,
            "tx_hash": self.tx_hash,
            "timestamp": self.timestamp.isoformat(),
            "dex": self.dex_name,
            "type": "buy" if self.amount_out_usd > self.amount_in_usd else "sell"
        }


class ChainBase(ABC):
    """
    Базовый класс для всех блокчейнов
    
    Наследники должны реализовать:
    - parse_transaction()
    - get_token_price()
    - get_wallet_balance()
    - detect_dex()
    """
    
    def __init__(self, rpc_urls: List[str], api_key: Optional[str] = None):
        self.rpc_urls = rpc_urls
        self.api_key = api_key
        self.chain_type = ChainType.EVM  # По умолчанию
        self.name = "unknown"
        self.native_token = "ETH"
        
        # DEX addresses (будут переопределены в наследниках)
        self.known_dexes: Dict[str, str] = {}
    
    # ========================================================================
    # ABSTRACT METHODS (должны быть реализованы)
    # ========================================================================
    
    @abstractmethod
    async def parse_transaction(self, tx_hash: str) -> Optional[TransactionEvent]:
        """
        Парсит транзакцию и возвращает нормализованное событие
        
        Args:
            tx_hash: Hash транзакции
        
        Returns:
            TransactionEvent или None если не удалось распарсить
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Получает цену токена в USD
        
        Args:
            token_address: Адрес токена
        
        Returns:
            Цена в USD или None
        """
        pass
    
    @abstractmethod
    async def get_wallet_balance(self, wallet_address: str, token_address: Optional[str] = None) -> float:
        """
        Получает баланс кошелька
        
        Args:
            wallet_address: Адрес кошелька
            token_address: Адрес токена (None = нативный токен)
        
        Returns:
            Баланс
        """
        pass
    
    @abstractmethod
    def detect_dex(self, to_address: str) -> Optional[str]:
        """
        Определяет DEX по адресу контракта
        
        Args:
            to_address: Адрес контракта
        
        Returns:
            Название DEX или None
        """
        pass
    
    # ========================================================================
    # COMMON METHODS (работают для всех chains)
    # ========================================================================
    
    def normalize_address(self, address: str) -> str:
        """Нормализует адрес к стандартному виду"""
        if self.chain_type == ChainType.EVM:
            # EVM: lowercase с 0x
            return address.lower() if address.startswith('0x') else f"0x{address.lower()}"
        elif self.chain_type == ChainType.SOLANA:
            # Solana: base58
            return address
        else:
            return address
    
    def is_significant_amount(self, amount_usd: float, threshold: float = 10000) -> bool:
        """Проверяет значимость суммы"""
        return amount_usd >= threshold
    
    def calculate_price_impact(self, amount_in_usd: float, amount_out_usd: float) -> float:
        """Рассчитывает price impact"""
        if amount_in_usd == 0:
            return 0
        return abs(amount_out_usd - amount_in_usd) / amount_in_usd
    
    def is_swap_transaction(self, event: TransactionEvent) -> bool:
        """Проверяет является ли транзакция swap"""
        return event.event_type == "swap"
    
    # ========================================================================
    # RPC HELPERS
    # ========================================================================
    
    def get_rpc_url(self, index: int = 0) -> str:
        """Получает RPC URL (с fallback)"""
        if index < len(self.rpc_urls):
            return self.rpc_urls[index]
        return self.rpc_urls[0]
    
    async def call_rpc_with_fallback(self, method: str, params: List = None) -> Optional[Any]:
        """
        Вызывает RPC метод с автоматическим fallback
        
        Пробует все доступные RPC endpoints
        """
        import aiohttp
        
        for i, rpc_url in enumerate(self.rpc_urls):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params or [],
                        "id": 1
                    }
                    
                    async with session.post(rpc_url, json=payload, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data:
                                return data["result"]
                
            except Exception as e:
                print(f"⚠️  RPC #{i+1} failed: {e}")
                continue
        
        print(f"❌ All RPC endpoints failed for {method}")
        return None
    
    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================
    
    async def parse_transactions_batch(self, tx_hashes: List[str]) -> List[TransactionEvent]:
        """
        Парсит несколько транзакций параллельно
        
        Args:
            tx_hashes: Список hash транзакций
        
        Returns:
            Список событий
        """
        import asyncio
        
        tasks = [self.parse_transaction(tx_hash) for tx_hash in tx_hashes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем успешные результаты
        events = []
        for result in results:
            if isinstance(result, TransactionEvent):
                events.append(result)
        
        return events
    
    async def get_token_prices_batch(self, token_addresses: List[str]) -> Dict[str, float]:
        """
        Получает цены нескольких токенов параллельно
        
        Returns:
            {token_address: price_usd}
        """
        import asyncio
        
        tasks = [self.get_token_price(addr) for addr in token_addresses]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for addr, price in zip(token_addresses, prices):
            if isinstance(price, (int, float)) and price is not None:
                result[addr] = price
        
        return result
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def __repr__(self):
        return f"<{self.__class__.__name__} chain={self.name} type={self.chain_type.value}>"


# ============================================================================
# DEX BASE CLASS
# ============================================================================

class DEXBase:
    """
    Базовый класс для DEX
    
    Определяет интерфейс для работы с конкретным DEX
    """
    
    def __init__(self, name: str, router_address: str, factory_address: str):
        self.name = name
        self.router_address = router_address
        self.factory_address = factory_address
    
    def is_this_dex(self, contract_address: str) -> bool:
        """Проверяет принадлежит ли адрес этому DEX"""
        contract_address = contract_address.lower()
        return (
            contract_address == self.router_address.lower() or
            contract_address == self.factory_address.lower()
        )
    
    @abstractmethod
    def parse_swap_event(self, tx_receipt: Dict) -> Optional[Dict]:
        """Парсит swap event из receipt"""
        pass
    
    def __repr__(self):
        return f"<DEX {self.name}>"


# ============================================================================
# CHAIN REGISTRY
# ============================================================================

class ChainRegistry:
    """
    Реестр всех поддерживаемых блокчейнов
    
    Используется для получения нужного chain parser
    """
    
    _chains: Dict[str, ChainBase] = {}
    
    @classmethod
    def register(cls, chain_name: str, chain_instance: ChainBase):
        """Регистрирует chain"""
        cls._chains[chain_name] = chain_instance
        print(f"✅ Registered chain: {chain_name}")
    
    @classmethod
    def get(cls, chain_name: str) -> Optional[ChainBase]:
        """Получает chain по имени"""
        return cls._chains.get(chain_name)
    
    @classmethod
    def get_all(cls) -> Dict[str, ChainBase]:
        """Получает все chains"""
        return cls._chains.copy()
    
    @classmethod
    def list_chains(cls) -> List[str]:
        """Список всех зарегистрированных chains"""
        return list(cls._chains.keys())


# ============================================================================
# HELPERS
# ============================================================================

def create_transaction_event(
    chain: str,
    tx_hash: str,
    block_number: int,
    from_address: str,
    to_address: str,
    dex_name: str,
    dex_address: str,
    token_in: str,
    token_out: str,
    amount_in: float,
    amount_out: float,
    amount_in_usd: float,
    amount_out_usd: float,
    **kwargs
) -> TransactionEvent:
    """Helper для быстрого создания TransactionEvent"""
    
    return TransactionEvent(
        chain=chain,
        tx_hash=tx_hash,
        block_number=block_number,
        timestamp=kwargs.get('timestamp', datetime.utcnow()),
        from_address=from_address,
        to_address=to_address,
        dex_name=dex_name,
        dex_address=dex_address,
        token_in=token_in,
        token_out=token_out,
        amount_in=amount_in,
        amount_out=amount_out,
        amount_in_usd=amount_in_usd,
        amount_out_usd=amount_out_usd,
        event_type=kwargs.get('event_type', 'swap'),
        gas_used=kwargs.get('gas_used'),
        gas_price=kwargs.get('gas_price'),
        success=kwargs.get('success', True),
        raw_data=kwargs.get('raw_data')
    )