# app/config/blockchain/chain_validators.py
"""
Chain Validators Module
Валидация блокчейнов и их параметров
"""

import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class ChainValidators:
    """
    Валидация блокчейнов
    
    Проверяет:
    - Включен ли блокчейн
    - Поддерживается ли блокчейн
    - Корректность названия блокчейна
    """
    
    def __init__(self, enabled_chains: List[str], supported_chains: List[str]):
        """
        Инициализация валидаторов
        
        Args:
            enabled_chains: Список включенных блокчейнов
            supported_chains: Список поддерживаемых блокчейнов
        """
        self._enabled_chains: Set[str] = set(chain.lower() for chain in enabled_chains)
        self._supported_chains: Set[str] = set(chain.lower() for chain in supported_chains)
        
        logger.debug(
            f"Chain validators initialized: "
            f"{len(self._enabled_chains)} enabled, "
            f"{len(self._supported_chains)} supported"
        )
    
    def is_chain_enabled(self, chain: str) -> bool:
        """
        Проверка включен ли блокчейн
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн включен
        """
        return chain.lower() in self._enabled_chains
    
    def is_chain_supported(self, chain: str) -> bool:
        """
        Проверка поддерживается ли блокчейн системой
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн поддерживается
        """
        return chain.lower() in self._supported_chains
    
    def is_chain_active(self, chain: str) -> bool:
        """
        Проверка активен ли блокчейн (включен и поддерживается)
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн активен
        """
        return self.is_chain_enabled(chain) and self.is_chain_supported(chain)
    
    def validate_chain(self, chain: str) -> bool:
        """
        Полная валидация блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            True если блокчейн прошел все проверки
        """
        if not chain:
            logger.warning("Empty chain name provided")
            return False
        
        if not isinstance(chain, str):
            logger.warning(f"Invalid chain type: {type(chain)}")
            return False
        
        if not self.is_chain_supported(chain):
            logger.warning(f"Unsupported chain: {chain}")
            return False
        
        if not self.is_chain_enabled(chain):
            logger.debug(f"Chain not enabled: {chain}")
            return False
        
        return True
    
    def get_enabled_chains(self) -> List[str]:
        """
        Получение списка включенных блокчейнов
        
        Returns:
            Список названий блокчейнов
        """
        return sorted(list(self._enabled_chains))
    
    def get_supported_chains(self) -> List[str]:
        """
        Получение списка поддерживаемых блокчейнов
        
        Returns:
            Список названий блокчейнов
        """
        return sorted(list(self._supported_chains))
    
    def get_active_chains(self) -> List[str]:
        """
        Получение списка активных блокчейнов (включенных и поддерживаемых)
        
        Returns:
            Список названий блокчейнов
        """
        active = self._enabled_chains.intersection(self._supported_chains)
        return sorted(list(active))
    
    def get_disabled_chains(self) -> List[str]:
        """
        Получение списка отключенных блокчейнов (поддерживаемых, но не включенных)
        
        Returns:
            Список названий блокчейнов
        """
        disabled = self._supported_chains.difference(self._enabled_chains)
        return sorted(list(disabled))