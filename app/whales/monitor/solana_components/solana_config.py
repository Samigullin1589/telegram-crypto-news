# app/whales/monitor/solana_components/solana_config.py
"""
Solana Configuration
Конфигурация и константы для Solana блокчейна
"""

from typing import List


class SolanaConfig:
    """Конфигурация Solana"""
    
    # Программные ID
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    
    # RPC Endpoints
    PUBLIC_RPC_ENDPOINTS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com",
        "https://rpc.ankr.com/solana"
    ]
    
    # Helius RPC (требует API ключ)
    HELIUS_RPC_BASE = "https://mainnet.helius-rpc.com"
    
    # Параметры блокчейна
    NATIVE_TOKEN = "SOL"
    DECIMALS = 9
    BLOCK_TIME = 0.4  # секунды
    
    # Известные DEX программы
    DEX_PROGRAMS = {
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
        "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": "Serum",
        "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter",
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca"
    }
    
    @classmethod
    def get_rpc_endpoints(cls, api_key: str = None) -> List[str]:
        """
        Получение списка RPC endpoints
        
        Args:
            api_key: Helius API ключ (опционально)
            
        Returns:
            Список RPC URL
        """
        endpoints = []
        
        # Helius с API ключом (приоритет)
        if api_key:
            endpoints.append(f"{cls.HELIUS_RPC_BASE}/?api-key={api_key}")
        
        # Публичные endpoints как fallback
        endpoints.extend(cls.PUBLIC_RPC_ENDPOINTS)
        
        return endpoints
    
    @classmethod
    def is_dex_program(cls, program_id: str) -> bool:
        """
        Проверка является ли программа DEX
        
        Args:
            program_id: ID программы
            
        Returns:
            True если это известный DEX
        """
        return program_id in cls.DEX_PROGRAMS
    
    @classmethod
    def get_dex_name(cls, program_id: str) -> str:
        """
        Получение названия DEX по program ID
        
        Args:
            program_id: ID программы
            
        Returns:
            Название DEX или пустая строка
        """
        return cls.DEX_PROGRAMS.get(program_id, "")