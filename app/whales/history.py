# app/whales/history.py
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional
from app import settings
from app.whales.normalize import WhaleEvent, HistoryHint

class HistoryManager:
    """Управление историей для функции 'В прошлый раз' с РЕАЛЬНЫМИ ценами"""
    
    def __init__(self):
        self.history_dir = settings.HISTORY_DIR
    
    def save_event(self, event: WhaleEvent, verdict: str):
        """Сохраняет событие в историю"""
        history_file = f"{self.history_dir}/{event.asset}.jsonl"
        
        entry = {
            "ts": event.tx_time_utc.isoformat(),
            "phase": event.phase,
            "direction": event.direction,
            "size_bucket": self._get_size_bucket(event.amount_usd),
            "price_at_tx": event.market.price if event.market.price else 0,
            "verdict": verdict,
            "amount_usd": event.amount_usd
        }
        
        try:
            with open(history_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠️  [HISTORY] Не удалось сохранить {event.asset}: {e}")
    
    async def find_similar_event(self, event: WhaleEvent, session: aiohttp.ClientSession) -> Optional[HistoryHint]:
        """Ищет похожее событие и рассчитывает РЕАЛЬНЫЕ Δ%"""
        
        history_file = f"{self.history_dir}/{event.asset}.jsonl"
        
        try:
            with open(history_file, 'r') as f:
                lines = f.readlines()
            
            cutoff = datetime.utcnow() - timedelta(days=30)
            current_bucket = self._get_size_bucket(event.amount_usd)
            
            candidates = []
            
            for line in lines:
                try:
                    entry = json.loads(line)
                    entry_ts = datetime.fromisoformat(entry["ts"])
                    
                    if entry_ts < cutoff:
                        continue
                    
                    if (entry["direction"] == event.direction and
                        entry["size_bucket"] == current_bucket and
                        entry["phase"] in [event.phase, "activation"]):
                        
                        candidates.append(entry)
                
                except Exception:
                    continue
            
            if not candidates:
                return None
            
            candidates.sort(key=lambda x: x["ts"], reverse=True)
            match = candidates[0]
            
            match_ts = datetime.fromisoformat(match["ts"])
            deltas = await self._calculate_price_deltas(event.asset, match_ts, match["price_at_tx"], session)
            
            if deltas:
                hint = HistoryHint(
                    d1h=deltas.get("1h"),
                    d4h=deltas.get("4h"),
                    d24h=deltas.get("24h"),
                    comparable_ts=match["ts"]
                )
                return hint
            
            return None
            
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"⚠️  [HISTORY] Ошибка: {e}")
            return None
    
    async def _calculate_price_deltas(
        self, 
        asset: str, 
        event_time: datetime, 
        price_at_event: float,
        session: aiohttp.ClientSession
    ) -> Optional[dict]:
        """Рассчитывает реальные Δ% через CoinGecko History API"""
        
        if not price_at_event or price_at_event == 0:
            return None
        
        try:
            coin_id = self._get_coingecko_id(asset)
            if not coin_id:
                return None
            
            t1h = event_time + timedelta(hours=1)
            t4h = event_time + timedelta(hours=4)
            t24h = event_time + timedelta(hours=24)
            
            now = datetime.utcnow()
            if t1h > now:
                return None
            
            prices = {}
            
            for label, target_time in [("1h", t1h), ("4h", t4h), ("24h", t24h)]:
                if target_time > now:
                    continue
                
                price = await self._get_historical_price(coin_id, target_time, session)
                if price:
                    delta_pct = ((price - price_at_event) / price_at_event) * 100
                    prices[label] = round(delta_pct, 1)
            
            if not prices:
                return None
            
            return prices
            
        except Exception as e:
            print(f"⚠️  [HISTORY] Ошибка расчёта дельт: {e}")
            return None
    
    async def _get_historical_price(
        self, 
        coin_id: str, 
        target_time: datetime, 
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """Получает историческую цену из CoinGecko"""
        try:
            date_str = target_time.strftime("%d-%m-%Y")
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
            params = {
                "date": date_str,
                "localization": "false"
            }
            
            if settings.COINGECKO_API_KEY:
                params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2)
                    return None
                
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                market_data = data.get("market_data", {})
                current_price = market_data.get("current_price", {})
                price_usd = current_price.get("usd")
                
                return price_usd
                
        except Exception as e:
            return None
    
    def _get_coingecko_id(self, asset: str) -> Optional[str]:
        """Маппинг символов на CoinGecko IDs"""
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "USDT": "tether",
            "USDC": "usd-coin",
            "BNB": "binancecoin",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "ARB": "arbitrum",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "WETH": "weth",
            "WBTC": "wrapped-bitcoin",
            "DAI": "dai",
        }
        
        return mapping.get(asset.upper())
    
    def _get_size_bucket(self, amount_usd: float) -> str:
        """Определяет размерную категорию"""
        if amount_usd < 500_000:
            return "small"
        elif amount_usd < 2_000_000:
            return "medium"
        elif amount_usd < 10_000_000:
            return "large"
        else:
            return "whale"