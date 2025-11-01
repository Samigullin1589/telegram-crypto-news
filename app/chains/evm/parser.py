# app/chains/evm/parser.py
"""
EVM CHAIN PARSER - FIXED VERSION

Универсальный парсер для всех EVM-совместимых блокчейнов:
- Ethereum
- BSC
- Base
- Arbitrum
- Optimism
- Avalanche C-Chain
- Polygon

ИСПРАВЛЕНИЯ:
✅ Правильные API URLs (без двойных слешей)
✅ datetime.utcnow() → datetime.now(timezone.utc)
✅ Добавлена обработка ошибок
"""

import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timezone
from web3 import Web3

from app.chains.base import ChainBase, ChainType, TransactionEvent, create_transaction_event


class EVMChain(ChainBase):
    """
    Универсальный EVM chain parser
    
    Работает с любым EVM-совместимым блокчейном
    """
    
    def __init__(
        self, 
        name: str,
        rpc_urls: List[str],
        explorer_api_url: str,
        explorer_api_key: Optional[str] = None,
        native_token: str = "ETH",
        chain_id: int = 1
    ):
        super().__init__(rpc_urls, explorer_api_key)
        
        self.chain_type = ChainType.EVM
        self.name = name
        self.native_token = native_token
        self.chain_id = chain_id
        self.explorer_api_url = explorer_api_url
        
        # Web3 instance
        self.w3 = Web3(Web3.HTTPProvider(self.get_rpc_url()))
        
        # Uniswap V2/V3 Swap event signatures
        self.SWAP_V2_SIGNATURE = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
        self.SWAP_V3_SIGNATURE = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
        
        # DEXes будут установлены в наследниках
        self.known_dexes: Dict[str, str] = {}
    
    # ========================================================================
    # MAIN METHODS
    # ========================================================================
    
    async def parse_transaction(self, tx_hash: str) -> Optional[TransactionEvent]:
        """
        Парсит EVM транзакцию
        
        Args:
            tx_hash: Transaction hash (0x...)
        
        Returns:
            TransactionEvent или None
        """
        
        try:
            # Получаем transaction и receipt
            tx = await self._get_transaction(tx_hash)
            receipt = await self._get_transaction_receipt(tx_hash)
            
            if not tx or not receipt:
                return None
            
            # Проверяем успешность
            if receipt.get("status") != 1:
                return None
            
            # Определяем DEX
            to_address = tx.get("to", "").lower()
            dex_name = self.detect_dex(to_address)
            
            if not dex_name:
                # Не DEX транзакция
                return None
            
            # Парсим swap events из logs
            swap_data = self._parse_swap_from_logs(receipt.get("logs", []))
            
            if not swap_data:
                return None
            
            # Получаем timestamp (ИСПРАВЛЕНО: datetime.now(timezone.utc))
            block = await self._get_block(tx.get("blockNumber"))
            timestamp = datetime.fromtimestamp(block.get("timestamp", 0), tz=timezone.utc) if block else datetime.now(timezone.utc)
            
            # Создаём событие
            event = create_transaction_event(
                chain=self.name,
                tx_hash=tx_hash,
                block_number=int(tx.get("blockNumber", 0), 16),
                from_address=tx.get("from", ""),
                to_address=to_address,
                dex_name=dex_name,
                dex_address=to_address,
                token_in=swap_data["token_in"],
                token_out=swap_data["token_out"],
                amount_in=swap_data["amount_in"],
                amount_out=swap_data["amount_out"],
                amount_in_usd=swap_data["amount_in_usd"],
                amount_out_usd=swap_data["amount_out_usd"],
                timestamp=timestamp,
                event_type="swap",
                gas_used=int(receipt.get("gasUsed", "0"), 16),
                success=True,
                raw_data={"tx": tx, "receipt": receipt}
            )
            
            return event
        
        except Exception as e:
            print(f"❌ Error parsing {self.name} transaction: {e}")
            return None
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Получает цену токена через CoinGecko или DEX
        
        Args:
            token_address: Token contract address
        
        Returns:
            Price in USD
        """
        
        try:
            # Пробуем CoinGecko
            # Маппинг chain -> platform
            platform_id = self._get_coingecko_platform()
            
            if platform_id:
                url = f"https://api.coingecko.com/api/v3/simple/token_price/{platform_id}"
                params = {
                    "contract_addresses": token_address.lower(),
                    "vs_currencies": "usd"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            token_data = data.get(token_address.lower(), {})
                            return token_data.get("usd")
        
        except Exception as e:
            print(f"⚠️  Error getting token price: {e}")
        
        return None
    
    async def get_wallet_balance(
        self, 
        wallet_address: str, 
        token_address: Optional[str] = None
    ) -> float:
        """
        Получает баланс кошелька
        
        Args:
            wallet_address: Wallet address
            token_address: Token contract (None = native token)
        
        Returns:
            Balance
        """
        
        try:
            if token_address is None:
                # Native token (ETH, BNB, etc)
                result = await self.call_rpc_with_fallback(
                    "eth_getBalance",
                    [wallet_address, "latest"]
                )
                
                if result:
                    # Convert from wei to token
                    return int(result, 16) / 1e18
            
            else:
                # ERC20 token
                # balanceOf(address) = 0x70a08231 + address (32 bytes)
                data = "0x70a08231" + wallet_address[2:].zfill(64)
                
                result = await self.call_rpc_with_fallback(
                    "eth_call",
                    [{"to": token_address, "data": data}, "latest"]
                )
                
                if result:
                    balance = int(result, 16)
                    # TODO: Get token decimals
                    return balance / 1e18
        
        except Exception as e:
            print(f"⚠️  Error getting balance: {e}")
        
        return 0.0
    
    def detect_dex(self, contract_address: str) -> Optional[str]:
        """
        Определяет DEX по адресу контракта
        
        Args:
            contract_address: Contract address
        
        Returns:
            DEX name or None
        """
        contract_address = contract_address.lower()
        return self.known_dexes.get(contract_address)
    
    # ========================================================================
    # EVM-SPECIFIC METHODS
    # ========================================================================
    
    async def _get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Получает транзакцию через RPC"""
        return await self.call_rpc_with_fallback("eth_getTransactionByHash", [tx_hash])
    
    async def _get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Получает receipt транзакции"""
        return await self.call_rpc_with_fallback("eth_getTransactionReceipt", [tx_hash])
    
    async def _get_block(self, block_number: int) -> Optional[Dict]:
        """
        Получает блок по номеру
        
        Args:
            block_number: Block number (hex or int)
        
        Returns:
            Block data
        """
        
        # Конвертируем в hex если нужно
        if isinstance(block_number, int):
            block_number = hex(block_number)
        
        return await self.call_rpc_with_fallback("eth_getBlockByNumber", [block_number, False])
    
    def _parse_swap_from_logs(self, logs: List[Dict]) -> Optional[Dict]:
        """
        Парсит Swap event из логов транзакции
        
        Args:
            logs: Transaction logs
        
        Returns:
            Swap data или None
        """
        
        for log in logs:
            topics = log.get("topics", [])
            
            if not topics:
                continue
            
            # Проверяем Swap signature
            if topics[0].lower() in [self.SWAP_V2_SIGNATURE.lower(), self.SWAP_V3_SIGNATURE.lower()]:
                # Нашли Swap event
                
                # TODO: Декодировать amounts из data
                # Это требует знания ABI и token decimals
                
                # Пока возвращаем заглушку
                return {
                    "token_in": "0x0000000000000000000000000000000000000000",
                    "token_out": log.get("address", ""),
                    "amount_in": 1000.0,
                    "amount_out": 1000.0,
                    "amount_in_usd": 1000.0,
                    "amount_out_usd": 1000.0
                }
        
        return None
    
    def _get_coingecko_platform(self) -> Optional[str]:
        """Получает CoinGecko platform ID для chain"""
        
        platform_mapping = {
            "ethereum": "ethereum",
            "bsc": "binance-smart-chain",
            "base": "base",
            "arbitrum": "arbitrum-one",
            "optimism": "optimistic-ethereum",
            "avalanche": "avalanche",
            "polygon": "polygon-pos"
        }
        
        return platform_mapping.get(self.name)


# ============================================================================
# SPECIFIC CHAIN CLASSES
# ============================================================================

class BaseChain(EVMChain):
    """Base (Coinbase L2)"""
    
    def __init__(self, rpc_urls: List[str] = None, api_key: Optional[str] = None):
        if rpc_urls is None:
            rpc_urls = [
                "https://mainnet.base.org",
                "https://base.llamarpc.com",
                "https://base-mainnet.public.blastapi.io"
            ]
        
        super().__init__(
            name="base",
            rpc_urls=rpc_urls,
            explorer_api_url="https://api.basescan.org/api",  # ✅ ИСПРАВЛЕНО: правильный URL
            explorer_api_key=api_key,
            native_token="ETH",
            chain_id=8453
        )
        
        # Base DEXes
        self.known_dexes = {
            "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V3",
            "0x327df1e6de05895d2ab08513aadd9313fe505d86": "Aerodrome",
            "0x8909dc15e40173ff4699343b6eb8132c65e18ec6": "BaseSwap"
        }


class ArbitrumChain(EVMChain):
    """Arbitrum One"""
    
    def __init__(self, rpc_urls: List[str] = None, api_key: Optional[str] = None):
        if rpc_urls is None:
            rpc_urls = [
                "https://arb1.arbitrum.io/rpc",
                "https://arbitrum.llamarpc.com",
                "https://rpc.ankr.com/arbitrum"
            ]
        
        super().__init__(
            name="arbitrum",
            rpc_urls=rpc_urls,
            explorer_api_url="https://api.arbiscan.io/api",  # ✅ ИСПРАВЛЕНО: правильный URL
            explorer_api_key=api_key,
            native_token="ETH",
            chain_id=42161
        )
        
        # Arbitrum DEXes
        self.known_dexes = {
            "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
            "0xc873fecbd354f5a56e00e710b90ef4201db2448d": "Camelot",
            "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap",
            "0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a": "GMX"
        }


class OptimismChain(EVMChain):
    """Optimism"""
    
    def __init__(self, rpc_urls: List[str] = None, api_key: Optional[str] = None):
        if rpc_urls is None:
            rpc_urls = [
                "https://mainnet.optimism.io",
                "https://optimism.llamarpc.com",
                "https://rpc.ankr.com/optimism"
            ]
        
        super().__init__(
            name="optimism",
            rpc_urls=rpc_urls,
            explorer_api_url="https://api-optimistic.etherscan.io/api",  # ✅ ИСПРАВЛЕНО: правильный URL
            explorer_api_key=api_key,
            native_token="ETH",
            chain_id=10
        )
        
        # Optimism DEXes
        self.known_dexes = {
            "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
            "0x9c12939390052919af3155f41bf4160fd3666a6f": "Velodrome",
            "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
        }


class AvalancheChain(EVMChain):
    """Avalanche C-Chain"""
    
    def __init__(self, rpc_urls: List[str] = None, api_key: Optional[str] = None):
        if rpc_urls is None:
            rpc_urls = [
                "https://api.avax.network/ext/bc/C/rpc",
                "https://avalanche.public-rpc.com",
                "https://rpc.ankr.com/avalanche"
            ]
        
        super().__init__(
            name="avalanche",
            rpc_urls=rpc_urls,
            explorer_api_url="https://api.snowtrace.io/api",  # ✅ ИСПРАВЛЕНО: правильный URL
            explorer_api_key=api_key,
            native_token="AVAX",
            chain_id=43114
        )
        
        # Avalanche DEXes
        self.known_dexes = {
            "0x60ae616a2155ee3d9a68541ba4544862310933d4": "Trader Joe",
            "0xe54ca86531e17ef3616d22ca28b0d458b6c89106": "Pangolin",
            "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
        }


class PolygonChain(EVMChain):
    """Polygon PoS"""
    
    def __init__(self, rpc_urls: List[str] = None, api_key: Optional[str] = None):
        if rpc_urls is None:
            rpc_urls = [
                "https://polygon.llamarpc.com",
                "https://polygon-mainnet.public.blastapi.io",
                "https://polygon.blockpi.network/v1/rpc/public",
                "https://polygon-bor.publicnode.com",
                "https://rpc.ankr.com/polygon",
                "https://polygon.rpc.blxrbdn.com",
                "https://rpc-mainnet.matic.network",
                "https://polygon-rpc.com"
            ]
        
        super().__init__(
            name="polygon",
            rpc_urls=rpc_urls,
            explorer_api_url="https://api.polygonscan.com/api",  # ✅ ИСПРАВЛЕНО: правильный URL
            explorer_api_key=api_key,
            native_token="MATIC",
            chain_id=137
        )
        
        # Polygon DEXes
        self.known_dexes = {
            "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
            "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff": "QuickSwap",
            "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap",
            "0xba12222222228d8ba445958a75a0704d566bf2c8": "Balancer"
        }


# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_base_chain(api_key: Optional[str] = None) -> BaseChain:
    """Инициализирует Base chain"""
    return BaseChain(api_key=api_key)


def initialize_arbitrum_chain(api_key: Optional[str] = None) -> ArbitrumChain:
    """Инициализирует Arbitrum chain"""
    return ArbitrumChain(api_key=api_key)


def initialize_optimism_chain(api_key: Optional[str] = None) -> OptimismChain:
    """Инициализирует Optimism chain"""
    return OptimismChain(api_key=api_key)


def initialize_avalanche_chain(api_key: Optional[str] = None) -> AvalancheChain:
    """Инициализирует Avalanche chain"""
    return AvalancheChain(api_key=api_key)


def initialize_polygon_chain(api_key: Optional[str] = None) -> PolygonChain:
    """Инициализирует Polygon chain"""
    return PolygonChain(api_key=api_key)


def initialize_all_evm_chains(api_keys: Optional[Dict[str, str]] = None) -> Dict[str, EVMChain]:
    """
    Инициализирует все EVM chains
    
    Args:
        api_keys: {"base": "...", "arbitrum": "...", ...}
    
    Returns:
        {"base": BaseChain, "arbitrum": ArbitrumChain, ...}
    """
    
    api_keys = api_keys or {}
    
    return {
        "base": initialize_base_chain(api_keys.get("base")),
        "arbitrum": initialize_arbitrum_chain(api_keys.get("arbitrum")),
        "optimism": initialize_optimism_chain(api_keys.get("optimism")),
        "avalanche": initialize_avalanche_chain(api_keys.get("avalanche")),
        "polygon": initialize_polygon_chain(api_keys.get("polygon"))
    }