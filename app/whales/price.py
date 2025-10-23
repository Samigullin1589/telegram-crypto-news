# app/whales/price.py
import aiohttp
import asyncio
from typing import Optional, Dict
from datetime import datetime
from app import settings
from app.whales.normalize import MarketInfo

class PriceProvider:
    """Получение цен и 24h объёмов через CoinGecko"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 60  # кэш на 60 секунд
        
    async def get_market_info(self, asset: str, session: aiohttp.ClientSession) -> Optional[MarketInfo]:
        """Получает цену и 24h объём для актива"""
        
        # Проверяем кэш
        if asset in self.cache:
            cached = self.cache[asset]
            if (datetime.utcnow() - cached["timestamp"]).seconds < self.cache_ttl:
                return cached["data"]
        
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            
            coin_id = self._get_coingecko_id(asset)
            if not coin_id:
                if settings.DEBUG_FILTERS:
                    print(f"⚠️  [PRICE] Неизвестный актив для CoinGecko: {asset}")
                return None
            
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            if settings.COINGECKO_API_KEY:
                params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
            
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    print(f"⚠️  [PRICE] CoinGecko вернул {resp.status} для {asset}")
                    return None
                
                data = await resp.json()
                
                if coin_id not in data:
                    return None
                
                coin_data = data[coin_id]
                
                market_info = MarketInfo(
                    price=coin_data.get("usd"),
                    volume_24h_usd=coin_data.get("usd_24h_vol"),
                    price_change_24h=coin_data.get("usd_24h_change")
                )
                
                # Кэшируем
                self.cache[asset] = {
                    "data": market_info,
                    "timestamp": datetime.utcnow()
                }
                
                if settings.DEBUG_FILTERS:
                    print(f"💵 [PRICE] {asset}: ${market_info.price:,.2f}, Vol 24h: ${market_info.volume_24h_usd:,.0f}")
                
                return market_info
                
        except Exception as e:
            print(f"❌ [PRICE] Ошибка для {asset}: {e}")
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
            "OP": "optimism",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "AAVE": "aave",
            "WETH": "weth",
            "WBTC": "wrapped-bitcoin",
            "DAI": "dai",
            "TRX": "tron",
        }
        
        return mapping.get(asset.upper())
    
    async def enrich_event_with_market_data(self, event, session: aiohttp.ClientSession):
        """Обогащает событие рыночными данными"""
        
        old_usd = event.amount_usd
        
        market_info = await self.get_market_info(event.asset, session)
        
        if market_info:
            event.market = market_info
            
            # ИСПРАВЛЕНО: ВСЕГДА пересчитываем USD если есть реальная цена
            # Раньше было: if market_info.price and event.amount_usd == 0
            # Теперь: ВСЕГДА пересчитываем
            if market_info.price:
                event.amount_usd = event.amount_native * market_info.price
                
                if settings.DEBUG_FILTERS and old_usd != event.amount_usd:
                    print(f"🔄 [PRICE] {event.asset}: пересчёт ${old_usd:,.0f} → ${event.amount_usd:,.0f}")
            
            # В Discovery режиме пересчитываем порог
            if settings.ASSETS == '*':
                old_threshold = event.min_usd_threshold
                event.min_usd_threshold = self.calculate_dynamic_threshold(
                    event.asset,
                    market_info.volume_24h_usd
                )
                
                if settings.DEBUG_FILTERS and old_threshold != event.min_usd_threshold:
                    print(f"📊 [THRESHOLD] {event.asset}: ${old_threshold:,.0f} → ${event.min_usd_threshold:,.0f}")
        else:
            if settings.DEBUG_FILTERS:
                print(f"⚠️  [PRICE] Не удалось получить рыночные данные для {event.asset}")
    
    def calculate_dynamic_threshold(self, asset: str, volume_24h_usd: Optional[float]) -> float:
        """Динамический порог для Discovery режима"""
        if not volume_24h_usd or volume_24h_usd == 0:
            return settings.MIN_USD_FLOOR
        
        dynamic = settings.MIN_USD_K * volume_24h_usd
        return max(settings.MIN_USD_FLOOR, dynamic)