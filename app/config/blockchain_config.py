# app/config/blockchain_config.py
"""
Blockchain Configuration Module v3.0
Главный модуль конфигурации блокчейнов
"""

import os
import logging
from typing import Dict, List, Optional, Any

from .blockchain.chain_thresholds import ChainThresholds
from .blockchain.chain_metadata import ChainMetadata
from .blockchain.chain_explorers import ChainExplorers
from .blockchain.chain_validators import ChainValidators
from .blockchain.chain_formatters import ChainFormatters

logger = logging.getLogger(__name__)


class BlockchainConfig:
    """
    Главный класс конфигурации блокчейнов
    
    Управляет:
    - Списком активных блокчейнов
    - Порогами для whale транзакций
    - Метаданными блокчейнов
    - URL эксплореров
    - Валидацией и форматированием
    """
    
    def __init__(self):
        """Инициализация конфигурации блокчейнов"""
        logger.debug("Инициализация BlockchainConfig v3.0...")
        
        # Загрузка списка активных блокчейнов
        self.enabled_chains = self._parse_enabled_chains()
        
        # Глобальный минимальный порог в USD
        self.min_usd = float(os.getenv('MIN_USD', '100000'))
        
        # Инициализация компонентов
        self.thresholds = ChainThresholds()
        self.metadata = ChainMetadata()
        self.explorers = ChainExplorers()
        self.validators = ChainValidators(
            enabled_chains=self.enabled_chains,
            supported_chains=self.thresholds.get_all_chains()
        )
        self.formatters = ChainFormatters(self.metadata)
        
        logger.info(
            f"✅ [BLOCKCHAIN] Инициализировано chains: {len(self.enabled_chains)} "
            f"({', '.join(self.enabled_chains)})"
        )
    
    @staticmethod
    def _parse_enabled_chains() -> List[str]:
        """
        Парсинг списка включенных блокчейнов из переменных окружения
        
        Returns:
            Список названий блокчейнов в нижнем регистре
        """
        chains_str = os.getenv(
            'ENABLED_CHAINS',
            'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche'
        )
        
        chains = [chain.strip().lower() for chain in chains_str.split(',') if chain.strip()]
        
        logger.debug(f"Parsed enabled chains: {chains}")
        return chains
    
    # ========================================================================
    # ПРОВЕРКА БЛОКЧЕЙНОВ
    # ========================================================================
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return self.validators.is_chain_enabled(chain)
    
    def is_chain_supported(self, chain: str) -> bool:
        """Проверка поддерживается ли блокчейн системой"""
        return self.validators.is_chain_supported(chain)
    
    def get_all_supported_chains(self) -> List[str]:
        """Получение списка всех поддерживаемых блокчейнов"""
        return self.thresholds.get_all_chains()
    
    # ========================================================================
    # WHALE THRESHOLDS
    # ========================================================================
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """Получение порогов для блокчейна"""
        return self.thresholds.get_threshold(chain)
    
    def get_min_usd_value(self, chain: str) -> float:
        """Получение минимального порога в USD для блокчейна"""
        return self.thresholds.get_min_usd_value(chain)
    
    def get_min_native_value(self, chain: str) -> float:
        """Получение минимального количества нативной валюты"""
        return self.thresholds.get_min_native_value(chain)
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        return self.thresholds.is_whale_transaction(chain, usd_value)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        return self.thresholds.is_mega_whale_transaction(chain, usd_value)
    
    def get_transaction_category(self, chain: str, usd_value: float) -> str:
        """Определение категории транзакции по сумме"""
        return self.thresholds.get_transaction_category(chain, usd_value)
    
    def should_process_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка нужно ли обрабатывать транзакцию"""
        return self.thresholds.should_process_transaction(chain, usd_value)
    
    # ========================================================================
    # EXPLORERS
    # ========================================================================
    
    def get_explorer_url(
        self,
        chain: str,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> str:
        """Получение URL эксплорера"""
        return self.explorers.get_url(chain, address=address, tx_hash=tx_hash)
    
    # ========================================================================
    # МЕТАДАННЫЕ
    # ========================================================================
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение нативного символа блокчейна"""
        return self.metadata.get_symbol(chain)
    
    def get_chain_name(self, chain: str) -> str:
        """Получение полного имени блокчейна"""
        return self.metadata.get_name(chain)
    
    def get_chain_emoji(self, chain: str) -> str:
        """Получение emoji блокчейна"""
        return self.metadata.get_emoji(chain)
    
    def get_chain_color(self, chain: str) -> str:
        """Получение цвета блокчейна"""
        return self.metadata.get_color(chain)
    
    # ========================================================================
    # ФОРМАТИРОВАНИЕ
    # ========================================================================
    
    def format_amount(
        self,
        chain: str,
        amount: float,
        decimals: int = 2,
        include_symbol: bool = True
    ) -> str:
        """Форматирование суммы с символом валюты"""
        return self.formatters.format_amount(chain, amount, decimals, include_symbol)
    
    # ========================================================================
    # КОМПЛЕКСНЫЕ МЕТОДЫ
    # ========================================================================
    
    def get_chain_info(self, chain: str) -> Dict[str, Any]:
        """
        Получение полной информации о блокчейне
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Словарь с полной информацией о блокчейне
        """
        chain_lower = chain.lower()
        
        return {
            'chain': chain_lower,
            'name': self.get_chain_name(chain_lower),
            'symbol': self.get_chain_symbol(chain_lower),
            'emoji': self.get_chain_emoji(chain_lower),
            'color': self.get_chain_color(chain_lower),
            'explorer': self.explorers.get_base_url(chain_lower),
            'enabled': self.is_chain_enabled(chain_lower),
            'thresholds': self.get_whale_threshold(chain_lower)
        }
    
    def get_enabled_chains_info(self) -> List[Dict[str, Any]]:
        """Получение информации о всех включенных блокчейнах"""
        return [self.get_chain_info(chain) for chain in self.enabled_chains]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Словарь со всеми настройками
        """
        return {
            'enabled_chains': self.enabled_chains,
            'min_usd': self.min_usd,
            'total_supported': len(self.thresholds.get_all_chains()),
            'thresholds': {
                chain: self.get_whale_threshold(chain)
                for chain in self.enabled_chains
            },
            'explorers': {
                chain: self.explorers.get_base_url(chain)
                for chain in self.enabled_chains
            },
            'metadata': {
                chain: {
                    'name': self.get_chain_name(chain),
                    'symbol': self.get_chain_symbol(chain),
                    'emoji': self.get_chain_emoji(chain),
                    'color': self.get_chain_color(chain)
                }
                for chain in self.enabled_chains
            }
        }
    
    def __repr__(self) -> str:
        """Строковое представление конфигурации"""
        return (
            f"BlockchainConfig("
            f"enabled={len(self.enabled_chains)}, "
            f"supported={len(self.thresholds.get_all_chains())}, "
            f"chains={', '.join(self.enabled_chains)}"
            f")"
        )