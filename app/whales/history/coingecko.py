# app/whales/history/coingecko.py
"""
CoinGecko API Integration
"""

import asyncio
from typing import Optional
from datetime import datetime

import aiohttp

from app.config import config


class CoinGeckoClient:
    """Клиент для CoinGecko API"""
    
    COIN_IDS = {
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
        "AAVE": "aave",
        "DOT": "polkadot",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "SHIB": "shiba-inu"
    }
    
    def __init__(self):
        # ИСПРАВЛЕНО: Безопасный доступ к config.api.coingecko_api_key
        _api = getattr(config, 'api', None)
        self.api_key = getattr(_api, 'coingecko_api_key', '') if _api else ''
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def get_coin_id(self, asset: str) -> Optional[str]:
        """Получает CoinGecko ID для актива"""
        return self.COIN_IDS.get(asset.upper())
    
    async def get_historical_price(
        self,
        coin_id: str,
        target_time: datetime,
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """
        Получает историческую цену из CoinGecko
        
        Args:
            coin_id: CoinGecko ID
            target_time: Целевое время
            session: aiohttp сессия
        
        Returns:
            Цена в USD или None
        """
        try:
            date_str = target_time.strftime("%d-%m-%Y")
            
            url = f"{self.base_url}/coins/{coin_id}/history"
            params = {
                "date": date_str,
                "localization": "false"
            }
            
            if self.api_key:
                params["x_cg_pro_api_key"] = self.api_key
            
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
        
        except asyncio.TimeoutError:
            return None
        
        except Exception:
            return None