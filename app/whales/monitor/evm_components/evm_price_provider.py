# app/whales/monitor/evm_components/evm_price_provider.py
"""
EVM Price Provider v3.0
Продвинутая система получения цен с множественными источниками и умным кэшированием
"""

import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PriceSource(str, Enum):
    """Источники цен"""
    COINGECKO = "coingecko"
    COINCAP = "coincap"
    FALLBACK = "fallback"


class EVMPriceProvider:
    """
    Главный провайдер цен для EVM токенов
    Использует несколько источников с автоматическим переключением
    """
    
    FALLBACK_PRICES = {
        "ETH": 3200.0,
        "BNB": 620.0,
        "MATIC": 0.85,
        "AVAX": 38.0,
        "FTM": 0.65,
        "UNKNOWN": 1000.0
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        
        # Инициализация компонентов
        self.cache = PriceCache(ttl_minutes=5)
        self.coingecko = CoinGeckoProvider(session)
        self.coincap = CoinCapProvider(session)
        self.aggregator = PriceAggregator([self.coingecko, self.coincap])
        
        # Статистика использования источников
        self.source_stats = {
            PriceSource.COINGECKO: 0,
            PriceSource.COINCAP: 0,
            PriceSource.FALLBACK: 0
        }
        
        logger.info("🔧 [PRICE] EVMPriceProvider инициализирован")
    
    async def get_token_price(
        self,
        token_symbol: str,
        chain: str = "ethereum"
    ) -> float:
        """
        Получение цены токена в USD с автоматическим fallback
        
        Args:
            token_symbol: Символ токена (ETH, BNB, etc)
            chain: Название блокчейна
            
        Returns:
            Цена в USD
        """
        # Нормализация символа
        normalized_symbol = token_symbol.upper().strip()
        
        # Проверка кэша
        cached_price = self.cache.get(normalized_symbol, chain)
        if cached_price is not None:
            logger.debug(
                f"💰 [PRICE] Кэш hit для {normalized_symbol}: ${cached_price:,.2f}"
            )
            return cached_price
        
        # Получение цены из источников
        price, source = await self._fetch_price_with_fallback(normalized_symbol, chain)
        
        # Сохранение в кэш
        if price is not None:
            self.cache.set(normalized_symbol, chain, price)
            self.source_stats[source] += 1
            
            if source == PriceSource.FALLBACK:
                logger.warning(
                    f"⚠️ [PRICE] Fallback цена для {normalized_symbol}: ${price:,.2f}"
                )
            else:
                logger.debug(
                    f"💰 [PRICE] Цена {normalized_symbol} получена из {source.value}: ${price:,.2f}"
                )
        
        return price
    
    async def _fetch_price_with_fallback(
        self,
        token_symbol: str,
        chain: str
    ) -> Tuple[float, PriceSource]:
        """
        Получение цены с автоматическим fallback между источниками
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            (цена, источник)
        """
        # Попытка получить из агрегатора (пробует все источники)
        price = await self.aggregator.get_price(token_symbol, chain)
        
        if price is not None:
            # Определение использованного источника
            if self.coingecko.last_request_success:
                return price, PriceSource.COINGECKO
            else:
                return price, PriceSource.COINCAP
        
        # Fallback на дефолтные цены
        fallback_price = self.FALLBACK_PRICES.get(
            token_symbol,
            self.FALLBACK_PRICES["UNKNOWN"]
        )
        
        return fallback_price, PriceSource.FALLBACK
    
    def get_stats(self) -> Dict:
        """
        Получение статистики использования источников
        
        Returns:
            Dict со статистикой
        """
        total = sum(self.source_stats.values())
        
        if total == 0:
            return {source.value: 0.0 for source in PriceSource}
        
        return {
            source.value: round((count / total) * 100, 2)
            for source, count in self.source_stats.items()
        }
    
    def clear_cache(self):
        """Очистка кэша цен"""
        self.cache.clear()
        logger.info("🗑️ [PRICE] Кэш цен очищен")


class PriceCache:
    """
    Умный кэш цен с TTL
    Хранит цены с временными метками
    """
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Args:
            ttl_minutes: Time-to-live в минутах
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: Dict[str, Tuple[float, datetime]] = {}
    
    def get(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из кэша
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена или None если устарела
        """
        cache_key = f"{chain}:{token_symbol}"
        
        if cache_key not in self.cache:
            return None
        
        price, cached_time = self.cache[cache_key]
        
        # Проверка актуальности
        if datetime.utcnow() - cached_time > self.ttl:
            # Удаление устаревшей записи
            del self.cache[cache_key]
            return None
        
        return price
    
    def set(self, token_symbol: str, chain: str, price: float):
        """
        Сохранение цены в кэш
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            price: Цена
        """
        cache_key = f"{chain}:{token_symbol}"
        self.cache[cache_key] = (price, datetime.utcnow())
    
    def clear(self):
        """Очистка всего кэша"""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Удаление устаревших записей"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, cached_time) in self.cache.items()
            if now - cached_time > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"🗑️ [CACHE] Удалено {len(expired_keys)} устаревших записей")


class CoinGeckoProvider:
    """
    Провайдер цен CoinGecko
    Free API с rate limiting
    """
    
    # Расширенный маппинг токенов
    TOKEN_ID_MAP = {
        "ETH": "ethereum",
        "WETH": "ethereum",
        "BNB": "binancecoin",
        "WBNB": "binancecoin",
        "MATIC": "matic-network",
        "WMATIC": "matic-network",
        "AVAX": "avalanche-2",
        "WAVAX": "avalanche-2",
        "FTM": "fantom",
        "WFTM": "fantom",
        "OP": "optimism",
        "ARB": "arbitrum",
        "BASE": "base",
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        self.base_url = "https://api.coingecko.com/api/v3"
        self.last_request_success = False
        self.request_timeout = 10
        self.max_retries = 2
    
    async def get_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из CoinGecko
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна (не используется)
            
        Returns:
            Цена или None
        """
        token_id = self.TOKEN_ID_MAP.get(token_symbol)
        
        if not token_id:
            logger.debug(f"⚠️ [COINGECKO] Неизвестный токен: {token_symbol}")
            return None
        
        # Попытки с retry
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/simple/price"
                params = {
                    "ids": token_id,
                    "vs_currencies": "usd"
                }
                
                async with self.session.get(
                    url,
                    params=params,
                    timeout=self.request_timeout
                ) as response:
                    
                    if response.status == 429:
                        # Rate limited
                        logger.debug(f"⏱️ [COINGECKO] Rate limited, попытка {attempt + 1}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    
                    if response.status != 200:
                        logger.debug(
                            f"⚠️ [COINGECKO] HTTP {response.status} для {token_symbol}"
                        )
                        continue
                    
                    data = await response.json()
                    
                    if token_id in data and "usd" in data[token_id]:
                        price = float(data[token_id]["usd"])
                        self.last_request_success = True
                        logger.debug(
                            f"✅ [COINGECKO] Получена цена {token_symbol}: ${price:,.2f}"
                        )
                        return price
            
            except asyncio.TimeoutError:
                logger.debug(
                    f"⏱️ [COINGECKO] Timeout для {token_symbol} "
                    f"(попытка {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(1)
                continue
            
            except Exception as e:
                logger.debug(f"⚠️ [COINGECKO] Ошибка для {token_symbol}: {e}")
                continue
        
        self.last_request_success = False
        return None


class CoinCapProvider:
    """
    Провайдер цен CoinCap
    Альтернативный free API
    """
    
    # Маппинг токенов для CoinCap
    TOKEN_ID_MAP = {
        "ETH": "ethereum",
        "WETH": "ethereum",
        "BNB": "binance-coin",
        "WBNB": "binance-coin",
        "MATIC": "polygon",
        "WMATIC": "polygon",
        "AVAX": "avalanche",
        "WAVAX": "avalanche",
        "FTM": "fantom",
        "WFTM": "fantom",
    }
    
    def __init__(self, session):
        """
        Args:
            session: aiohttp ClientSession
        """
        self.session = session
        self.base_url = "https://api.coincap.io/v2"
        self.last_request_success = False
        self.request_timeout = 10
    
    async def get_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из CoinCap
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна (не используется)
            
        Returns:
            Цена или None
        """
        token_id = self.TOKEN_ID_MAP.get(token_symbol)
        
        if not token_id:
            return None
        
        try:
            url = f"{self.base_url}/assets/{token_id}"
            
            async with self.session.get(
                url,
                timeout=self.request_timeout
            ) as response:
                
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if "data" in data and "priceUsd" in data["data"]:
                    price = float(data["data"]["priceUsd"])
                    self.last_request_success = True
                    logger.debug(
                        f"✅ [COINCAP] Получена цена {token_symbol}: ${price:,.2f}"
                    )
                    return price
        
        except asyncio.TimeoutError:
            logger.debug(f"⏱️ [COINCAP] Timeout для {token_symbol}")
        
        except Exception as e:
            logger.debug(f"⚠️ [COINCAP] Ошибка для {token_symbol}: {e}")
        
        self.last_request_success = False
        return None


class PriceAggregator:
    """
    Агрегатор цен из нескольких источников
    Пробует источники по порядку приоритета
    """
    
    def __init__(self, providers: List):
        """
        Args:
            providers: Список провайдеров в порядке приоритета
        """
        self.providers = providers
    
    async def get_price(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены с fallback между провайдерами
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            
        Returns:
            Цена или None
        """
        for provider in self.providers:
            try:
                price = await provider.get_price(token_symbol, chain)
                
                if price is not None and price > 0:
                    return price
            
            except Exception as e:
                logger.debug(
                    f"⚠️ [AGGREGATOR] Ошибка в {provider.__class__.__name__}: {e}"
                )
                continue
        
        return None