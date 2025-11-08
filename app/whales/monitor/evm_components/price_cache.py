# app/whales/monitor/evm_components/price_cache.py
"""
Price Cache Module
Умное кэширование цен токенов с TTL и автоматической очисткой
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PriceCache:
    """
    Кэш цен токенов с временными метками и автоматической очисткой
    Поддерживает разные TTL для разных типов данных
    """
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Args:
            ttl_minutes: Время жизни записи в минутах
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: Dict[str, Tuple[float, datetime]] = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, token_symbol: str, chain: str) -> Optional[float]:
        """
        Получение цены из кэша
        
        Args:
            token_symbol: Символ токена (ETH, BNB)
            chain: Название блокчейна
            
        Returns:
            Цена в USD или None если не найдено/устарело
        """
        cache_key = self._make_key(token_symbol, chain)
        
        if cache_key not in self.cache:
            self.misses += 1
            return None
        
        price, cached_time = self.cache[cache_key]
        
        if datetime.utcnow() - cached_time > self.ttl:
            del self.cache[cache_key]
            self.misses += 1
            return None
        
        self.hits += 1
        return price
    
    def set(self, token_symbol: str, chain: str, price: float) -> None:
        """
        Сохранение цены в кэш
        
        Args:
            token_symbol: Символ токена
            chain: Название блокчейна
            price: Цена в USD
        """
        cache_key = self._make_key(token_symbol, chain)
        self.cache[cache_key] = (price, datetime.utcnow())
    
    def clear(self) -> None:
        """Полная очистка кэша"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def cleanup_expired(self) -> int:
        """
        Удаление устаревших записей
        
        Returns:
            Количество удаленных записей
        """
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, cached_time) in self.cache.items()
            if now - cached_time > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, any]:
        """
        Статистика работы кэша
        
        Returns:
            Словарь со статистикой
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2)
        }
    
    @staticmethod
    def _make_key(token_symbol: str, chain: str) -> str:
        """Создание ключа кэша"""
        return f"{chain}:{token_symbol.upper()}"