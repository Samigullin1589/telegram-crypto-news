# app/whales/monitor/solana_components/solana_price_provider.py
"""
Solana Price Provider
Получение цен для Solana токенов
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SolanaPriceProvider:
    """Провайдер цен для Solana токенов"""
    
    FALLBACK_PRICES = {
        "SOL": 150.0,
        "USDC": 1.0,
        "USDT": 1.0
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        self.price_cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    async def get_token_price(self, token_symbol: str) -> float:
        """
        Получение цены токена в USD
        
        Args:
            token_symbol: Символ токена
            
        Returns:
            Цена в USD
        """
        # Проверка кэша
        cache_key = token_symbol.upper()
        
        if cache_key in self.price_cache:
            cached_price, cached_time = self.price_cache[cache_key]
            
            if datetime.utcnow() - cached_time < self.cache_ttl:
                logger.debug(f"💰 [SOLANA PRICE] Кэш для {token_symbol}: ${cached_price}")
                return cached_price
        
        # Попытка получить цену из API
        price = await self._fetch_price_from_api(token_symbol)
        
        if price is None:
            # Fallback на дефолтную цену
            price = self.FALLBACK_PRICES.get(cache_key, 100.0)
            logger.warning(
                f"⚠️ [SOLANA PRICE] Fallback цена для {token_symbol}: ${price}"
            )
        else:
            # Сохранение в кэш
            self.price_cache[cache_key] = (price, datetime.utcnow())
            logger.debug(f"💰 [SOLANA PRICE] Получена цена {token_symbol}: ${price}")
        
        return price
    
    async def _fetch_price_from_api(self, token_symbol: str) -> Optional[float]:
        """
        Получение цены из CoinGecko API
        
        Args:
            token_symbol: Символ токена
            
        Returns:
            Цена или None
        """
        try:
            # Маппинг токенов на CoinGecko IDs
            token_map = {
                "SOL": "solana",
                "USDC": "usd-coin",
                "USDT": "tether"
            }
            
            token_id = token_map.get(token_symbol.upper())
            
            if not token_id:
                return None
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": token_id,
                "vs_currencies": "usd"
            }
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if token_id in data and "usd" in data[token_id]:
                    return float(data[token_id]["usd"])
        
        except asyncio.TimeoutError:
            logger.debug(f"⏱️ [SOLANA PRICE] Timeout для {token_symbol}")
        
        except Exception as e:
            logger.debug(f"⚠️ [SOLANA PRICE] Ошибка для {token_symbol}: {e}")
        
        return None