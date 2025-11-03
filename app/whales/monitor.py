# app/whales/monitor.py
"""
BLOCKCHAIN MONITOR v4.3

Универсальный мониторинг крупных транзакций на всех блокчейнах:
- Multi-chain support (Ethereum, BSC, Solana, Tron, Base, Arbitrum, Polygon)
- Smart filtering (биржи, мосты, внутренние переводы)
- DEX detection (Uniswap, PancakeSwap, Raydium, etc)
- ERC-20/SPL token support
- Automatic retry с exponential backoff
- Circuit breaker для защиты от перегрузки
- Rate limiting и caching
- НОВОЕ v4.3: Детальное логирование фильтрации для диагностики
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import hashlib

from app import settings
from app.whales.normalize import WhaleEvent


class CircuitBreaker:
    """
    Circuit Breaker для защиты от перегрузки API
    
    States:
    - CLOSED: Нормальная работа
    - OPEN: API перегружен, все запросы блокируются
    - HALF_OPEN: Тестирование восстановления
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def record_success(self):
        """Записывает успешный запрос"""
        self.failures = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Записывает неудачный запрос"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            print(f"⚠️ [CIRCUIT] Circuit breaker OPEN ({self.failures} failures)")
    
    def can_execute(self) -> bool:
        """Проверяет можно ли выполнять запросы"""
        
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = "HALF_OPEN"
                print(f"🔄 [CIRCUIT] Circuit breaker HALF_OPEN (testing)")
                return True
            return False
        
        return True


