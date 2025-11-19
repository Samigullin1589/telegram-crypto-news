# app/config/blockchain/chain_metadata.py
"""
Chain Metadata Module
Управление метаданными блокчейнов (символы, имена, цвета, emoji)
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ChainMetadata:
    """
    Управление метаданными блокчейнов
    
    Включает:
    - Нативные символы валют (ETH, BNB, SOL)
    - Полные названия сетей
    - Цвета для UI (hex codes)
    - Emoji для визуального отображения
    """
    
    def __init__(self):
        """Инициализация метаданных"""
        self._symbols = self._initialize_symbols()
        self._names = self._initialize_names()
        self._colors = self._initialize_colors()
        self._emojis = self._initialize_emojis()
        
        logger.debug(f"Chain metadata initialized for {len(self._symbols)} chains")
    
    @staticmethod
    def _initialize_symbols() -> Dict[str, str]:
        """
        Инициализация нативных символов валют
        
        Returns:
            Словарь с символами для каждого блокчейна
        """
        return {
            'ethereum': 'ETH',
            'bsc': 'BNB',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'optimism': 'ETH',
            'base': 'ETH',
            'avalanche': 'AVAX',
            'solana': 'SOL',
            'fantom': 'FTM',
            'tron': 'TRX'
        }
    
    @staticmethod
    def _initialize_names() -> Dict[str, str]:
        """
        Инициализация полных названий блокчейнов

        Returns:
            Словарь с полными названиями
        """
        return {
            'ethereum': 'Ethereum Mainnet',
            'bsc': 'BNB Smart Chain',
            'polygon': 'Polygon PoS',
            'arbitrum': 'Arbitrum One',
            'optimism': 'Optimism Mainnet',
            'base': 'Base Network',
            'avalanche': 'Avalanche C-Chain',
            'solana': 'Solana Network',
            'fantom': 'Fantom Opera',
            'tron': 'Tron Network'
        }
    
    @staticmethod
    def _initialize_colors() -> Dict[str, str]:
        """
        Инициализация цветов блокчейнов
        
        Returns:
            Словарь с hex кодами цветов
        """
        return {
            'ethereum': '#627EEA',
            'bsc': '#F3BA2F',
            'polygon': '#8247E5',
            'arbitrum': '#28A0F0',
            'optimism': '#FF0420',
            'base': '#0052FF',
            'avalanche': '#E84142',
            'solana': '#14F195',
            'fantom': '#1969FF',
            'tron': '#FF0013'
        }
    
    @staticmethod
    def _initialize_emojis() -> Dict[str, str]:
        """
        Инициализация emoji для блокчейнов
        
        Returns:
            Словарь с emoji
        """
        return {
            'ethereum': '🔷',
            'bsc': '🟡',
            'polygon': '🟣',
            'arbitrum': '🔵',
            'optimism': '🔴',
            'base': '🔵',
            'avalanche': '🔺',
            'solana': '🌅',
            'fantom': '👻',
            'tron': '🔶'
        }
    
    def get_symbol(self, chain: str) -> str:
        """
        Получение нативного символа блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Символ валюты (ETH, BNB, SOL и т.д.)
        """
        chain_lower = chain.lower()
        return self._symbols.get(chain_lower, 'UNKNOWN')
    
    def get_name(self, chain: str) -> str:
        """
        Получение полного имени блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Полное название (Ethereum, BNB Chain и т.д.)
        """
        chain_lower = chain.lower()
        return self._names.get(chain_lower, chain.capitalize())
    
    def get_color(self, chain: str) -> str:
        """
        Получение цвета блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Hex код цвета
        """
        chain_lower = chain.lower()
        return self._colors.get(chain_lower, '#000000')
    
    def get_emoji(self, chain: str) -> str:
        """
        Получение emoji блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Emoji для визуального отображения
        """
        chain_lower = chain.lower()
        return self._emojis.get(chain_lower, '⛓️')
    
    def has_metadata(self, chain: str) -> bool:
        """
        Проверка наличия метаданных для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если метаданные определены
        """
        chain_lower = chain.lower()
        return chain_lower in self._symbols
    
    def get_all_chains(self) -> list:
        """
        Получение списка всех блокчейнов с метаданными
        
        Returns:
            Список названий блокчейнов
        """
        return list(self._symbols.keys())