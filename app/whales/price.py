# app/whales/price.py (ПОЛНОСТЬЮ УЛУЧШЕННАЯ ВЕРСИЯ)
import aiohttp
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from app import settings
from app.whales.normalize import MarketInfo

class PriceProvider:
    """Получение цен с fallback на несколько источников"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 60  # кэш на 60 секунд
        self.failed_providers: Dict[str, datetime] = {}  # Отслеживание проблемных провайдеров
        
    async def get_market_info(self, asset: str, session: aiohttp.ClientSession) -> Optional[MarketInfo]:
        """Получает цену и 24h объём для актива с fallback"""
        
        # Проверяем кэш
        if asset in self.cache:
            cached = self.cache[asset]
            if (datetime.utcnow() - cached["timestamp"]).seconds < self.cache_ttl:
                return cached["data"]
        
        # Пробуем источники по порядку
        providers = [
            self._fetch_from_coingecko,
            self._fetch_from_binance,
            self._fetch_from_coinmarketcap,
        ]
        
        for provider in providers:
            try:
                market_info = await provider(asset, session)
                if market_info and market_info.price:
                    # Кэшируем
                    self.cache[asset] = {
                        "data": market_info,
                        "timestamp": datetime.utcnow()
                    }
                    
                    if settings.DEBUG_FILTERS:
                        print(f"💵 [PRICE] {asset}: ${market_info.price:,.2f}, Vol 24h: ${market_info.volume_24h_usd:,.0f}")
                    
                    return market_info
            except Exception as e:
                if settings.DEBUG_FILTERS:
                    print(f"⚠️  [PRICE] {provider.__name__} не удалось для {asset}: {e}")
                continue
        
        # Все провайдеры провалились
        print(f"❌ [PRICE] Не удалось получить цену для {asset} из всех источников")
        return None
    
    async def _fetch_from_coingecko(self, asset: str, session: aiohttp.ClientSession) -> Optional[MarketInfo]:
        """Источник 1: CoinGecko"""
        
        coin_id = self._get_coingecko_id(asset)
        if not coin_id:
            return None
        
        url = "https://api.coingecko.com/api/v3/simple/price"
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
                raise Exception(f"CoinGecko вернул {resp.status}")
            
            data = await resp.json()
            
            if coin_id not in data:
                return None
            
            coin_data = data[coin_id]
            
            return MarketInfo(
                price=coin_data.get("usd"),
                volume_24h_usd=coin_data.get("usd_24h_vol"),
                price_change_24h=coin_data.get("usd_24h_change")
            )
    
    async def _fetch_from_binance(self, asset: str, session: aiohttp.ClientSession) -> Optional[MarketInfo]:
        """Источник 2: Binance (быстрый, без лимитов)"""
        
        # Binance использует пары типа BTCUSDT
        symbol = f"{asset}USDT"
        
        # Получаем цену
        price_url = f"https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": symbol}
        
        async with session.get(price_url, params=params, timeout=5) as resp:
            if resp.status != 200:
                raise Exception(f"Binance price вернул {resp.status}")
            
            price_data = await resp.json()
            price = float(price_data.get("price", 0))
            
            if price == 0:
                return None
        
        # Получаем 24h статистику
        stats_url = f"https://api.binance.com/api/v3/ticker/24hr"
        
        async with session.get(stats_url, params=params, timeout=5) as resp:
            if resp.status != 200:
                # Цена есть, но без статистики
                return MarketInfo(price=price, volume_24h_usd=None, price_change_24h=None)
            
            stats_data = await resp.json()
            
            volume_24h = float(stats_data.get("quoteVolume", 0))  # в USDT
            price_change = float(stats_data.get("priceChangePercent", 0))
            
            return MarketInfo(
                price=price,
                volume_24h_usd=volume_24h,
                price_change_24h=price_change
            )
    
    async def _fetch_from_coinmarketcap(self, asset: str, session: aiohttp.ClientSession) -> Optional[MarketInfo]:
        """Источник 3: CoinMarketCap (требует API ключ)"""
        
        # Требуется API ключ
        cmc_api_key = os.getenv('COINMARKETCAP_API_KEY')
        if not cmc_api_key:
            return None
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": cmc_api_key,
            "Accept": "application/json"
        }
        params = {
            "symbol": asset,
            "convert": "USD"
        }
        
        async with session.get(url, headers=headers, params=params, timeout=10) as resp:
            if resp.status != 200:
                raise Exception(f"CoinMarketCap вернул {resp.status}")
            
            data = await resp.json()
            
            if "data" not in data or asset not in data["data"]:
                return None
            
            coin_data = data["data"][asset]
            quote = coin_data.get("quote", {}).get("USD", {})
            
            return MarketInfo(
                price=quote.get("price"),
                volume_24h_usd=quote.get("volume_24h"),
                price_change_24h=quote.get("percent_change_24h")
            )
    
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
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
        }
        
        return mapping.get(asset.upper())
    
    async def enrich_event_with_market_data(self, event, session: aiohttp.ClientSession):
        """Обогащает событие рыночными данными"""
        
        old_usd = event.amount_usd
        
        market_info = await self.get_market_info(event.asset, session)
        
        if market_info:
            event.market = market_info
            
            # ВСЕГДА пересчитываем USD если есть реальная цена
            if market_info.price:
                event.amount_usd = event.amount_native * market_info.price
                
                if settings.DEBUG_FILTERS and abs(old_usd - event.amount_usd) > 1:
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