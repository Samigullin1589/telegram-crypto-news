# app/whales/monitor/evm_components/evm_price_provider.py
"""
EVM Price Provider
Получение цен для EVM токенов
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EVMPriceProvider:
    """Провайдер цен для EVM токенов"""
    
    FALLBACK_PRICES = {
        "ETH": 2500.0,
        "BNB": 400.0,
        "MATIC": 0.8,
        "UNKNOWN": 2000.0
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        self.price_cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    async def get_token_price(
        self,
        token_symbol: str,
        chain: str = "ethereum"
    ) -> float:
        """
        Получение цены токена в USD
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена в USD
        """
        # Проверка кэша
        cache_key = f"{chain}:{token_symbol}"
        
        if cache_key in self.price_cache:
            cached_price, cached_time = self.price_cache[cache_key]
            
            if datetime.utcnow() - cached_time < self.cache_ttl:
                logger.debug(f"💰 [PRICE] Используется кэш для {token_symbol}: ${cached_price}")
                return cached_price
        
        # Попытка получить цену из API
        price = await self._fetch_price_from_api(token_symbol, chain)
        
        if price is None:
            # Fallback на дефолтную цену
            price = self.FALLBACK_PRICES.get(token_symbol, self.FALLBACK_PRICES["UNKNOWN"])
            logger.warning(
                f"⚠️ [PRICE] Используется fallback цена для {token_symbol}: ${price}"
            )
        else:
            # Сохранение в кэш
            self.price_cache[cache_key] = (price, datetime.utcnow())
            logger.debug(f"💰 [PRICE] Получена цена для {token_symbol}: ${price}")
        
        return price
    
    async def _fetch_price_from_api(
        self,
        token_symbol: str,
        chain: str
    ) -> Optional[float]:
        """
        Получение цены из CoinGecko API
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена или None
        """
        try:
            # Маппинг символов на CoinGecko IDs
            token_id_map = {
                "ETH": "ethereum",
                "BNB": "binancecoin",
                "MATIC": "matic-network",
                "WETH": "ethereum",
                "WBNB": "binancecoin"
            }
            
            token_id = token_id_map.get(token_symbol.upper())
            
            if not token_id:
                return None
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": token_id,
                "vs_currencies": "usd"
            }
            
            async with self.session.get(
                url,
                params=params,
                timeout=10
            ) as response:
                
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if token_id in data and "usd" in data[token_id]:
                    return float(data[token_id]["usd"])
        
        except asyncio.TimeoutError:
            logger.debug(f"⏱️ [PRICE] Timeout при получении цены {token_symbol}")
        
        except Exception as e:
            logger.debug(f"⚠️ [PRICE] Ошибка получения цены {token_symbol}: {e}")
        
        return None
    
    def clear_cache(self):
        """Очистка кэша цен"""
        self.price_cache.clear()
        logger.debug("🗑️ [PRICE] Кэш цен очищен")