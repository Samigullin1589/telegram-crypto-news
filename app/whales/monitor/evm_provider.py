# app/whales/monitor/evm_provider.py
"""
EVM Chain Provider (Ethereum, BSC, Base, Arbitrum, Polygon)
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector


class EVMProvider:
    """Провайдер для EVM-совместимых блокчейнов"""
    
    def __init__(self, session, rate_limiter, tx_cache, dex_detector: DEXDetector):
        self.session = session
        self.rate_limiter = rate_limiter
        self.tx_cache = tx_cache
        self.dex_detector = dex_detector
        
        self.rpc_endpoints = {
            "ethereum": "https://eth.llamarpc.com",
            "bsc": "https://bsc-dataseed.binance.org",
            "base": "https://mainnet.base.org",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "polygon": "https://polygon-rpc.com"
        }
        
        self.chain_configs = {
            "ethereum": {"native": "ETH", "decimals": 18, "block_time": 12},
            "bsc": {"native": "BNB", "decimals": 18, "block_time": 3},
            "base": {"native": "ETH", "decimals": 18, "block_time": 2},
            "arbitrum": {"native": "ETH", "decimals": 18, "block_time": 0.25},
            "polygon": {"native": "MATIC", "decimals": 18, "block_time": 2}
        }
    
    async def fetch_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """Получает события для EVM chain"""
        
        events = []
        
        native_events = await self._fetch_native_transfers(chain, start_time)
        events.extend(native_events)
        
        return events
    
    async def _fetch_native_transfers(
        self,
        chain: str,
        start_time: datetime
    ) -> List[WhaleEvent]:
        """Получает крупные нативные транзакции"""
        
        events = []
        
        try:
            latest_block = await self._get_latest_block(chain)
            
            if latest_block is None:
                return []
            
            time_window_minutes = (datetime.utcnow() - start_time).total_seconds() / 60
            chain_config = self.chain_configs[chain]
            block_time = chain_config["block_time"]
            blocks_to_scan = int((time_window_minutes * 60) / block_time)
            blocks_to_scan = min(blocks_to_scan, 100)
            
            start_block = max(latest_block - blocks_to_scan, 0)
            
            for block_num in range(start_block, latest_block, 10):
                batch_size = min(10, latest_block - block_num)
                
                block_tasks = [
                    self._get_block_with_txs(chain, block_num + i)
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
                            continue
                        
                        event = await self._parse_native_transaction(tx, chain)
                        
                        if event:
                            events.append(event)
                            self.tx_cache.add(tx_hash)
                
                await asyncio.sleep(0.3)
        
        except Exception as e:
            print(f"❌ [EVM] Ошибка {chain}: {e}")
        
        return events
    
    async def _get_latest_block(self, chain: str) -> Optional[int]:
        """Получает номер последнего блока"""
        
        try:
            rpc_url = self.rpc_endpoints[chain]
            
            rpc_payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            headers = {"Content-Type": "application/json"}
            
            async with self.session.post(rpc_url, json=rpc_payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                
                if "error" in data:
                    return None
                
                result = data.get("result", "0x0")
                if isinstance(result, str) and result.startswith("0x"):
                    return int(result, 16)
                
                return None
        
        except Exception:
            return None
    
    async def _get_block_with_txs(
        self,
        chain: str,
        block_num: int
    ) -> Optional[Dict]:
        """Получает блок с транзакциями"""
        
        try:
            rpc_url = self.rpc_endpoints[chain]
            
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
        
        except Exception:
            return None
    
    async def _parse_native_transaction(
        self,
        tx: Dict,
        chain: str
    ) -> Optional[WhaleEvent]:
        """Парсит нативную EVM транзакцию"""
        
        try:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if not from_addr or not to_addr:
                return None
            
            value_hex = tx.get("value", "0x0")
            value_wei = int(value_hex, 16)
            
            if value_wei == 0:
                return None
            
            chain_config = self.chain_configs[chain]
            decimals = chain_config["decimals"]
            native_token = chain_config["native"]
            
            amount = value_wei / (10 ** decimals)
            
            fallback_prices = {
                "ETH": 2500,
                "BNB": 400,
                "MATIC": 0.8
            }
            
            price = fallback_prices.get(native_token, 2000)
            amount_usd = amount * price
            
            min_threshold = getattr(config.whale, 'min_usd_threshold', 50000)
            if amount_usd < min_threshold:
                return None
            
            timestamp_hex = tx.get("timestamp")
            if timestamp_hex:
                timestamp = int(timestamp_hex, 16)
                tx_time = datetime.fromtimestamp(timestamp)
            else:
                tx_time = datetime.utcnow()
            
            dex = self.dex_detector.detect_evm_dex(chain, to_addr)
            
            event = WhaleEvent(
                chain=chain,
                asset=native_token,
                from_address=from_addr,
                to_address=to_addr,
                amount_native=amount,
                amount_usd=amount_usd,
                tx_hash=tx.get("hash", ""),
                direction="unknown",
                phase="execution",
                dex=dex,
                is_internal=False,
                is_bridge=False,
                is_reorg=False,
                tx_time_utc=tx_time
            )
            
            return event
        
        except Exception:
            return None