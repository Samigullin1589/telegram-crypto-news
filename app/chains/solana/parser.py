"""
SOLANA CHAIN PARSER v2.0 - PRODUCTION READY

Парсинг Solana транзакций с поддержкой:
- Raydium (AMM V4 + CLMM)
- Orca (Whirlpools)
- Jupiter (Aggregator v6)
- Meteora
- Phoenix

Интегрирован с SolanaRpcManager для решения проблемы 429 ошибок
"""

import aiohttp
import base58
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import struct
from collections import defaultdict
import json

from app.chains.base import ChainBase, ChainType, TransactionEvent, create_transaction_event
from app.chains.solana.rpc_manager import get_rpc_manager, RequestPriority

logger = logging.getLogger(__name__)


class SolanaChain(ChainBase):
    """
    Solana blockchain parser с продвинутым RPC management
    
    Особенности:
    - Использует base58 адреса
    - Транзакции содержат instructions
    - Парсинг account changes через pre/post balances
    - Поддержка всех major DEX
    - Интеграция с RPC Manager для устойчивости к rate limiting
    """
    
    def __init__(self, rpc_urls: List[str], api_key: Optional[str] = None):
        super().__init__(rpc_urls, api_key)
        
        self.chain_type = ChainType.SOLANA
        self.name = "solana"
        self.native_token = "SOL"
        
        self.rpc_manager = None
        
        # Известные DEX program IDs
        self.known_dexes = {
            # Raydium AMM V4
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            # Raydium CLMM
            "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
            # Orca Whirlpool
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
            # Jupiter Aggregator v6
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter",
            # Jupiter v4
            "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter v4",
            # Meteora
            "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora",
            # Phoenix
            "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": "Phoenix",
            # Lifinity
            "EewxydAPCCVuNEyrVN68PuSYdQ7wKn27V9Gjeoi8dy3S": "Lifinity",
        }
        
        # Token program ID
        self.token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        
        # Кэш для token metadata
        self.token_metadata_cache: Dict[str, Dict] = {}
        self.metadata_cache_ttl = timedelta(hours=1)
        
        # Кэш для цен
        self.price_cache: Dict[str, Tuple[float, datetime]] = {}
        self.price_cache_ttl = timedelta(minutes=5)
        
        # Known token addresses
        self.known_tokens = {
            "So11111111111111111111111111111111111111112": {
                "symbol": "SOL",
                "name": "Wrapped SOL",
                "decimals": 9,
                "coingecko_id": "solana"
            },
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {
                "symbol": "USDC",
                "name": "USD Coin",
                "decimals": 6,
                "coingecko_id": "usd-coin"
            },
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": {
                "symbol": "USDT",
                "name": "Tether USD",
                "decimals": 6,
                "coingecko_id": "tether"
            },
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": {
                "symbol": "mSOL",
                "name": "Marinade staked SOL",
                "decimals": 9,
                "coingecko_id": "msol"
            },
            "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": {
                "symbol": "stSOL",
                "name": "Lido Staked SOL",
                "decimals": 9,
                "coingecko_id": "lido-staked-sol"
            },
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": {
                "symbol": "ETH",
                "name": "Wrapped Ethereum",
                "decimals": 8,
                "coingecko_id": "ethereum"
            },
            "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E": {
                "symbol": "BTC",
                "name": "Wrapped Bitcoin",
                "decimals": 6,
                "coingecko_id": "bitcoin"
            },
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {
                "symbol": "BONK",
                "name": "Bonk",
                "decimals": 5,
                "coingecko_id": "bonk"
            },
            "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": {
                "symbol": "JUP",
                "name": "Jupiter",
                "decimals": 6,
                "coingecko_id": "jupiter-exchange-solana"
            }
        }
        
        logger.info("✅ SolanaChain инициализирован")
    
    async def initialize(self):
        """Инициализация RPC manager"""
        if self.rpc_manager is None:
            self.rpc_manager = await get_rpc_manager(self.rpc_urls)
            logger.info("✅ RPC Manager подключен к SolanaChain")
    
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
        
        await self.initialize()
        
        try:
            # Получаем транзакцию через RPC Manager
            tx_data = await self._get_transaction(tx_hash)
            
            if not tx_data:
                logger.warning(f"⚠️ Транзакция {tx_hash} не найдена")
                return None
            
            # Извлекаем основную информацию
            meta = tx_data.get("meta", {})
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            
            # Проверяем успешность
            if meta.get("err"):
                logger.debug(f"⚠️ Транзакция {tx_hash} неуспешна: {meta.get('err')}")
                return None
            
            # Извлекаем accounts
            account_keys = message.get("accountKeys", [])
            
            # Определяем DEX
            dex_name, dex_program_id = self._detect_dex_from_accounts(account_keys)
            
            if not dex_name:
                logger.debug(f"⚠️ Транзакция {tx_hash} не является DEX транзакцией")
                return None
            
            # Парсим swap в зависимости от DEX
            swap_data = None
            
            if "Raydium" in dex_name:
                swap_data = await self._parse_raydium_swap(meta, message, account_keys)
            elif dex_name == "Orca":
                swap_data = await self._parse_orca_swap(meta, message, account_keys)
            elif "Jupiter" in dex_name:
                swap_data = await self._parse_jupiter_swap(meta, message, account_keys)
            elif dex_name == "Meteora":
                swap_data = await self._parse_meteora_swap(meta, message, account_keys)
            else:
                # Generic swap parser
                swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if not swap_data:
                logger.debug(f"⚠️ Не удалось распарсить swap данные для {tx_hash}")
                return None
            
            # Получаем timestamp
            block_time = tx_data.get("blockTime")
            timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()
            
            # Получаем информацию о токенах
            token_in_info = await self._get_token_info(swap_data["token_in"])
            token_out_info = await self._get_token_info(swap_data["token_out"])
            
            # Получаем цены токенов
            token_in_price = await self.get_token_price(swap_data["token_in"])
            token_out_price = await self.get_token_price(swap_data["token_out"])
            
            # Рассчитываем USD amounts
            amount_in_usd = swap_data["amount_in"] * (token_in_price or 0)
            amount_out_usd = swap_data["amount_out"] * (token_out_price or 0)
            
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
                amount_in_usd=amount_in_usd,
                amount_out_usd=amount_out_usd,
                timestamp=timestamp,
                event_type="swap",
                success=True,
                raw_data={
                    "slot": tx_data.get("slot"),
                    "token_in_symbol": token_in_info.get("symbol", "UNKNOWN"),
                    "token_out_symbol": token_out_info.get("symbol", "UNKNOWN"),
                    "token_in_decimals": token_in_info.get("decimals", 9),
                    "token_out_decimals": token_out_info.get("decimals", 9),
                    "fee": meta.get("fee", 0) / 1e9
                }
            )
            
            logger.info(f"✅ Распарсена {dex_name} транзакция: {tx_hash[:16]}...")
            
            return event
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Solana транзакции {tx_hash}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """
        Получает цену Solana токена
        
        Использует Jupiter Price API с fallback на CoinGecko
        """
        
        # Проверяем кэш
        if token_address in self.price_cache:
            price, cached_at = self.price_cache[token_address]
            if datetime.utcnow() - cached_at < self.price_cache_ttl:
                return price
        
        price = None
        
        try:
            # Метод 1: Jupiter Price API (быстрый и надёжный)
            url = f"https://price.jup.ag/v6/price?ids={token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "data" in data and token_address in data["data"]:
                            price_data = data["data"][token_address]
                            price = price_data.get("price")
        
        except Exception as e:
            logger.debug(f"⚠️ Jupiter Price API недоступен для {token_address}: {e}")
        
        # Метод 2: Fallback на CoinGecko
        if price is None:
            try:
                token_info = await self._get_token_info(token_address)
                coingecko_id = token_info.get("coingecko_id")
                
                if coingecko_id:
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                data = await response.json()
                                if coingecko_id in data and "usd" in data[coingecko_id]:
                                    price = data[coingecko_id]["usd"]
            
            except Exception as e:
                logger.debug(f"⚠️ CoinGecko недоступен для {token_address}: {e}")
        
        # Кэшируем
        if price is not None:
            self.price_cache[token_address] = (price, datetime.utcnow())
        
        return price
    
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
        
        await self.initialize()
        
        try:
            if token_address is None:
                # Нативный SOL баланс
                result = await self.rpc_manager.call(
                    "getBalance",
                    [wallet_address],
                    priority=RequestPriority.NORMAL,
                    use_cache=True
                )
                
                if result and "value" in result:
                    return result["value"] / 1e9
                elif isinstance(result, int):
                    return result / 1e9
            
            else:
                # Token balance
                result = await self.rpc_manager.call(
                    "getTokenAccountsByOwner",
                    [
                        wallet_address,
                        {"mint": token_address},
                        {"encoding": "jsonParsed"}
                    ],
                    priority=RequestPriority.NORMAL,
                    use_cache=True
                )
                
                if result and "value" in result and result["value"]:
                    account = result["value"][0]
                    parsed = account["account"]["data"]["parsed"]["info"]
                    amount = parsed["tokenAmount"]["uiAmount"]
                    return amount or 0.0
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения Solana баланса для {wallet_address}: {e}")
        
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
    
    async def get_recent_transactions(
        self,
        wallet_address: str,
        limit: int = 100,
        before: Optional[str] = None
    ) -> List[str]:
        """
        Получить последние транзакции для кошелька
        
        Args:
            wallet_address: Solana address
            limit: Количество транзакций
            before: Signature для пагинации
        
        Returns:
            Список signatures
        """
        
        await self.initialize()
        
        try:
            params = [wallet_address, {"limit": limit}]
            
            if before:
                params[1]["before"] = before
            
            result = await self.rpc_manager.call(
                "getSignaturesForAddress",
                params,
                priority=RequestPriority.HIGH,
                use_cache=True
            )
            
            if not result:
                return []
            
            return [sig["signature"] for sig in result]
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения транзакций для {wallet_address}: {e}")
            return []
    
    async def batch_parse_transactions(self, signatures: List[str]) -> List[Optional[TransactionEvent]]:
        """
        Batch парсинг транзакций для оптимизации
        
        Args:
            signatures: Список signatures
        
        Returns:
            Список TransactionEvent
        """
        
        await self.initialize()
        
        try:
            # Используем batch call
            calls = [
                ("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
                for sig in signatures
            ]
            
            results = await self.rpc_manager.batch_call(calls, priority=RequestPriority.HIGH)
            
            events = []
            
            for sig, tx_data in zip(signatures, results):
                if tx_data:
                    event = await self._parse_transaction_data(sig, tx_data)
                    events.append(event)
                else:
                    events.append(None)
            
            return events
        
        except Exception as e:
            logger.error(f"❌ Ошибка batch парсинга: {e}")
            return [None] * len(signatures)
    
    # ========================================================================
    # SOLANA-SPECIFIC METHODS
    # ========================================================================
    
    async def _get_transaction(self, signature: str) -> Optional[Dict]:
        """Получает транзакцию через RPC Manager"""
        
        try:
            result = await self.rpc_manager.call(
                "getTransaction",
                [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "maxSupportedTransactionVersion": 0
                    }
                ],
                priority=RequestPriority.HIGH,
                use_cache=True
            )
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения транзакции {signature}: {e}")
            return None
    
    async def _parse_transaction_data(self, signature: str, tx_data: Dict) -> Optional[TransactionEvent]:
        """Внутренний метод для парсинга уже полученных данных транзакции"""
        
        try:
            meta = tx_data.get("meta", {})
            
            if meta.get("err"):
                return None
            
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])
            
            dex_name, dex_program_id = self._detect_dex_from_accounts(account_keys)
            
            if not dex_name:
                return None
            
            swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if not swap_data:
                return None
            
            block_time = tx_data.get("blockTime")
            timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()
            
            token_in_price = await self.get_token_price(swap_data["token_in"])
            token_out_price = await self.get_token_price(swap_data["token_out"])
            
            amount_in_usd = swap_data["amount_in"] * (token_in_price or 0)
            amount_out_usd = swap_data["amount_out"] * (token_out_price or 0)
            
            event = create_transaction_event(
                chain="solana",
                tx_hash=signature,
                block_number=tx_data.get("slot", 0),
                from_address=swap_data["user"],
                to_address=dex_program_id,
                dex_name=dex_name,
                dex_address=dex_program_id,
                token_in=swap_data["token_in"],
                token_out=swap_data["token_out"],
                amount_in=swap_data["amount_in"],
                amount_out=swap_data["amount_out"],
                amount_in_usd=amount_in_usd,
                amount_out_usd=amount_out_usd,
                timestamp=timestamp,
                event_type="swap",
                success=True,
                raw_data=tx_data
            )
            
            return event
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга данных транзакции: {e}")
            return None
    
    def _detect_dex_from_accounts(self, account_keys: List) -> Tuple[Optional[str], Optional[str]]:
        """
        Определяет DEX из списка accounts
        
        Returns:
            (dex_name, program_id) или (None, None)
        """
        
        for account in account_keys:
            if isinstance(account, dict):
                pubkey = account.get("pubkey", "")
            else:
                pubkey = account
            
            dex_name = self.detect_dex(pubkey)
            if dex_name:
                return dex_name, pubkey
        
        return None, None
    
    async def _parse_generic_swap(self, meta: Dict, account_keys: List) -> Optional[Dict]:
        """
        Generic парсер swap данных из transaction meta
        
        Работает для большинства DEX на Solana
        
        Returns:
            {
                "user": str,
                "token_in": str,
                "token_out": str,
                "amount_in": float,
                "amount_out": float
            }
        """
        
        try:
            # Pre и post token balances
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            
            if not pre_balances or not post_balances:
                return None
            
            # Находим изменения
            changes = []
            
            # Создаём мапу pre balances
            pre_map = {
                (balance.get("accountIndex"), balance.get("mint")): balance
                for balance in pre_balances
            }
            
            # Сравниваем с post balances
            for post in post_balances:
                account_index = post.get("accountIndex")
                mint = post.get("mint")
                post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount") or 0)
                
                key = (account_index, mint)
                
                if key in pre_map:
                    pre = pre_map[key]
                    pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    delta = post_amount - pre_amount
                    
                    if abs(delta) > 1e-9:
                        owner = post.get("owner", "")
                        
                        changes.append({
                            "account_index": account_index,
                            "mint": mint,
                            "delta": delta,
                            "owner": owner
                        })
                else:
                    # Новый токен аккаунт
                    if post_amount > 0:
                        owner = post.get("owner", "")
                        
                        changes.append({
                            "account_index": account_index,
                            "mint": mint,
                            "delta": post_amount,
                            "owner": owner
                        })
            
            # Проверяем закрытые токен аккаунты
            for key, pre in pre_map.items():
                if key not in [(p.get("accountIndex"), p.get("mint")) for p in post_balances]:
                    pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    if pre_amount > 0:
                        owner = pre.get("owner", "")
                        
                        changes.append({
                            "account_index": key[0],
                            "mint": key[1],
                            "delta": -pre_amount,
                            "owner": owner
                        })
            
            # Должно быть минимум 2 изменения
            if len(changes) < 2:
                return None
            
            # Группируем по owner для определения user
            owner_changes = defaultdict(list)
            for change in changes:
                owner_changes[change["owner"]].append(change)
            
            # Находим owner с максимальным количеством изменений (обычно это user)
            main_owner = max(owner_changes.keys(), key=lambda k: len(owner_changes[k]))
            user_changes = owner_changes[main_owner]
            
            # Определяем token_in (отрицательная дельта) и token_out (положительная)
            token_in_change = next((c for c in user_changes if c["delta"] < 0), None)
            token_out_change = next((c for c in user_changes if c["delta"] > 0), None)
            
            if not token_in_change or not token_out_change:
                # Пробуем найти среди всех изменений
                token_in_change = next((c for c in changes if c["delta"] < 0), None)
                token_out_change = next((c for c in changes if c["delta"] > 0), None)
                
                if not token_in_change or not token_out_change:
                    return None
            
            # User address
            user = main_owner if main_owner else (account_keys[0] if account_keys else "unknown")
            if isinstance(user, dict):
                user = user.get("pubkey", "unknown")
            
            amount_in = abs(token_in_change["delta"])
            amount_out = token_out_change["delta"]
            
            return {
                "user": user,
                "token_in": token_in_change["mint"],
                "token_out": token_out_change["mint"],
                "amount_in": amount_in,
                "amount_out": amount_out
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка generic парсинга swap: {e}")
            return None
    
    # ========================================================================
    # DEX-SPECIFIC PARSERS
    # ========================================================================
    
    async def _parse_raydium_swap(self, meta: Dict, message: Dict, account_keys: List) -> Optional[Dict]:
        """
        Парсит Raydium swap instruction
        
        Raydium использует AMM model с pool accounts
        """
        
        try:
            # Raydium swap можно распарсить через generic метод
            # но можем добавить специфичную логику если нужно
            
            swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if swap_data:
                # Добавляем Raydium-специфичную информацию
                instructions = message.get("instructions", [])
                
                for instruction in instructions:
                    if isinstance(instruction, dict):
                        program_id = instruction.get("programId", "")
                        
                        if program_id in ["675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", 
                                         "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"]:
                            # Это Raydium instruction
                            parsed = instruction.get("parsed")
                            if parsed:
                                swap_data["instruction_type"] = parsed.get("type", "swap")
                            
                            break
            
            return swap_data
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Raydium swap: {e}")
            return None
    
    async def _parse_orca_swap(self, meta: Dict, message: Dict, account_keys: List) -> Optional[Dict]:
        """
        Парсит Orca Whirlpool swap instruction
        
        Orca использует concentrated liquidity (CLMM) model
        """
        
        try:
            # Используем generic parser
            swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if swap_data:
                # Добавляем Orca-специфичную информацию
                instructions = message.get("instructions", [])
                
                for instruction in instructions:
                    if isinstance(instruction, dict):
                        program_id = instruction.get("programId", "")
                        
                        if program_id == "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc":
                            parsed = instruction.get("parsed")
                            if parsed:
                                swap_data["pool_type"] = "whirlpool"
                                swap_data["instruction_type"] = parsed.get("type", "swap")
                            
                            break
            
            return swap_data
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Orca swap: {e}")
            return None
    
    async def _parse_jupiter_swap(self, meta: Dict, message: Dict, account_keys: List) -> Optional[Dict]:
        """
        Парсит Jupiter Aggregator swap instruction
        
        Jupiter может использовать несколько DEX в одной транзакции
        """
        
        try:
            # Jupiter swap обычно содержит несколько inner swaps
            swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if swap_data:
                # Добавляем Jupiter-специфичную информацию
                instructions = message.get("instructions", [])
                
                # Jupiter может делать multi-hop swaps
                swap_data["aggregator"] = "Jupiter"
                
                # Подсчитываем количество промежуточных токенов
                pre_balances = meta.get("preTokenBalances", [])
                post_balances = meta.get("postTokenBalances", [])
                
                unique_mints = set()
                for balance in pre_balances + post_balances:
                    unique_mints.add(balance.get("mint"))
                
                if len(unique_mints) > 2:
                    swap_data["multi_hop"] = True
                    swap_data["intermediate_tokens"] = len(unique_mints) - 2
            
            return swap_data
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Jupiter swap: {e}")
            return None
    
    async def _parse_meteora_swap(self, meta: Dict, message: Dict, account_keys: List) -> Optional[Dict]:
        """
        Парсит Meteora swap instruction
        
        Meteora использует dynamic pools
        """
        
        try:
            swap_data = await self._parse_generic_swap(meta, account_keys)
            
            if swap_data:
                swap_data["pool_type"] = "meteora_dynamic"
            
            return swap_data
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Meteora swap: {e}")
            return None
    
    # ========================================================================
    # TOKEN METADATA
    # ========================================================================
    
    async def _get_token_info(self, mint_address: str) -> Dict:
        """
        Получает информацию о токене
        
        Args:
            mint_address: Token mint address
        
        Returns:
            {
                "symbol": str,
                "name": str,
                "decimals": int,
                "coingecko_id": str (optional)
            }
        """
        
        # Проверяем known tokens
        if mint_address in self.known_tokens:
            return self.known_tokens[mint_address]
        
        # Проверяем кэш
        if mint_address in self.token_metadata_cache:
            metadata, cached_at = self.token_metadata_cache[mint_address]
            if datetime.utcnow() - cached_at < self.metadata_cache_ttl:
                return metadata
        
        # Получаем метаданные
        metadata = await self._fetch_token_metadata(mint_address)
        
        # Кэшируем
        if metadata:
            self.token_metadata_cache[mint_address] = (metadata, datetime.utcnow())
        
        return metadata or {
            "symbol": mint_address[:6],
            "name": "Unknown Token",
            "decimals": 9
        }
    
    async def _fetch_token_metadata(self, mint_address: str) -> Optional[Dict]:
        """
        Получает метаданные токена через Solana RPC
        """
        
        await self.initialize()
        
        try:
            # Пробуем получить через Token Program
            result = await self.rpc_manager.call(
                "getAccountInfo",
                [
                    mint_address,
                    {"encoding": "jsonParsed"}
                ],
                priority=RequestPriority.LOW,
                use_cache=True
            )
            
            if result and "value" in result:
                account_data = result["value"]
                
                if account_data and "data" in account_data:
                    parsed = account_data["data"].get("parsed", {})
                    info = parsed.get("info", {})
                    
                    decimals = info.get("decimals", 9)
                    
                    return {
                        "symbol": mint_address[:6],
                        "name": "Token",
                        "decimals": decimals
                    }
        
        except Exception as e:
            logger.debug(f"⚠️ Не удалось получить метаданные токена {mint_address}: {e}")
        
        # Fallback: пробуем Jupiter Token List
        try:
            url = f"https://token.jup.ag/strict"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        tokens = await response.json()
                        
                        for token in tokens:
                            if token.get("address") == mint_address:
                                return {
                                    "symbol": token.get("symbol", "UNKNOWN"),
                                    "name": token.get("name", "Unknown Token"),
                                    "decimals": token.get("decimals", 9),
                                    "coingecko_id": token.get("extensions", {}).get("coingeckoId")
                                }
        
        except Exception as e:
            logger.debug(f"⚠️ Не удалось получить метаданные из Jupiter Token List: {e}")
        
        return None
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def get_rpc_health(self) -> Dict:
        """Получить health report RPC manager"""
        await self.initialize()
        return self.rpc_manager.get_health_report()
    
    async def print_rpc_health(self):
        """Вывести health report в консоль"""
        await self.initialize()
        self.rpc_manager.print_health_report()
    
    def clear_caches(self):
        """Очистить все кэши"""
        self.token_metadata_cache.clear()
        self.price_cache.clear()
        if self.rpc_manager:
            self.rpc_manager.clear_cache()
        logger.info("🧹 Кэши Solana парсера очищены")


# ============================================================================
# SOLANA DEX CLASSES
# ============================================================================

class RaydiumDEX:
    """Raydium AMM"""
    
    PROGRAM_ID_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    PROGRAM_ID_CLMM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
    
    @staticmethod
    def is_raydium_instruction(instruction: Dict) -> bool:
        """Проверяет является ли instruction Raydium swap"""
        program_id = instruction.get("programId")
        return program_id in [RaydiumDEX.PROGRAM_ID_V4, RaydiumDEX.PROGRAM_ID_CLMM]


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
    
    PROGRAM_ID_V6 = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
    PROGRAM_ID_V4 = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"
    
    @staticmethod
    def is_jupiter_instruction(instruction: Dict) -> bool:
        """Проверяет является ли instruction Jupiter swap"""
        program_id = instruction.get("programId")
        return program_id in [JupiterAggregator.PROGRAM_ID_V6, JupiterAggregator.PROGRAM_ID_V4]


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_solana_chain(rpc_urls: List[str] = None) -> SolanaChain:
    """
    Инициализирует Solana chain с RPC endpoints
    
    Usage:
        from app.chains.solana.parser import initialize_solana_chain
        from app.chains.base import ChainRegistry
        
        solana = initialize_solana_chain()
        ChainRegistry.register("solana", solana)
    """
    
    if rpc_urls is None:
        # Будут использованы endpoints из RPC Manager
        rpc_urls = []
    
    return SolanaChain(rpc_urls)


__all__ = [
    'SolanaChain',
    'RaydiumDEX',
    'OrcaDEX',
    'JupiterAggregator',
    'initialize_solana_chain'
]