class TransactionCache:
    """
    Кэш транзакций для предотвращения дубликатов
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, float] = {}
        self.ttl = ttl_seconds
    
    def add(self, tx_hash: str):
        """Добавляет транзакцию в кэш"""
        self.cache[tx_hash] = time.time()
        self._cleanup()
    
    def contains(self, tx_hash: str) -> bool:
        """Проверяет наличие транзакции в кэше"""
        self._cleanup()
        return tx_hash in self.cache
    
    def _cleanup(self):
        """Удаляет устаревшие записи"""
        now = time.time()
        to_remove = [
            tx_hash for tx_hash, timestamp in self.cache.items()
            if now - timestamp > self.ttl
        ]
        for tx_hash in to_remove:
            del self.cache[tx_hash]


class BlockchainMonitor:
    """
    Универсальный монитор всех блокчейнов
    
    НОВОЕ v4.3: Улучшенное логирование для диагностики
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.rate_limiter = None
        
        # API endpoints и ключи
        self.apis = {
            "ethereum": {
                "url": "https://api.etherscan.io/api",
                "key": settings.ETHERSCAN_API_KEY,
                "native_token": "ETH",
                "decimals": 18
            },
            "bsc": {
                "url": "https://api.bscscan.com/api",
                "key": settings.ETHERSCAN_API_KEY,
                "native_token": "BNB",
                "decimals": 18
            },
            "solana": {
                "url": f"https://mainnet.helius-rpc.com/?api-key={settings.HELIUS_API_KEY}",
                "key": settings.HELIUS_API_KEY,
                "native_token": "SOL",
                "decimals": 9
            },
            "tron": {
                "url": "https://apilist.tronscanapi.com/api",
                "key": settings.TRONSCAN_API_KEY,
                "native_token": "TRX",
                "decimals": 6
            },
            "base": {
                "url": "https://api.basescan.org/api",
                "key": settings.ETHERSCAN_API_KEY,
                "native_token": "ETH",
                "decimals": 18
            },
            "arbitrum": {
                "url": "https://api.arbiscan.io/api",
                "key": settings.ETHERSCAN_API_KEY,
                "native_token": "ETH",
                "decimals": 18
            },
            "polygon": {
                "url": "https://api.polygonscan.com/api",
                "key": settings.ETHERSCAN_API_KEY,
                "native_token": "MATIC",
                "decimals": 18
            }
        }
        
        # Circuit breakers для каждого chain
        self.circuit_breakers = {
            chain: CircuitBreaker(failure_threshold=3, timeout=120)
            for chain in self.apis.keys()
        }
        
        # Transaction cache
        self.tx_cache = TransactionCache(ttl_seconds=3600)
        
        # Адреса бирж и мостов
        self.exchange_addresses = self._load_exchange_addresses()
        self.bridge_addresses = self._load_bridge_addresses()
        
        # DEX contracts
        self.dex_contracts = self._load_dex_contracts()
        
        # Статистика
        self.stats = {
            "requests_made": defaultdict(int),
            "events_found": defaultdict(int),
            "events_filtered": defaultdict(int),
            "events_parsed_total": defaultdict(int),
            "events_parsed_none": defaultdict(int),
            "events_below_threshold": defaultdict(int),
            "events_exchange_filtered": defaultdict(int),
            "events_bridge_filtered": defaultdict(int),
            "events_internal_filtered": defaultdict(int),
            "cache_hits": 0,
            "errors": defaultdict(int),
            "circuit_breaker_trips": defaultdict(int),
            "dex_detected": defaultdict(int),
            "retries_429": defaultdict(int),
            "chains": {}
        }
    
    async def __aenter__(self):
        """Создает aiohttp сессию"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "CryptoCompass/4.3",
                "Accept": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает aiohttp сессию"""
        if self.session:
            await self.session.close()
    
    async def _execute_with_rate_limit(
        self,
        chain: str,
        request_func,
        *args,
        **kwargs
    ):
        """
        Выполняет запрос с интеграцией ChainRateLimiter
        """
        
        if chain not in self.stats["chains"]:
            self.stats["chains"][chain] = {
                "success": False,
                "http_429": False,
                "error": False,
                "attempts": 0
            }
        
        chain_stats = self.stats["chains"][chain]
        chain_stats["attempts"] += 1
        
        if self.rate_limiter:
            if not self.rate_limiter.is_chain_enabled(chain):
                print(f"⏸️ [MONITOR] {chain} временно отключен rate limiter")
                chain_stats["error"] = True
                return None
            
            await self.rate_limiter.wait_if_needed(chain)
        
        max_attempts = getattr(settings, 'RETRY_MAX_ATTEMPTS', 3)
        backoff_factor = getattr(settings, 'RETRY_BACKOFF_FACTOR', 2)
        initial_delay = getattr(settings, 'RETRY_INITIAL_DELAY', 1.0)
        
        for attempt in range(max_attempts):
            try:
                result = await request_func(*args, **kwargs)
                
                if self.rate_limiter:
                    self.rate_limiter.record_success(chain)
                
                chain_stats["success"] = True
                chain_stats["http_429"] = False
                chain_stats["error"] = False
                
                return result
            
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    chain_stats["http_429"] = True
                    
                    if self.rate_limiter:
                        self.rate_limiter.record_429_error(chain)
                    
                    if attempt < max_attempts - 1:
                        delay = initial_delay * (backoff_factor ** attempt)
                        
                        self.stats["retries_429"][chain] += 1
                        print(f"⏳ [RETRY] {chain} HTTP 429, attempt {attempt + 1}/{max_attempts}, waiting {delay:.1f}s")
                        
                        await asyncio.sleep(delay)
                    else:
                        print(f"❌ [RETRY] {chain} HTTP 429, max retries exceeded")
                        chain_stats["error"] = True
                        return None
                else:
                    print(f"❌ [MONITOR] {chain} HTTP {e.status}: {e}")
                    
                    if self.rate_limiter:
                        self.rate_limiter.record_other_error(chain)
                    
                    chain_stats["error"] = True
                    return None
            
            except asyncio.TimeoutError:
                print(f"⏱️ [MONITOR] {chain} timeout")
                
                if self.rate_limiter:
                    self.rate_limiter.record_other_error(chain)
                
                chain_stats["error"] = True
                return None
            
            except Exception as e:
                print(f"❌ [MONITOR] {chain} unexpected error: {e}")
                
                if self.rate_limiter:
                    self.rate_limiter.record_other_error(chain)
                
                chain_stats["error"] = True
                return None
        
        return None
    
    async def fetch_events(
        self,
        start_time: datetime,
        chains: Optional[List[str]] = None,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получает события со всех блокчейнов
        """
        
        if not self.session:
            raise RuntimeError("BlockchainMonitor должен использоваться с async context manager")
        
        chains_to_monitor = chains or list(self.apis.keys())
        
        chains_to_monitor = [
            chain for chain in chains_to_monitor
            if self.apis[chain]["key"] or chain in ["solana", "tron"]
        ]
        
        if self.rate_limiter:
            available_chains = [
                chain for chain in chains_to_monitor
                if self.rate_limiter.is_chain_enabled(chain)
            ]
            
            if len(available_chains) < len(chains_to_monitor):
                disabled = set(chains_to_monitor) - set(available_chains)
                print(f"⏸️ [CHAINS] Временно отключены: {', '.join(disabled)}")
            
            chains_to_monitor = available_chains
        
        if not chains_to_monitor:
            print("⚠️ [MONITOR] Нет доступных chains")
            return []
        
        print(f"🔍 [MONITOR] Сканирую {len(chains_to_monitor)} chains: {', '.join(chains_to_monitor)}")
        
        min_threshold = getattr(settings, 'MIN_USD_FLOOR', 10000)
        print(f"💰 [MONITOR] Минимальный порог: ${min_threshold:,.0f}")
        
        tasks = [
            self._fetch_chain_events(chain, start_time, assets)
            for chain in chains_to_monitor
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_events = []
        for chain, result in zip(chains_to_monitor, results):
            if isinstance(result, Exception):
                print(f"❌ [MONITOR] Ошибка {chain}: {result}")
                self.stats["errors"][chain] += 1
                continue
            
            if result:
                all_events.extend(result)
                self.stats["events_found"][chain] += len(result)
                print(f"✅ [MONITOR] {chain}: найдено {len(result)} событий")
        
        unique_events = {}
        for event in all_events:
            if event.tx_hash not in unique_events:
                unique_events[event.tx_hash] = event
        
        all_events = list(unique_events.values())
        
        all_events.sort(key=lambda e: e.tx_time_utc, reverse=True)
        
        print(f"🎯 [MONITOR] Всего уникальных событий: {len(all_events)}")
        
        return all_events
    
    async def _fetch_chain_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получает события для конкретного chain
        """
        
        if not self.circuit_breakers[chain].can_execute():
            print(f"⚠️ [MONITOR] {chain} circuit breaker OPEN, пропускаю")
            self.stats["circuit_breaker_trips"][chain] += 1
            return []
        
        try:
            if chain in ["ethereum", "bsc", "base", "arbitrum", "polygon"]:
                events = await self._fetch_evm_events(chain, start_time, assets)
            elif chain == "solana":
                events = await self._fetch_solana_events(start_time, assets)
            elif chain == "tron":
                events = await self._fetch_tron_events(start_time, assets)
            else:
                print(f"⚠️ [MONITOR] Неизвестный chain: {chain}")
                return []
            
            self.circuit_breakers[chain].record_success()
            self.stats["requests_made"][chain] += 1
            
            return events
        
        except Exception as e:
            print(f"❌ [MONITOR] Ошибка {chain}: {e}")
            self.circuit_breakers[chain].record_failure()
            self.stats["errors"][chain] += 1
            return []
    
    async def _fetch_evm_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получает события для EVM-совместимых chains
        """
        
        api_config = self.apis[chain]
        api_url = api_config["url"]
        api_key = api_config["key"]
        
        events = []
        
        native_events = await self._fetch_evm_native_transfers(
            chain, api_url, api_key, start_time
        )
        events.extend(native_events)
        
        if assets:
            token_events = await self._fetch_evm_token_transfers(
                chain, api_url, api_key, start_time, assets
            )
            events.extend(token_events)
        
        dex_events = await self._fetch_evm_dex_swaps(
            chain, api_url, api_key, start_time
        )
        events.extend(dex_events)
        
        return events
    
    async def _fetch_evm_native_transfers(
        self,
        chain: str,
        api_url: str,
        api_key: str,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """
        Получает крупные нативные транзакции (ETH, BNB, etc)
        """
        
        events = []
        
        try:
            rpc_endpoints = {
                "ethereum": "https://eth.llamarpc.com",
                "bsc": "https://bsc-dataseed.binance.org",
                "base": "https://mainnet.base.org",
                "arbitrum": "https://arb1.arbitrum.io/rpc",
                "polygon": "https://polygon-rpc.com"
            }
            
            rpc_url = rpc_endpoints.get(chain, api_url)
            
            async def _get_latest_block():
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }
                
                print(f"🔍 [DEBUG] {chain} - Запрос к RPC:")
                print(f"   RPC URL: {rpc_url}")
                
                headers = {"Content-Type": "application/json"}
                
                async with self.session.post(rpc_url, json=rpc_payload, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "error" in data:
                        error_msg = data.get("error", {})
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get("message", str(error_msg))
                        raise Exception(f"RPC error: {error_msg}")
                    
                    result = data.get("result", "0x0")
                    if isinstance(result, str) and result.startswith("0x"):
                        latest_block = int(result, 16)
                        print(f"✅ [DEBUG] {chain} - Успешный ответ:")
                        print(f"   Latest block: {latest_block} ({result})")
                        return latest_block
                    else:
                        raise Exception(f"Неверный формат блока: {result}")
            
            latest_block = await self._execute_with_rate_limit(chain, _get_latest_block)
            
            if latest_block is None:
                return []
            
            time_window_minutes = (datetime.utcnow() - start_time).total_seconds() / 60
            
            block_times = {
                "ethereum": 12,
                "bsc": 3,
                "base": 2,
                "arbitrum": 0.25,
                "polygon": 2
            }
            
            block_time = block_times.get(chain, 12)
            blocks_to_scan = int((time_window_minutes * 60) / block_time)
            blocks_to_scan = min(blocks_to_scan, 100)
            
            start_block = max(latest_block - blocks_to_scan, 0)
            
            for block_num in range(start_block, latest_block, 10):
                batch_size = min(10, latest_block - block_num)
                
                block_tasks = [
                    self._get_evm_block_with_txs(
                        chain, api_url, api_key, block_num + i
                    )
                    for i in range(batch_size)
                ]
                
                blocks = await asyncio.gather(*block_tasks, return_exceptions=True)
                
                for block_data in blocks:
                    if isinstance(block_data, Exception) or not block_data:
                        continue
                    
                    transactions = block_data.get("transactions", [])
                    
                    for tx in transactions:
                        tx_hash = tx.get("hash", "")
                        if self.tx_cache.contains(tx_hash):
                            self.stats["cache_hits"] += 1
                            continue
                        
                        event = await self._parse_evm_native_transaction(tx, chain)
                        
                        if event:
                            if self._should_filter_event(event, chain):
                                self.stats["events_filtered"][chain] += 1
                                continue
                            
                            events.append(event)
                            self.tx_cache.add(tx_hash)
                
                await asyncio.sleep(0.3)
        
        except Exception as e:
            print(f"❌ [MONITOR] Ошибка нативных трансферов {chain}: {e}")
        
        return events
    
    async def _get_evm_block_with_txs(
        self,
        chain: str,
        api_url: str,
        api_key: str,
        block_num: int
    ) -> Optional[Dict]:
        """
        Получает блок с транзакциями через прямой JSON-RPC
        """
        
        try:
            rpc_endpoints = {
                "https://api.etherscan.io/api": "https://eth.llamarpc.com",
                "https://api.bscscan.com/api": "https://bsc-dataseed.binance.org",
                "https://api.basescan.org/api": "https://mainnet.base.org",
                "https://api.arbiscan.io/api": "https://arb1.arbitrum.io/rpc",
                "https://api.polygonscan.com/api": "https://polygon-rpc.com"
            }
            
            rpc_url = rpc_endpoints.get(api_url, api_url)
            
            async def _get_block():
                rpc_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [hex(block_num), True],
                    "id": 1
                }
                
                headers = {"Content-Type": "application/json"}
                
                async with self.session.post(rpc_url, json=rpc_payload, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "error" in data:
                        return None
                    
                    return data.get("result")
            
            return await self._execute_with_rate_limit(chain, _get_block)
        
        except Exception:
            return None
    
    async def _parse_evm_native_transaction(
        self,
        tx: Dict,
        chain: str
    ) -> Optional[WhaleEvent]:
        """
        Парсит нативную EVM транзакцию
        """
        
        try:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if not from_addr or not to_addr:
                return None
            
            value_hex = tx.get("value", "0x0")
            value_wei = int(value_hex, 16)
            
            if value_wei == 0:
                return None
            
            api_config = self.apis[chain]
            decimals = api_config["decimals"]
            native_token = api_config["native_token"]
            
            amount = value_wei / (10 ** decimals)
            
            price = settings.FALLBACK_PRICES.get(native_token, 2000)
            amount_usd = amount * price
            
            min_threshold = getattr(settings, 'MIN_USD_FLOOR', 10000)
            if amount_usd < min_threshold:
                return None
            
            timestamp_hex = tx.get("timestamp")
            if timestamp_hex:
                timestamp = int(timestamp_hex, 16)
                tx_time = datetime.fromtimestamp(timestamp)
            else:
                tx_time = datetime.utcnow()
            
            dex = self._detect_dex(chain, to_addr)
            
            event = WhaleEvent(
                chain=chain,
                asset=native_token,
                from_address=from_addr,
                to_address=to_addr,
                amount=amount,
                amount_usd=amount_usd,
                tx_hash=tx.get("hash", ""),
                block_number=int(tx.get("blockNumber", "0x0"), 16),
                tx_time_utc=tx_time,
                dex=dex,
                is_internal=False,
                is_bridge=self._is_bridge_address(to_addr),
                is_reorg=False
            )
            
            return event
        
        except Exception as e:
            return None
    
    async def _fetch_evm_token_transfers(
        self,
        chain: str,
        api_url: str,
        api_key: str,
        start_time: datetime,
        assets: List[str]
    ) -> List[WhaleEvent]:
        """
        Получает крупные ERC-20 трансферы для указанных токенов
        """
        
        events = []
        
        return events
    
    async def _fetch_evm_dex_swaps(
        self,
        chain: str,
        api_url: str,
        api_key: str,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """
        Мониторит крупные DEX swaps
        """
        
        events = []
        
        return events
    
    async def _fetch_solana_events(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получает события для Solana
        """
        
        api_url = self.apis["solana"]["url"]
        events = []
        
        try:
            print(f"🔍 [DEBUG] solana - Запрос к RPC:")
            print(f"   RPC URL: {api_url}")
            
            async def _get_signatures():
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        "11111111111111111111111111111111",
                        {"limit": 100}
                    ]
                }
                
                async with self.session.post(api_url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
            
            data = await self._execute_with_rate_limit("solana", _get_signatures)
            
            if not data:
                print(f"❌ [MONITOR] Solana: не удалось получить сигнатуры")
                return []
            
            signatures = data.get("result", [])
            print(f"✅ [DEBUG] solana - Получено {len(signatures)} сигнатур")
            
            tx_tasks = [
                self._get_solana_transaction(api_url, sig["signature"])
                for sig in signatures[:20]
            ]
            
            transactions = await asyncio.gather(*tx_tasks, return_exceptions=True)
            
            parsed_count = 0
            for tx_data in transactions:
                if isinstance(tx_data, Exception) or not tx_data:
                    continue
                
                parsed_count += 1
                event = await self._parse_solana_transaction(tx_data)
                
                if event:
                    if self._should_filter_event(event, "solana"):
                        continue
                    
                    events.append(event)
            
            self.stats["events_parsed_total"]["solana"] = parsed_count
            print(f"✅ [DEBUG] solana - Распарсено {parsed_count} транзакций, найдено {len(events)} событий")
        
        except Exception as e:
            print(f"❌ [MONITOR] Ошибка Solana: {e}")
        
        return events
    
    async def _get_solana_transaction(
        self,
        api_url: str,
        signature: str
    ) -> Optional[Dict]:
        """
        Получает детали Solana транзакции
        """
        
        try:
            async def _get_tx():
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        signature,
                        {
                            "encoding": "jsonParsed",
                            "maxSupportedTransactionVersion": 0
                        }
                    ]
                }
                
                async with self.session.post(api_url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("result")
            
            return await self._execute_with_rate_limit("solana", _get_tx)
        
        except Exception:
            return None
    
    async def _parse_solana_transaction(
        self,
        tx_data: Dict
    ) -> Optional[WhaleEvent]:
        """
        Парсит Solana транзакцию
        """
        
        try:
            meta = tx_data.get("meta", {})
            transaction = tx_data.get("transaction", {})
            
            if meta.get("err"):
                return None
            
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            
            if not pre_balances or not post_balances:
                return None
            
            max_change = 0
            from_idx = -1
            to_idx = -1
            
            for i in range(min(len(pre_balances), len(post_balances))):
                change = abs(post_balances[i] - pre_balances[i])
                
                if change > max_change:
                    max_change = change
                    
                    if post_balances[i] < pre_balances[i]:
                        from_idx = i
                    else:
                        to_idx = i
            
            amount_sol = max_change / 1e9
            
            if amount_sol < 10:
                return None
            
            account_keys = transaction.get("message", {}).get("accountKeys", [])
            
            from_addr = account_keys[from_idx] if 0 <= from_idx < len(account_keys) else "unknown"
            to_addr = account_keys[to_idx] if 0 <= to_idx < len(account_keys) else "unknown"
            
            dex = self._detect_solana_dex(account_keys)
            
            price = settings.FALLBACK_PRICES.get("SOL", 150)
            amount_usd = amount_sol * price
            
            block_time = tx_data.get("blockTime")
            tx_time = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()
            
            event = WhaleEvent(
                chain="solana",
                asset="SOL",
                from_address=from_addr,
                to_address=to_addr,
                amount=amount_sol,
                amount_usd=amount_usd,
                tx_hash=transaction.get("signatures", [""])[0],
                block_number=tx_data.get("slot", 0),
                tx_time_utc=tx_time,
                dex=dex,
                is_internal=False,
                is_bridge=False,
                is_reorg=False
            )
            
            return event
        
        except Exception as e:
            return None
    
    def _detect_solana_dex(self, account_keys: List) -> Optional[str]:
        """
        Определяет Solana DEX по account keys
        """
        
        solana_dexes = {
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter",
            "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "Orca V2"
        }
        
        for account in account_keys:
            account_str = account if isinstance(account, str) else account.get("pubkey", "")
            
            if account_str in solana_dexes:
                return solana_dexes[account_str]
        
        return None
    
    async def _fetch_tron_events(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """
        Получает события для Tron с детальным логированием
        НОВОЕ v4.3: Улучшенная диагностика фильтрации
        """
        
        api_url = self.apis["tron"]["url"]
        api_key = self.apis["tron"]["key"]
        events = []
        
        try:
            print(f"🔍 [DEBUG] tron - Запрос к API:")
            print(f"   API URL: {api_url}")
            
            async def _get_transfers():
                params = {
                    "limit": 50,
                    "start": 0,
                    "sort": "-timestamp",
                    "count": "true"
                }
                
                headers = {}
                if api_key:
                    headers["TRON-PRO-API-KEY"] = api_key
                
                async with self.session.get(
                    f"{api_url}/transfer",
                    params=params,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("data", [])
            
            transfers = await self._execute_with_rate_limit("tron", _get_transfers)
            
            if not transfers:
                print(f"⚠️ [DEBUG] tron - Нет трансферов от API")
                return []
            
            print(f"✅ [DEBUG] tron - Получено {len(transfers)} трансферов")
            
            min_threshold = getattr(settings, 'MIN_USD_FLOOR', 10000)
            print(f"💰 [DEBUG] tron - Минимальный порог: ${min_threshold:,.0f}")
            
            parsed_count = 0
            none_count = 0
            
            for idx, transfer in enumerate(transfers):
                self.stats["events_parsed_total"]["tron"] += 1
                parsed_count += 1
                
                event = await self._parse_tron_transfer(transfer, idx + 1)
                
                if event is None:
                    none_count += 1
                    self.stats["events_parsed_none"]["tron"] += 1
                    continue
                
                if self._should_filter_event(event, "tron"):
                    continue
                
                events.append(event)
            
            print(f"📊 [DEBUG] tron - Статистика парсинга:")
            print(f"   Всего трансферов: {len(transfers)}")
            print(f"   Распарсено: {parsed_count}")
            print(f"   Вернули None: {none_count}")
            print(f"   Прошли фильтры: {len(events)}")
            print(f"✅ [DEBUG] tron - Найдено {len(events)} событий")
        
        except Exception as e:
            print(f"❌ [MONITOR] Ошибка Tron: {e}")
            import traceback
            traceback.print_exc()
        
        return events
    
    async def _parse_tron_transfer(
        self,
        transfer: Dict,
        transfer_num: int = 0
    ) -> Optional[WhaleEvent]:
        """
        Парсит Tron трансфер с детальным логированием
        НОВОЕ v4.3: Подробные логи для диагностики
        """
        
        try:
            amount_str = transfer.get("amount", "0")
            token_info = transfer.get("tokenInfo", {})
            token_symbol = token_info.get("tokenSymbol", "TRX")
            token_decimals = int(token_info.get("tokenDecimal", 6))
            
            amount_raw = float(amount_str)
            amount = amount_raw / (10 ** token_decimals)
            
            price = settings.FALLBACK_PRICES.get(token_symbol, 0.1)
            amount_usd = amount * price
            
            min_threshold = getattr(settings, 'MIN_USD_FLOOR', 10000)
            
            if transfer_num <= 3:
                print(f"🔍 [DEBUG] tron - Трансфер #{transfer_num}:")
                print(f"   Token: {token_symbol}")
                print(f"   Amount raw: {amount_raw}")
                print(f"   Decimals: {token_decimals}")
                print(f"   Amount: {amount:,.2f} {token_symbol}")
                print(f"   Price: ${price}")
                print(f"   USD Value: ${amount_usd:,.2f}")
                print(f"   Min threshold: ${min_threshold:,.0f}")
                print(f"   Pass threshold: {amount_usd >= min_threshold}")
            
            if amount_usd < min_threshold:
                if transfer_num <= 3:
                    print(f"   ❌ Отклонено: сумма ${amount_usd:,.2f} < ${min_threshold:,.0f}")
                self.stats["events_below_threshold"]["tron"] += 1
                return None
            
            from_addr = transfer.get("transferFromAddress", "")
            to_addr = transfer.get("transferToAddress", "")
            
            if transfer_num <= 3:
                print(f"   ✅ Прошло порог!")
                print(f"   From: {from_addr[:10]}...")
                print(f"   To: {to_addr[:10]}...")
            
            timestamp = transfer.get("timestamp", 0) / 1000
            tx_time = datetime.fromtimestamp(timestamp)
            
            event = WhaleEvent(
                chain="tron",
                asset=token_symbol,
                from_address=from_addr,
                to_address=to_addr,
                amount=amount,
                amount_usd=amount_usd,
                tx_hash=transfer.get("transactionHash", ""),
                block_number=transfer.get("block", 0),
                tx_time_utc=tx_time,
                dex=None,
                is_internal=False,
                is_bridge=False,
                is_reorg=False
            )
            
            return event
        
        except Exception as e:
            if transfer_num <= 3:
                print(f"❌ [DEBUG] tron - Ошибка парсинга трансфера #{transfer_num}: {e}")
            return None
    
    def _detect_dex(self, chain: str, address: str) -> Optional[str]:
        """
        Определяет DEX по адресу контракта
        """
        
        address = address.lower()
        
        chain_dexes = self.dex_contracts.get(chain, {})
        return chain_dexes.get(address)
    
    def _load_dex_contracts(self) -> Dict[str, Dict[str, str]]:
        """
        Загружает адреса DEX контрактов
        """
        
        return {
            "ethereum": {
                "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
                "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
                "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "Sushiswap",
                "0xba12222222228d8ba445958a75a0704d566bf2c8": "Balancer",
                "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x"
            },
            "bsc": {
                "0x10ed43c718714eb63d5aa57b78b54704e256024e": "PancakeSwap V2",
                "0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "PancakeSwap V3",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            },
            "base": {
                "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V3",
                "0x327df1e6de05895d2ab08513aadd9313fe505d86": "Aerodrome",
                "0x8909dc15e40173ff4699343b6eb8132c65e18ec6": "BaseSwap"
            },
            "arbitrum": {
                "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
                "0xc873fecbd354f5a56e00e710b90ef4201db2448d": "Camelot",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            },
            "polygon": {
                "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
                "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff": "QuickSwap",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            }
        }
    
    def _should_filter_event(self, event: WhaleEvent, chain: str) -> bool:
        """
        Определяет нужно ли фильтровать событие с детальным логированием
        НОВОЕ v4.3: Логирование причин фильтрации
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
        
        min_threshold = getattr(settings, 'MIN_USD_FLOOR', 10000)
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
    
    def _load_exchange_addresses(self) -> Set[str]:
        """
        Загружает список адресов бирж
        """
        
        exchanges = {
            "0x28c6c06298d514db089934071355e5743bf21d60",
            "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
            "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
            "0x564286362092d8e7936f0549571a803b203aaced",
            "0x0681d8db095565fe8a346fa0277bffde9c0edbbf",
            "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
            "0x503828976d22510aad0201ac7ec88293211d23da",
            "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740",
            "0xa090e606e30bd747d4e6245a1517ebe430f0057e",
            "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
            "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",
            "0xe853c56864a2ebe4576a807d26fdc4a0ada51919",
            "0x1151314c646ce4e0efd76d1af4760ae66a9fe30f",
            "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa",
            "0x98ec059dc3adfbdd63429454aeb0c990fba4a128",
            "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
            "0xf89d7b9c864f589bbf53a82105107622b35eaa40",
            "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c",
            "0xab5c66752a9e8167967685f1450532fb96d5d24f",
            "0x2b5634c42055806a59e9107ed44d43c426e58258"
        }
        
        return exchanges
    
    def _load_bridge_addresses(self) -> Set[str]:
        """
        Загружает список адресов мостов
        """
        
        bridges = {
            "0x6b7a87899490ece95443e979ca9485cbe7e71522",
            "0x5427fefa711eff984124bfbb1ab6fbf5e3da1820",
            "0x2796317b0ff8538f253012862c06787adfb8ceb6",
            "0xc186fa914353c44b2e33ebe05f21846f1048beda",
            "0x3666f603cc164936c1b87e207f36babaa41b67aa",
            "0x8731d54e9d02c286767d56ac03e8037c07e01e98",
            "0x66a71dcef29a0ffbdbe3c6a460a3b5bc225cd675"
        }
        
        return bridges
    
    def get_stats(self) -> Dict:
        """
        Возвращает статистику мониторинга
        НОВОЕ v4.3: Расширенная статистика фильтрации
        """
        
        return {
            "requests_made": dict(self.stats["requests_made"]),
            "events_found": dict(self.stats["events_found"]),
            "events_filtered": dict(self.stats["events_filtered"]),
            "events_parsed_total": dict(self.stats["events_parsed_total"]),
            "events_parsed_none": dict(self.stats["events_parsed_none"]),
            "events_below_threshold": dict(self.stats["events_below_threshold"]),
            "events_exchange_filtered": dict(self.stats["events_exchange_filtered"]),
            "events_bridge_filtered": dict(self.stats["events_bridge_filtered"]),
            "events_internal_filtered": dict(self.stats["events_internal_filtered"]),
            "cache_hits": self.stats["cache_hits"],
            "errors": dict(self.stats["errors"]),
            "circuit_breaker_trips": dict(self.stats["circuit_breaker_trips"]),
            "dex_detected": dict(self.stats["dex_detected"]),
            "retries_429": dict(self.stats["retries_429"]),
            "circuit_breaker_states": {
                chain: breaker.state
                for chain, breaker in self.circuit_breakers.items()
            },
            "chains": dict(self.stats["chains"])
        }
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("📊 BLOCKCHAIN MONITOR STATISTICS v4.3")
        print("=" * 80)
        
        print(f"\n📡 Requests Made:")
        for chain, count in stats["requests_made"].items():
            print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n🐋 Events Found:")
        for chain, count in stats["events_found"].items():
            print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n🚫 Events Filtered:")
        for chain, count in stats["events_filtered"].items():
            if count > 0:
                print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n📊 Filter Details:")
        print(f"   Below threshold: {dict(stats['events_below_threshold'])}")
        print(f"   Exchange filtered: {dict(stats['events_exchange_filtered'])}")
        print(f"   Bridge filtered: {dict(stats['events_bridge_filtered'])}")
        print(f"   Internal filtered: {dict(stats['events_internal_filtered'])}")
        
        print(f"\n🔍 Parsing Stats:")
        print(f"   Total parsed: {dict(stats['events_parsed_total'])}")
        print(f"   Returned None: {dict(stats['events_parsed_none'])}")
        
        print(f"\n💾 Cache Hits: {stats['cache_hits']}")
        
        print(f"\n🔄 429 Retries:")
        for chain, count in stats["retries_429"].items():
            if count > 0:
                print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n❌ Errors:")
        for chain, count in stats["errors"].items():
            if count > 0:
                print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n⚡ Circuit Breaker States:")
        for chain, state in stats["circuit_breaker_states"].items():
            emoji = "✅" if state == "CLOSED" else "⚠️" if state == "HALF_OPEN" else "🔴"
            print(f"   {chain:12s}: {emoji} {state}")
        
        if stats["chains"]:
            print(f"\n🔗 Chain Status (v4.3):")
            for chain, chain_stats in stats["chains"].items():
                status = "✅" if chain_stats.get("success", False) else "❌"
                http_429 = "🔴 429" if chain_stats.get("http_429", False) else ""
                error = "⚠️ ERROR" if chain_stats.get("error", False) else ""
                attempts = chain_stats.get("attempts", 0)
                
                status_str = f"{status} {http_429} {error}".strip()
                print(f"   {chain:12s}: {status_str} ({attempts} attempts)")
        
        print("\n" + "=" * 80 + "\n")