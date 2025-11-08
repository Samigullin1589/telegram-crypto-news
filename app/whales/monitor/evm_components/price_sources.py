# app/whales/monitor/evm_components/price_sources.py
"""
Price Data Sources
Провайдеры данных о ценах из различных API
"""

import asyncio
import logging
from typing import Optional, Dict
from abc import ABC, abstractmethod

from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PriceSourceBase(ABC):
    """Базовый класс для источников цен"""
    
    def __init__(self, session, name: str):
        """
        Args:
            session: aiohttp ClientSession
            name: Название источника
        """
        self.session = session
        self.name = name
        self.circuit_breaker = CircuitBreaker(
            name=name,
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2
        )
        self.request_timeout = 10
        self.max_retries = 3
    
    @abstractmethod
    async def fetch_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """Получение цены (должен реализовать наследник)"""
        pass
    
    async def get_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены с circuit breaker и retry logic
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена в USD или None
        """
        if not self.circuit_breaker.can_execute():
            return None
        
        for attempt in range(self.max_retries):
            try:
                price = await self.fetch_price(token_symbol, chain)
                
                if price is not None and price > 0:
                    self.circuit_breaker.record_success()
                    return price
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                else:
                    await asyncio.sleep(1)
            
            except Exception as e:
                logger.debug(f"⚠️ [{self.name}] Ошибка для {token_symbol}: {e}")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                else:
                    await asyncio.sleep(1)
        
        self.circuit_breaker.record_failure()
        return None
    
    def get_stats(self) -> Dict[str, any]:
        """Статистика источника"""
        return self.circuit_breaker.get_stats()


class CoinGeckoProvider(PriceSourceBase):
    """
    Провайдер CoinGecko API
    Free tier: 10-50 запросов/минуту
    """
    
    TOKEN_ID_MAP = {
        "ETH": "ethereum",
        "WETH": "ethereum",
        "BNB": "binancecoin",
        "WBNB": "binancecoin",
        "MATIC": "matic-network",
        "WMATIC": "matic-network",
        "POL": "matic-network",
        "WPOL": "matic-network",
        "AVAX": "avalanche-2",
        "WAVAX": "avalanche-2",
        "FTM": "fantom",
        "WFTM": "fantom",
        "OP": "optimism",
        "ARB": "arbitrum",
        "ONE": "harmony",
        "WONE": "harmony",
        "CELO": "celo",
        "GLMR": "moonbeam",
        "MOVR": "moonriver",
    }
    
    def __init__(self, session):
        super().__init__(session, "COINGECKO")
        self.base_url = "https://api.coingecko.com/api/v3"
    
    async def fetch_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из CoinGecko API
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена в USD или None
        """
        token_id = self.TOKEN_ID_MAP.get(token_symbol.upper())
        
        if not token_id:
            return None
        
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": token_id,
            "vs_currencies": "usd",
            "precision": 2
        }
        
        async with self.session.get(
            url,
            params=params,
            timeout=self.request_timeout
        ) as response:
            
            if response.status == 429:
                await asyncio.sleep(2)
                raise Exception("Rate limited")
            
            if response.status != 200:
                return None
            
            data = await response.json()
            
            if token_id in data and "usd" in data[token_id]:
                return float(data[token_id]["usd"])
        
        return None


class CoinCapProvider(PriceSourceBase):
    """
    Провайдер CoinCap API
    Free tier: без ограничений (с разумным rate limit)
    """
    
    TOKEN_ID_MAP = {
        "ETH": "ethereum",
        "WETH": "ethereum",
        "BNB": "binance-coin",
        "WBNB": "binance-coin",
        "MATIC": "polygon",
        "WMATIC": "polygon",
        "POL": "polygon",
        "WPOL": "polygon",
        "AVAX": "avalanche",
        "WAVAX": "avalanche",
        "FTM": "fantom",
        "WFTM": "fantom",
        "OP": "optimism",
        "ARB": "arbitrum",
    }
    
    def __init__(self, session):
        super().__init__(session, "COINCAP")
        self.base_url = "https://api.coincap.io/v2"
    
    async def fetch_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из CoinCap API
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена в USD или None
        """
        token_id = self.TOKEN_ID_MAP.get(token_symbol.upper())
        
        if not token_id:
            return None
        
        url = f"{self.base_url}/assets/{token_id}"
        
        async with self.session.get(
            url,
            timeout=self.request_timeout
        ) as response:
            
            if response.status != 200:
                return None
            
            data = await response.json()
            
            if "data" in data and "priceUsd" in data["data"]:
                return float(data["data"]["priceUsd"])
        
        return None


class CryptoCompareProvider(PriceSourceBase):
    """
    Провайдер CryptoCompare API
    Free tier: 100,000 запросов/месяц
    """
    
    def __init__(self, session):
        super().__init__(session, "CRYPTOCOMPARE")
        self.base_url = "https://min-api.cryptocompare.com/data"
    
    async def fetch_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из CryptoCompare API
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена в USD или None
        """
        url = f"{self.base_url}/price"
        params = {
            "fsym": token_symbol.upper(),
            "tsyms": "USD"
        }
        
        async with self.session.get(
            url,
            params=params,
            timeout=self.request_timeout
        ) as response:
            
            if response.status != 200:
                return None
            
            data = await response.json()
            
            if "USD" in data:
                return float(data["USD"])
        
        return None