# app/whales/monitor/tron_provider.py
"""
Tron Chain Provider
"""

from typing import List, Dict, Optional
from datetime import datetime

from app.config import config
from app.whales.normalize import WhaleEvent


class TronProvider:
    """Провайдер для Tron"""
    
    def __init__(self, session, rate_limiter, tx_cache):
        self.session = session
        self.rate_limiter = rate_limiter
        self.tx_cache = tx_cache
        
        self.api_url = "https://apilist.tronscanapi.com/api"
        self.api_key = getattr(config.chains.api_keys, 'tronscan', '') or getattr(config, 'TRONSCAN_API_KEY', '')
    
    async def fetch_events(
        self,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """Получает события для Tron"""
        
        events = []
        
        try:
            transfers = await self._get_transfers()
            
            if not transfers:
                return []
            
            print(f"✅ [TRON] Получено {len(transfers)} трансферов")
            
            min_threshold = getattr(config.whale, 'min_usd_threshold', 50000)
            
            for idx, transfer in enumerate(transfers):
                event = await self._parse_transfer(transfer, idx + 1)
                
                if event and event.amount_usd >= min_threshold:
                    events.append(event)
            
            print(f"✅ [TRON] Найдено {len(events)} событий")
        
        except Exception as e:
            print(f"❌ [TRON] Ошибка: {e}")
        
        return events
    
    async def _get_transfers(self) -> List[Dict]:
        """Получает список трансферов"""
        
        try:
            params = {
                "limit": 50,
                "start": 0,
                "sort": "-timestamp",
                "count": "true"
            }
            
            headers = {}
            if self.api_key:
                headers["TRON-PRO-API-KEY"] = self.api_key
            
            async with self.session.get(
                f"{self.api_url}/transfer",
                params=params,
                headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("data", [])
        
        except Exception:
            return []
    
    async def _parse_transfer(
        self,
        transfer: Dict,
        transfer_num: int = 0
    ) -> Optional[WhaleEvent]:
        """Парсит Tron трансфер"""
        
        try:
            amount_str = transfer.get("amount", "0")
            token_info = transfer.get("tokenInfo", {})
            token_symbol = token_info.get("tokenSymbol", "TRX")
            token_decimals = int(token_info.get("tokenDecimal", 6))
            
            amount_raw = float(amount_str)
            amount = amount_raw / (10 ** token_decimals)
            
            fallback_prices = {
                "TRX": 0.1,
                "USDT": 1.0,
                "USDC": 1.0
            }
            
            price = fallback_prices.get(token_symbol, 0.1)
            amount_usd = amount * price
            
            from_addr = transfer.get("transferFromAddress", "")
            to_addr = transfer.get("transferToAddress", "")
            
            timestamp = transfer.get("timestamp", 0) / 1000
            tx_time = datetime.fromtimestamp(timestamp)
            
            event = WhaleEvent(
                chain="tron",
                asset=token_symbol,
                from_address=from_addr,
                to_address=to_addr,
                amount_native=amount,
                amount_usd=amount_usd,
                tx_hash=transfer.get("transactionHash", ""),
                direction="unknown",
                phase="execution",
                dex=None,
                is_internal=False,
                is_bridge=False,
                is_reorg=False,
                tx_time_utc=tx_time
            )
            
            return event
        
        except Exception:
            return None