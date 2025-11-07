# app/whales/monitor/solana_provider.py
"""
Solana Chain Provider
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.dex_detector import DEXDetector


class SolanaProvider:
    """Провайдер для Solana"""
    
    def __init__(self, session, rate_limiter, tx_cache, dex_detector: DEXDetector):
        self.session = session
        self.rate_limiter = rate_limiter
        self.tx_cache = tx_cache
        self.dex_detector = dex_detector
        
        helius_key = getattr(config.chains.api_keys, 'helius', '') or getattr(config, 'HELIUS_API_KEY', '')
        self.api_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    
    async def fetch_events(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """Получает события для Solana"""
        
        events = []
        
        try:
            signatures = await self._get_signatures()
            
            if not signatures:
                return []
            
            print(f"✅ [SOLANA] Получено {len(signatures)} сигнатур")
            
            tx_tasks = [
                self._get_transaction(sig["signature"])
                for sig in signatures[:20]
            ]
            
            transactions = await asyncio.gather(*tx_tasks, return_exceptions=True)
            
            for tx_data in transactions:
                if isinstance(tx_data, Exception) or not tx_data:
                    continue
                
                event = await self._parse_transaction(tx_data)
                
                if event:
                    events.append(event)
        
        except Exception as e:
            print(f"❌ [SOLANA] Ошибка: {e}")
        
        return events
    
    async def _get_signatures(self) -> List[Dict]:
        """Получает список сигнатур транзакций"""
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    "11111111111111111111111111111111",
                    {"limit": 100}
                ]
            }
            
            async with self.session.post(self.api_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                
                return data.get("result", [])
        
        except Exception:
            return []
    
    async def _get_transaction(self, signature: str) -> Optional[Dict]:
        """Получает детали транзакции"""
        
        try:
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
            
            async with self.session.post(self.api_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("result")
        
        except Exception:
            return None
    
    async def _parse_transaction(self, tx_data: Dict) -> Optional[WhaleEvent]:
        """Парсит Solana транзакцию"""
        
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
            
            dex = self.dex_detector.detect_solana_dex(account_keys)
            
            price = 150
            amount_usd = amount_sol * price
            
            block_time = tx_data.get("blockTime")
            tx_time = datetime.fromtimestamp(block_time) if block_time else datetime.utcnow()
            
            event = WhaleEvent(
                chain="solana",
                asset="SOL",
                from_address=from_addr,
                to_address=to_addr,
                amount_native=amount_sol,
                amount_usd=amount_usd,
                tx_hash=transaction.get("signatures", [""])[0],
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