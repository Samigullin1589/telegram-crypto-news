# app/whales/monitor/evm_components/evm_config.py
"""
EVM Chain Configuration
Конфигурация для различных EVM блокчейнов
"""

from typing import Dict, List


class EVMChainConfig:
    """Конфигурация EVM блокчейнов"""
    
    CHAIN_CONFIGS = {
        "ethereum": {
            "native": "ETH",
            "decimals": 18,
            "block_time": 12,
            "chain_id": 1,
            "explorer": "https://etherscan.io"
        },
        "bsc": {
            "native": "BNB",
            "decimals": 18,
            "block_time": 3,
            "chain_id": 56,
            "explorer": "https://bscscan.com"
        },
        "base": {
            "native": "ETH",
            "decimals": 18,
            "block_time": 2,
            "chain_id": 8453,
            "explorer": "https://basescan.org"
        },
        "arbitrum": {
            "native": "ETH",
            "decimals": 18,
            "block_time": 0.25,
            "chain_id": 42161,
            "explorer": "https://arbiscan.io"
        },
        "polygon": {
            "native": "MATIC",
            "decimals": 18,
            "block_time": 2,
            "chain_id": 137,
            "explorer": "https://polygonscan.com"
        }
    }
    
    RPC_ENDPOINTS = {
        "ethereum": [
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://ethereum.publicnode.com",
            "https://eth.drpc.org"
        ],
        "bsc": [
            "https://bsc-dataseed.binance.org",
            "https://rpc.ankr.com/bsc",
            "https://bsc-dataseed1.defibit.io",
            "https://bsc.publicnode.com"
        ],
        "base": [
            "https://mainnet.base.org",
            "https://base.blockpi.network/v1/rpc/public",
            "https://base.meowrpc.com",
            "https://base.drpc.org"
        ],
        "arbitrum": [
            "https://arb1.arbitrum.io/rpc",
            "https://rpc.ankr.com/arbitrum",
            "https://arbitrum.publicnode.com",
            "https://arbitrum.drpc.org"
        ],
        "polygon": [
            "https://polygon-rpc.com",
            "https://rpc.ankr.com/polygon",
            "https://polygon.publicnode.com",
            "https://polygon.drpc.org"
        ]
    }
    
    @classmethod
    def get_config(cls, chain: str) -> Dict:
        """
        Получение конфигурации для chain
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Dict с конфигурацией
        """
        return cls.CHAIN_CONFIGS.get(chain, {})
    
    @classmethod
    def get_rpc_endpoints(cls, chain: str) -> List[str]:
        """
        Получение RPC endpoints для chain
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Список RPC URL
        """
        return cls.RPC_ENDPOINTS.get(chain, [])
    
    @classmethod
    def get_native_token(cls, chain: str) -> str:
        """
        Получение нативного токена
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Символ нативного токена
        """
        config = cls.get_config(chain)
        return config.get("native", "UNKNOWN")
    
    @classmethod
    def get_block_time(cls, chain: str) -> float:
        """
        Получение среднего времени блока
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Время блока в секундах
        """
        config = cls.get_config(chain)
        return config.get("block_time", 12)
    
    @classmethod
    def get_decimals(cls, chain: str) -> int:
        """
        Получение decimals нативного токена
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Количество decimals
        """
        config = cls.get_config(chain)
        return config.get("decimals", 18)