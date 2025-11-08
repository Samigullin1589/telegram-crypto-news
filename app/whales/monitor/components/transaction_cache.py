# app/whales/monitor/components/transaction_cache.py
"""
Transaction Cache
Кэш для отслеживания уже обработанных транзакций
"""

import logging
from collections import OrderedDict
from typing import Set

logger = logging.getLogger(__name__)


class TransactionCache:
    """Кэш обработанных транзакций с LRU вытеснением"""
    
    def __init__(self, max_size: int = 10000):
        """
        Args:
            max_size: Максимальный размер кэша
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, bool] = OrderedDict()
        
        logger.debug(f"🔧 [CACHE] Инициализирован с max_size={max_size}")
    
    def contains(self, tx_hash: str) -> bool:
        """
        Проверка наличия транзакции в кэше
        
        Args:
            tx_hash: Хэш транзакции
            
        Returns:
            True если транзакция уже обработана
        """
        return tx_hash in self.cache
    
    def add(self, tx_hash: str):
        """
        Добавление транзакции в кэш
        
        Args:
            tx_hash: Хэш транзакции
        """
        if tx_hash in self.cache:
            # Перемещение в конец (обновление времени использования)
            self.cache.move_to_end(tx_hash)
        else:
            # Добавление новой транзакции
            self.cache[tx_hash] = True
            
            # Вытеснение старых при превышении лимита
            if len(self.cache) > self.max_size:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                logger.debug(f"🗑️ [CACHE] Вытеснена старая транзакция: {oldest[:16]}...")
    
    def clear(self):
        """Очистка кэша"""
        self.cache.clear()
        logger.debug("🗑️ [CACHE] Кэш очищен")
    
    def size(self) -> int:
        """
        Текущий размер кэша
        
        Returns:
            Количество транзакций в кэше
        """
        return len(self.cache)
    
    def get_stats(self) -> dict:
        """
        Получение статистики кэша
        
        Returns:
            Dict со статистикой
        """
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization_percent': round((len(self.cache) / self.max_size) * 100, 2)
        }