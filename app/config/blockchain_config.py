# app/config/blockchain_config.py
"""
Blockchain Configuration Module
Конфигурация блокчейнов и whale мониторинга
"""

import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BlockchainConfig:
    """
    Конфигурация блокчейнов и параметров мониторинга
    Настройки порогов, эксплореров и нативных символов
    """
    
    def __init__(self):
        """Инициализация конфигурации блокчейнов"""
        
        self.enabled_chains = self._parse_enabled_chains()
        
        self.min_usd = float(os.getenv('MIN_USD', '100000'))
        
        self.whale_thresholds = {
            'ethereum': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'bsc': {
                'min_native_value': 100,
                'min_usd_value': 50000,
                'whale_threshold_usd': 500000,
                'mega_whale_threshold_usd': 5000000
            },
            'polygon': {
                'min_native_value': 50000,
                'min_usd_value': 25000,
                'whale_threshold_usd': 250000,
                'mega_whale_threshold_usd': 2500000
            },
            'arbitrum': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'optimism': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'base': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'avalanche': {
                'min_native_value': 500,
                'min_usd_value': 15000,
                'whale_threshold_usd': 150000,
                'mega_whale_threshold_usd': 1500000
            },
            'solana': {
                'min_native_value': 100,
                'min_usd_value': 10000,
                'whale_threshold_usd': 100000,
                'mega_whale_threshold_usd': 1000000
            },
            'fantom': {
                'min_native_value': 10000,
                'min_usd_value': 5000,
                'whale_threshold_usd': 50000,
                'mega_whale_threshold_usd': 500000
            }
        }
        
        self.blockchain_explorers = {
            'ethereum': 'https://etherscan.io',
            'bsc': 'https://bscscan.com',
            'polygon': 'https://polygonscan.com',
            'arbitrum': 'https://arbiscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'base': 'https://basescan.org',
            'avalanche': 'https://snowtrace.io',
            'solana': 'https://solscan.io',
            'fantom': 'https://ftmscan.com'
        }
        
        self.chain_native_symbols = {
            'ethereum': 'ETH',
            'bsc': 'BNB',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'optimism': 'ETH',
            'base': 'ETH',
            'avalanche': 'AVAX',
            'solana': 'SOL',
            'fantom': 'FTM'
        }
        
        self.chain_names = {
            'ethereum': 'Ethereum',
            'bsc': 'BNB Chain',
            'polygon': 'Polygon',
            'arbitrum': 'Arbitrum',
            'optimism': 'Optimism',
            'base': 'Base',
            'avalanche': 'Avalanche',
            'solana': 'Solana',
            'fantom': 'Fantom'
        }
        
        self.chain_colors = {
            'ethereum': '#627EEA',
            'bsc': '#F3BA2F',
            'polygon': '#8247E5',
            'arbitrum': '#28A0F0',
            'optimism': '#FF0420',
            'base': '#0052FF',
            'avalanche': '#E84142',
            'solana': '#14F195',
            'fantom': '#1969FF'
        }
        
        self.chain_emojis = {
            'ethereum': '🔷',
            'bsc': '🟡',
            'polygon': '🟣',
            'arbitrum': '🔵',
            'optimism': '🔴',
            'base': '🔵',
            'avalanche': '🔺',
            'solana': '🌅',
            'fantom': '👻'
        }
        
        logger.info(f"✅ [BLOCKCHAIN] Включено chains: {', '.join(self.enabled_chains)}")
    
    @staticmethod
    def _parse_enabled_chains() -> List[str]:
        """Парсинг включенных блокчейнов"""
        chains_str = os.getenv(
            'ENABLED_CHAINS',
            'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche'
        )
        return [chain.strip() for chain in chains_str.split(',') if chain.strip()]
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return chain in self.enabled_chains
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """
        Получение порогов для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Словарь с порогами
        """
        return self.whale_thresholds.get(chain, {
            'min_native_value': 10,
            'min_usd_value': 10000,
            'whale_threshold_usd': 100000,
            'mega_whale_threshold_usd': 1000000
        })
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        threshold = self.get_whale_threshold(chain)
        return usd_value >= threshold.get('whale_threshold_usd', 1000000)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        threshold = self.get_whale_threshold(chain)
        return usd_value >= threshold.get('mega_whale_threshold_usd', 10000000)
    
    def get_explorer_url(
        self,
        chain: str,
        address: str = None,
        tx_hash: str = None
    ) -> str:
        """
        Получение URL эксплорера
        
        Args:
            chain: Название блокчейна
            address: Адрес (опционально)
            tx_hash: Хэш транзакции (опционально)
            
        Returns:
            URL эксплорера
        """
        base_url = self.blockchain_explorers.get(chain, '')
        
        if not base_url:
            return ''
        
        if tx_hash:
            return f"{base_url}/tx/{tx_hash}"
        elif address:
            return f"{base_url}/address/{address}"
        else:
            return base_url
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение нативного символа блокчейна"""
        return self.chain_native_symbols.get(chain, 'UNKNOWN')
    
    def get_chain_name(self, chain: str) -> str:
        """Получение полного имени блокчейна"""
        return self.chain_names.get(chain, chain.capitalize())
    
    def get_chain_emoji(self, chain: str) -> str:
        """Получение emoji блокчейна"""
        return self.chain_emojis.get(chain, '⛓️')
    
    def get_chain_color(self, chain: str) -> str:
        """Получение цвета блокчейна"""
        return self.chain_colors.get(chain, '#000000')
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'enabled_chains': self.enabled_chains,
            'min_usd': self.min_usd,
            'total_supported': len(self.blockchain_explorers),
            'thresholds': {
                chain: thresh for chain, thresh in self.whale_thresholds.items()
                if chain in self.enabled_chains
            }
        }