# app/whales/monitor/evm_components/evm_price_provider.py
"""
EVM Price Provider v4.0
Главный провайдер цен с продвинутой архитектурой и надежностью
"""

import logging
from typing import Optional, Dict
from enum import Enum

from .price_cache import PriceCache
from .price_sources import (
    CoinGeckoProvider,
    CoinCapProvider,
    CryptoCompareProvider
)
from .price_aggregator import PriceAggregator

logger = logging.getLogger(__name__)


class PriceSource(str, Enum):
    """Источники цен"""
    API = "api"
    FALLBACK = "fallback"


class EVMPriceProvider:
    """
    Главный провайдер цен для EVM токенов
    
    Features:
    - Множественные API источники с fallback
    - Circuit breaker для защиты от недоступных сервисов
    - Умное кэширование с TTL
    - Агрегация цен через median/average
    - Статистика использования
    """
    
    FALLBACK_PRICES = {
        "ETH": 3200.0,
        "BNB": 620.0,
        "MATIC": 0.85,
        "POL": 0.85,
        "AVAX": 38.0,
        "FTM": 0.65,
        "OP": 2.5,
        "ARB": 0.95,
        "ONE": 0.015,
        "CELO": 0.65,
        "GLMR": 0.35,
        "MOVR": 12.0,
        "UNKNOWN": 1000.0
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession для HTTP запросов
        """
        self.session = session
        
        self.cache = PriceCache(ttl_minutes=5)
        
        self.coingecko = CoinGeckoProvider(session)
        self.coincap = CoinCapProvider(session)
        self.cryptocompare = CryptoCompareProvider(session)
        
        self.aggregator = PriceAggregator([
            self.coingecko,
            self.coincap,
            self.cryptocompare
        ])
        
        self.source_stats = {
            PriceSource.API: 0,
            PriceSource.FALLBACK: 0
        }
        
        self.fallback_count = 0
        self.api_success_count = 0
        
        logger.info("🔧 [PRICE] EVMPriceProvider инициализирован")
        logger.info(f"📊 [PRICE] Активные источники: CoinGecko, CoinCap, CryptoCompare")
    
    async def get_token_price(
        self,
        token_symbol: str,
        chain: str = "ethereum"
    ) -> float:
        """
        Получение цены токена в USD
        
        Args:
            token_symbol: Символ токена (ETH, BNB, MATIC)
            chain: Название блокчейна
            
        Returns:
            Цена в USD
        """
        normalized_symbol = token_symbol.upper().strip()
        
        cached_price = self.cache.get(normalized_symbol, chain)
        if cached_price is not None:
            return cached_price
        
        price = await self.aggregator.get_price(normalized_symbol, chain)
        
        if price is not None and price > 0:
            self.cache.set(normalized_symbol, chain, price)
            self.source_stats[PriceSource.API] += 1
            self.api_success_count += 1
            return price
        
        fallback_price = self._get_fallback_price(normalized_symbol)
        self.cache.set(normalized_symbol, chain, fallback_price)
        self.source_stats[PriceSource.FALLBACK] += 1
        self.fallback_count += 1
        
        if self.fallback_count % 10 == 1:
            logger.warning(
                f"⚠️ [PRICE] Используется fallback цена для {normalized_symbol}: "
                f"${fallback_price:,.2f} (API недоступны, fallback count: {self.fallback_count})"
            )
        
        return fallback_price
    
    def _get_fallback_price(self, token_symbol: str) -> float:
        """
        Получение fallback цены
        
        Args:
            token_symbol: Символ токена
            
        Returns:
            Fallback цена
        """
        return self.FALLBACK_PRICES.get(
            token_symbol,
            self.FALLBACK_PRICES["UNKNOWN"]
        )
    
    def get_stats(self) -> Dict:
        """
        Получение статистики работы провайдера
        
        Returns:
            Словарь со статистикой
        """
        total = sum(self.source_stats.values())
        
        cache_stats = self.cache.get_stats()
        
        provider_stats = {
            "coingecko": self.coingecko.get_stats(),
            "coincap": self.coincap.get_stats(),
            "cryptocompare": self.cryptocompare.get_stats()
        }
        
        usage_stats = {}
        if total > 0:
            usage_stats = {
                source.value: round((count / total) * 100, 2)
                for source, count in self.source_stats.items()
            }
        
        return {
            "usage": usage_stats,
            "cache": cache_stats,
            "providers": provider_stats,
            "api_success_count": self.api_success_count,
            "fallback_count": self.fallback_count
        }
    
    def clear_cache(self) -> None:
        """Очистка кэша цен"""
        self.cache.clear()
        logger.info("🗑️ [PRICE] Кэш цен очищен")
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Проверка здоровья всех источников
        
        Returns:
            Статус каждого источника
        """
        results = {}
        
        test_token = "ETH"
        test_chain = "ethereum"
        
        for name, provider in [
            ("coingecko", self.coingecko),
            ("coincap", self.coincap),
            ("cryptocompare", self.cryptocompare)
        ]:
            try:
                price = await provider.get_price(test_token, test_chain)
                results[name] = price is not None and price > 0
            except Exception:
                results[name] = False
        
        return results