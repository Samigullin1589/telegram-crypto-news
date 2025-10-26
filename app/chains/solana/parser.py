# app/chains/solana/parser.py
"""
SOLANA CHAIN PARSER

Парсинг Solana транзакций с поддержкой:
- Raydium (AMM + CLMM)
- Orca (Whirlpools)
- Jupiter (Aggregator)
"""

import aiohttp
import base58
from typing import Dict, List, Optional
from datetime import datetime

from app.chains.base import ChainBase, ChainType, TransactionEvent, create_transaction_event


class SolanaChain(ChainBase):
    """
    Solana blockchain parser
    
    Особенности:
    - Использует base58 адреса
    - Транзакции содержат instructions
    - Нужен парсинг account changes
    """
    
    def __init__(self, rpc_urls: List[str], api_key: Optional[str] = None):
        super().__init__(rpc_urls, api_key)
        
        self.chain_type = ChainType.SOLANA
        self.name = "solana"
        self.native_token = "SOL"
        
        # Известные DEX program IDs
        self.known_dexes = {
            # Raydium AMM V4
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            # Raydium CLMM
            "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
            # Orca Whirlpool
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
            # Jupiter Aggregator v6
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter"
        }
    
    # ========================================================================
    # MAIN METHODS
    # ========================================================================
    
    async def parse_transaction(self, tx_hash: str) -> Optional[TransactionEvent]:
        """
        Парсит Solana транзакцию
        
        Args:
            tx_hash: Transaction signature (base58)
        
        Returns:
            TransactionEvent или None
        """
        
        try:
            # Получаем транзакцию через RPC
            tx_data = await self._get_transaction(tx_hash)
            
            if not tx_data:
                return None
            
            # Извлекаем основную информацию
            meta = tx_data.get("meta", {})
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            
            # Проверяем успешность
            if meta.get("err"):
                return None
            
            # Извлекаем accounts
            account_keys = message.get("accountKeys", [])
            
            # Определяем DEX
            dex_name, dex_program_id = self._detect_dex_from_accounts(account_keys)
            
            if not dex_name:
                # Не DEX транзакция
                return None
            
            # Парсим swap
            swap_data = self._parse_swap_from_meta(meta, account_keys, dex_name)
            
            if not swap_data:
                return None
            
            # Получаем timestamp
            block_time = tx_data.get("blockTime")
            timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()
            
            # Создаём событие
            event = create_transaction_event(
                chain="solana",
                tx_hash=tx_hash,
                block_number=tx_data.get("slot", 0),
                from_address=swap_data["user"],
                to_address=dex_program_id,
                dex_name=dex_name,
                dex_address=dex_program_id,
                token_in=swap_data["token_in"],
                token_out=swap_data["token_out"],
                amount_in=swap_data["amount_in"],
                amount_out=swap_data["amount_out"],
                amount_in_usd=swap_data["amount_in_usd"],
                amount_out_usd=swap_data["amount_out_usd"],
                timestamp=timestamp,
                event_type="swap",
                success=True,
                raw_data=tx_data
            )
            
            return event
        
        except Exception as e:
            print(f"❌ Error parsing Solana transaction: {e}")
            return None
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Получает цену Solana токена
        
        Использует Jupiter Price API или CoinGecko
        """
        
        try:
            # Jupiter Price API
            url = f"https://price.jup.ag/v4/price?ids={token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "data" in data and token_address in data["data"]:
                            price_data = data["data"][token_address]
                            return price_data.get("price")
        
        except Exception as e:
            print(f"⚠️  Error getting Solana token price: {e}")
        
        return None
    
    async def get_wallet_balance(
        self, 
        wallet_address: str, 
        token_address: Optional[str] = None
    ) -> float:
        """
        Получает баланс Solana кошелька
        
        Args:
            wallet_address: Solana address (base58)
            token_address: Token mint address (None = SOL)
        """
        
        try:
            if token_address is None:
                # Нативный SOL баланс
                result = await self.call_rpc_with_fallback(
                    "getBalance",
                    [wallet_address]
                )
                
                if result and "value" in result:
                    # Конвертируем lamports в SOL
                    return result["value"] / 1e9
            
            else:
                # Token balance
                result = await self.call_rpc_with_fallback(
                    "getTokenAccountsByOwner",
                    [
                        wallet_address,
                        {"mint": token_address},
                        {"encoding": "jsonParsed"}
                    ]
                )
                
                if result and "value" in result and result["value"]:
                    account = result["value"][0]
                    parsed = account["account"]["data"]["parsed"]["info"]
                    amount = parsed["tokenAmount"]["uiAmount"]
                    return amount
        
        except Exception as e:
            print(f"⚠️  Error getting Solana balance: {e}")
        
        return 0.0
    
    def detect_dex(self, program_id: str) -> Optional[str]:
        """
        Определяет DEX по program ID
        
        Args:
            program_id: Solana program address
        
        Returns:
            Название DEX или None
        """
        return self.known_dexes.get(program_id)
    
    # ========================================================================
    # SOLANA-SPECIFIC METHODS
    # ========================================================================
    
    async def _get_transaction(self, signature: str) -> Optional[Dict]:
        """Получает транзакцию через Solana RPC"""
        
        result = await self.call_rpc_with_fallback(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        )
        
        return result
    
    def _detect_dex_from_accounts(self, account_keys: List[str]) -> tuple:
        """
        Определяет DEX из списка accounts
        
        Returns:
            (dex_name, program_id) или (None, None)
        """
        
        for account in account_keys:
            if isinstance(account, dict):
                # Parsed format
                pubkey = account.get("pubkey", "")
            else:
                # String format
                pubkey = account
            
            dex_name = self.detect_dex(pubkey)
            if dex_name:
                return dex_name, pubkey
        
        return None, None
    
    def _parse_swap_from_meta(
        self, 
        meta: Dict, 
        account_keys: List, 
        dex_name: str
    ) -> Optional[Dict]:
        """
        Парсит swap данные из transaction meta
        
        Solana транзакции содержат изменения балансов в meta.postBalances
        
        Returns:
            {
                "user": str,
                "token_in": str,
                "token_out": str,
                "amount_in": float,
                "amount_out": float,
                "amount_in_usd": float,
                "amount_out_usd": float
            }
        """
        
        # Pre и post token balances
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])
        
        if not pre_balances or not post_balances:
            return None
        
        # Находим изменения
        changes = []
        
        for post in post_balances:
            account_index = post.get("accountIndex")
            mint = post.get("mint")
            post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount", 0))
            
            # Находим соответствующий pre balance
            pre = next((p for p in pre_balances if p.get("accountIndex") == account_index), None)
            
            if pre:
                pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0))
                delta = post_amount - pre_amount
                
                if abs(delta) > 0:
                    changes.append({
                        "account_index": account_index,
                        "mint": mint,
                        "delta": delta
                    })
        
        # Должно быть минимум 2 изменения (token_in уменьшился, token_out увеличился)
        if len(changes) < 2:
            return None
        
        # Определяем token_in (отрицательная дельта) и token_out (положительная)
        token_in_change = next((c for c in changes if c["delta"] < 0), None)
        token_out_change = next((c for c in changes if c["delta"] > 0), None)
        
        if not token_in_change or not token_out_change:
            return None
        
        # User address (обычно первый account)
        user = account_keys[0] if account_keys else "unknown"
        if isinstance(user, dict):
            user = user.get("pubkey", "unknown")
        
        # TODO: Получить реальные цены токенов
        # Пока заглушка
        token_in_price = 1.0
        token_out_price = 1.0
        
        amount_in = abs(token_in_change["delta"])
        amount_out = token_out_change["delta"]
        
        return {
            "user": user,
            "token_in": token_in_change["mint"],
            "token_out": token_out_change["mint"],
            "amount_in": amount_in,
            "amount_out": amount_out,
            "amount_in_usd": amount_in * token_in_price,
            "amount_out_usd": amount_out * token_out_price
        }
    
    # ========================================================================
    # DEX-SPECIFIC PARSERS
    # ========================================================================
    
    def _parse_raydium_swap(self, instructions: List[Dict]) -> Optional[Dict]:
        """Парсит Raydium swap instruction"""
        # TODO: Реализовать специфичный парсинг для Raydium
        pass
    
    def _parse_orca_swap(self, instructions: List[Dict]) -> Optional[Dict]:
        """Парсит Orca swap instruction"""
        # TODO: Реализовать специфичный парсинг для Orca
        pass
    
    def _parse_jupiter_swap(self, instructions: List[Dict]) -> Optional[Dict]:
        """Парсит Jupiter swap instruction"""
        # TODO: Реализовать специфичный парсинг для Jupiter
        pass


# ============================================================================
# SOLANA DEX CLASSES
# ============================================================================

class RaydiumDEX:
    """Raydium AMM"""
    
    PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    
    @staticmethod
    def is_raydium_instruction(instruction: Dict) -> bool:
        """Проверяет является ли instruction Raydium swap"""
        program_id = instruction.get("programId")
        return program_id == RaydiumDEX.PROGRAM_ID


class OrcaDEX:
    """Orca Whirlpools"""
    
    PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
    
    @staticmethod
    def is_orca_instruction(instruction: Dict) -> bool:
        """Проверяет является ли instruction Orca swap"""
        program_id = instruction.get("programId")
        return program_id == OrcaDEX.PROGRAM_ID


class JupiterAggregator:
    """Jupiter Aggregator"""
    
    PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
    
    @staticmethod
    def is_jupiter_instruction(instruction: Dict) -> bool:
        """Проверяет является ли instruction Jupiter swap"""
        program_id = instruction.get("programId")
        return program_id == JupiterAggregator.PROGRAM_ID


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_solana_chain(rpc_urls: List[str] = None) -> SolanaChain:
    """
    Инициализирует Solana chain с дефолтными RPC
    
    Usage:
        from app.chains.solana.parser import initialize_solana_chain
        from app.chains.base import ChainRegistry
        
        solana = initialize_solana_chain()
        ChainRegistry.register("solana", solana)
    """
    
    if rpc_urls is None:
        # Дефолтные public RPC endpoints
        rpc_urls = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
    
    return SolanaChain(rpc_urls)