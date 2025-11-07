# app/whales/monitor/cache.py
"""
Transaction Cache for Deduplication
"""

import time
from typing import Dict


class TransactionCache:
    """Кэш транзакций для предотвращения дубликатов"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, float] = {}
        self.ttl = ttl_seconds
    
    def add(self, tx_hash: str):
        """Добавляет транзакцию в кэш"""
        self.cache[tx_hash] = time.time()
        self._cleanup()
    
    def contains(self, tx_hash: str) -> bool:
        """Проверяет наличие транзакции в кэше"""
        self._cleanup()
        return tx_hash in self.cache
    
    def _cleanup(self):
        """Удаляет устаревшие записи"""
        now = time.time()
        to_remove = [
            tx_hash for tx_hash, timestamp in self.cache.items()
            if now - timestamp > self.ttl
        ]
        for tx_hash in to_remove:
            del self.cache[tx_hash]