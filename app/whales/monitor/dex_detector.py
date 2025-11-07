# app/whales/monitor/dex_detector.py
"""
DEX Detection System
"""

from typing import Dict, Optional, List


class DEXDetector:
    """Определение DEX протоколов"""
    
    def __init__(self):
        self.dex_contracts = self._load_dex_contracts()
    
    def _load_dex_contracts(self) -> Dict[str, Dict[str, str]]:
        """Загружает адреса DEX контрактов"""
        return {
            "ethereum": {
                "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
                "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
                "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "Sushiswap",
                "0xba12222222228d8ba445958a75a0704d566bf2c8": "Balancer",
                "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x"
            },
            "bsc": {
                "0x10ed43c718714eb63d5aa57b78b54704e256024e": "PancakeSwap V2",
                "0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "PancakeSwap V3",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            },
            "base": {
                "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V3",
                "0x327df1e6de05895d2ab08513aadd9313fe505d86": "Aerodrome",
                "0x8909dc15e40173ff4699343b6eb8132c65e18ec6": "BaseSwap"
            },
            "arbitrum": {
                "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
                "0xc873fecbd354f5a56e00e710b90ef4201db2448d": "Camelot",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            },
            "polygon": {
                "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
                "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff": "QuickSwap",
                "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "Sushiswap"
            }
        }
    
    def detect_evm_dex(self, chain: str, address: str) -> Optional[str]:
        """Определяет DEX по адресу контракта"""
        address = address.lower()
        chain_dexes = self.dex_contracts.get(chain, {})
        return chain_dexes.get(address)
    
    def detect_solana_dex(self, account_keys: List) -> Optional[str]:
        """Определяет Solana DEX по account keys"""
        solana_dexes = {
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
            "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
            "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter",
            "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": "Orca V2"
        }
        
        for account in account_keys:
            account_str = account if isinstance(account, str) else account.get("pubkey", "")
            if account_str in solana_dexes:
                return solana_dexes[account_str]
        
        return None