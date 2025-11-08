# app/config/blockchain/chain_explorers.py
"""
Chain Explorers Module
Управление URL блокчейн эксплореров
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ChainExplorers:
    """
    Управление URL блокчейн эксплореров
    
    Эксплореры используются для создания ссылок на:
    - Транзакции (tx hash)
    - Адреса кошельков
    - Блоки
    """
    
    def __init__(self):
        """Инициализация эксплореров"""
        self._base_urls = self._initialize_base_urls()
        self._url_patterns = self._initialize_url_patterns()
        
        logger.debug(f"Chain explorers initialized for {len(self._base_urls)} chains")
    
    @staticmethod
    def _initialize_base_urls() -> Dict[str, str]:
        """
        Инициализация базовых URL эксплореров
        
        Returns:
            Словарь с базовыми URL для каждого блокчейна
        """
        return {
            'ethereum': 'https://etherscan.io',
            'bsc': 'https://bscscan.com',
            'polygon': 'https://polygonscan.com',
            'arbitrum': 'https://arbiscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'base': 'https://basescan.org',
            'avalanche': 'https://snowtrace.io',
            'solana': 'https://solscan.io',
            'fantom': 'https://ftmscan.com',
            'tron': 'https://tronscan.org'
        }
    
    @staticmethod
    def _initialize_url_patterns() -> Dict[str, Dict[str, str]]:
        """
        Инициализация паттернов URL для разных типов данных
        
        Returns:
            Словарь с паттернами URL для транзакций и адресов
        """
        return {
            'ethereum': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'bsc': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'polygon': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'arbitrum': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'optimism': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'base': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'avalanche': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'solana': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'fantom': {
                'tx': '/tx/{hash}',
                'address': '/address/{address}'
            },
            'tron': {
                'tx': '/#/transaction/{hash}',
                'address': '/#/address/{address}'
            }
        }
    
    def get_base_url(self, chain: str) -> str:
        """
        Получение базового URL эксплорера
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Базовый URL эксплорера или пустая строка
        """
        chain_lower = chain.lower()
        url = self._base_urls.get(chain_lower, '')
        
        if not url:
            logger.warning(f"Explorer URL not found for chain: {chain}")
        
        return url
    
    def get_url(
        self,
        chain: str,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> str:
        """
        Получение полного URL эксплорера
        
        Args:
            chain: Название блокчейна
            address: Адрес кошелька (опционально)
            tx_hash: Хэш транзакции (опционально)
            
        Returns:
            Полный URL эксплорера или пустая строка
        """
        base_url = self.get_base_url(chain)
        
        if not base_url:
            return ''
        
        if tx_hash:
            return self._build_transaction_url(chain, base_url, tx_hash)
        elif address:
            return self._build_address_url(chain, base_url, address)
        else:
            return base_url
    
    def _build_transaction_url(self, chain: str, base_url: str, tx_hash: str) -> str:
        """
        Построение URL транзакции
        
        Args:
            chain: Название блокчейна
            base_url: Базовый URL
            tx_hash: Хэш транзакции
            
        Returns:
            Полный URL транзакции
        """
        chain_lower = chain.lower()
        patterns = self._url_patterns.get(chain_lower, {})
        tx_pattern = patterns.get('tx', '/tx/{hash}')
        
        path = tx_pattern.format(hash=tx_hash)
        return f"{base_url}{path}"
    
    def _build_address_url(self, chain: str, base_url: str, address: str) -> str:
        """
        Построение URL адреса
        
        Args:
            chain: Название блокчейна
            base_url: Базовый URL
            address: Адрес кошелька
            
        Returns:
            Полный URL адреса
        """
        chain_lower = chain.lower()
        patterns = self._url_patterns.get(chain_lower, {})
        address_pattern = patterns.get('address', '/address/{address}')
        
        path = address_pattern.format(address=address)
        return f"{base_url}{path}"
    
    def has_explorer(self, chain: str) -> bool:
        """
        Проверка наличия эксплорера для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если эксплорер определен
        """
        return chain.lower() in self._base_urls
    
    def get_all_chains(self) -> list:
        """
        Получение списка всех блокчейнов с эксплорерами
        
        Returns:
            Список названий блокчейнов
        """
        return list(self._base_urls.keys())