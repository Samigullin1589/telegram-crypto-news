# app/config/blockchain/chain_thresholds.py
"""
Chain Thresholds Module
Управление порогами для whale транзакций
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ChainThresholds:
    """
    Управление порогами whale транзакций для блокчейнов
    
    Пороги включают:
    - min_native_value: минимум нативной валюты
    - min_usd_value: минимум в USD для обработки
    - whale_threshold_usd: порог для whale
    - mega_whale_threshold_usd: порог для mega whale
    """
    
    def __init__(self):
        """Инициализация порогов"""
        self._thresholds = self._initialize_thresholds()
        self._default_threshold = self._get_default_threshold()
        
        logger.debug(f"Chain thresholds initialized for {len(self._thresholds)} chains")
    
    @staticmethod
    def _initialize_thresholds() -> Dict[str, Dict[str, float]]:
        """
        Инициализация порогов для всех поддерживаемых блокчейнов
        
        Returns:
            Словарь с порогами для каждого блокчейна
        """
        return {
            'ethereum': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'bsc': {
                'min_native_value': 100.0,
                'min_usd_value': 50000.0,
                'whale_threshold_usd': 500000.0,
                'mega_whale_threshold_usd': 5000000.0
            },
            'polygon': {
                'min_native_value': 50000.0,
                'min_usd_value': 25000.0,
                'whale_threshold_usd': 250000.0,
                'mega_whale_threshold_usd': 2500000.0
            },
            'arbitrum': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'optimism': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'base': {
                'min_native_value': 50.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            },
            'avalanche': {
                'min_native_value': 500.0,
                'min_usd_value': 15000.0,
                'whale_threshold_usd': 150000.0,
                'mega_whale_threshold_usd': 1500000.0
            },
            'solana': {
                'min_native_value': 100.0,
                'min_usd_value': 10000.0,
                'whale_threshold_usd': 100000.0,
                'mega_whale_threshold_usd': 1000000.0
            },
            'fantom': {
                'min_native_value': 10000.0,
                'min_usd_value': 5000.0,
                'whale_threshold_usd': 50000.0,
                'mega_whale_threshold_usd': 500000.0
            },
            'tron': {
                'min_native_value': 1000000.0,
                'min_usd_value': 100000.0,
                'whale_threshold_usd': 1000000.0,
                'mega_whale_threshold_usd': 10000000.0
            }
        }
    
    @staticmethod
    def _get_default_threshold() -> Dict[str, float]:
        """
        Получение дефолтных порогов для неизвестных блокчейнов
        
        Returns:
            Словарь с дефолтными значениями
        """
        return {
            'min_native_value': 10.0,
            'min_usd_value': 10000.0,
            'whale_threshold_usd': 100000.0,
            'mega_whale_threshold_usd': 1000000.0
        }
    
    def get_threshold(self, chain: str) -> Dict[str, float]:
        """
        Получение порогов для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Словарь с порогами
        """
        chain_lower = chain.lower()
        return self._thresholds.get(chain_lower, self._default_threshold.copy())
    
    def get_min_usd_value(self, chain: str) -> float:
        """
        Получение минимального порога в USD
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Минимальная сумма в USD
        """
        threshold = self.get_threshold(chain)
        return threshold['min_usd_value']
    
    def get_min_native_value(self, chain: str) -> float:
        """
        Получение минимального количества нативной валюты
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Минимальное количество нативной валюты
        """
        threshold = self.get_threshold(chain)
        return threshold['min_native_value']
    
    def get_whale_threshold_usd(self, chain: str) -> float:
        """
        Получение порога whale в USD
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Порог whale в USD
        """
        threshold = self.get_threshold(chain)
        return threshold['whale_threshold_usd']
    
    def get_mega_whale_threshold_usd(self, chain: str) -> float:
        """
        Получение порога mega whale в USD
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Порог mega whale в USD
        """
        threshold = self.get_threshold(chain)
        return threshold['mega_whale_threshold_usd']
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка является ли транзакция whale
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает whale порог
        """
        whale_threshold = self.get_whale_threshold_usd(chain)
        return usd_value >= whale_threshold
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка является ли транзакция mega whale
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает mega whale порог
        """
        mega_whale_threshold = self.get_mega_whale_threshold_usd(chain)
        return usd_value >= mega_whale_threshold
    
    def get_transaction_category(self, chain: str, usd_value: float) -> str:
        """
        Определение категории транзакции по сумме
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            Категория: 'mega_whale', 'whale', 'large', или 'normal'
        """
        if self.is_mega_whale_transaction(chain, usd_value):
            return 'mega_whale'
        elif self.is_whale_transaction(chain, usd_value):
            return 'whale'
        elif usd_value >= self.get_min_usd_value(chain):
            return 'large'
        else:
            return 'normal'
    
    def should_process_transaction(self, chain: str, usd_value: float) -> bool:
        """
        Проверка нужно ли обрабатывать транзакцию
        
        Args:
            chain: Название блокчейна
            usd_value: Сумма транзакции в USD
            
        Returns:
            True если транзакция превышает минимальный порог
        """
        min_usd = self.get_min_usd_value(chain)
        return usd_value >= min_usd
    
    def get_all_chains(self) -> List[str]:
        """
        Получение списка всех поддерживаемых блокчейнов
        
        Returns:
            Список названий блокчейнов
        """
        return list(self._thresholds.keys())
    
    def has_chain(self, chain: str) -> bool:
        """
        Проверка наличия порогов для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если пороги определены
        """
        return chain.lower() in self._thresholds