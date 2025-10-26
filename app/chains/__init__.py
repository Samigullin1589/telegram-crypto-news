# app/chains/__init__.py
"""
MULTI-CHAIN SUPPORT

Автоматическая инициализация и регистрация всех поддерживаемых блокчейнов.

Usage:
    from app.chains import initialize_all_chains, unified_api
    
    # Инициализация
    initialize_all_chains()
    
    # Использование
    event = await unified_api.parse_transaction("solana", "...")
    analysis = await unified_api.analyze_wallet_cross_chain("0x...")
"""

from typing import Dict, Optional
from app.chains.base import ChainRegistry
from app.chains.unified_api import unified_api


def initialize_all_chains(
    solana_rpc: Optional[list] = None,
    api_keys: Optional[Dict[str, str]] = None
):
    """
    Инициализирует и регистрирует все поддерживаемые блокчейны
    
    Args:
        solana_rpc: Список Solana RPC endpoints
        api_keys: API ключи для explorers {
            "base": "...",
            "arbitrum": "...",
            "optimism": "...",
            "avalanche": "...",
            "polygon": "..."
        }
    
    Returns:
        None (регистрирует chains в ChainRegistry)
    """
    
    api_keys = api_keys or {}
    
    print("\n" + "=" * 80)
    print("🌐 INITIALIZING MULTI-CHAIN SUPPORT")
    print("=" * 80)
    
    # ========================================================================
    # SOLANA
    # ========================================================================
    
    try:
        from app.chains.solana.parser import initialize_solana_chain
        
        solana = initialize_solana_chain(solana_rpc)
        ChainRegistry.register("solana", solana)
        
        print("✅ Solana: Raydium, Orca, Jupiter")
    
    except Exception as e:
        print(f"⚠️  Solana initialization failed: {e}")
    
    # ========================================================================
    # EVM CHAINS
    # ========================================================================
    
    try:
        from app.chains.evm.parser import (
            initialize_base_chain,
            initialize_arbitrum_chain,
            initialize_optimism_chain,
            initialize_avalanche_chain,
            initialize_polygon_chain
        )
        
        # Base
        base = initialize_base_chain(api_keys.get("base"))
        ChainRegistry.register("base", base)
        print("✅ Base: Uniswap V3, Aerodrome, BaseSwap")
        
        # Arbitrum
        arbitrum = initialize_arbitrum_chain(api_keys.get("arbitrum"))
        ChainRegistry.register("arbitrum", arbitrum)
        print("✅ Arbitrum: Uniswap V3, Camelot, Sushiswap, GMX")
        
        # Optimism
        optimism = initialize_optimism_chain(api_keys.get("optimism"))
        ChainRegistry.register("optimism", optimism)
        print("✅ Optimism: Uniswap V3, Velodrome, Sushiswap")
        
        # Avalanche
        avalanche = initialize_avalanche_chain(api_keys.get("avalanche"))
        ChainRegistry.register("avalanche", avalanche)
        print("✅ Avalanche: Trader Joe, Pangolin, Sushiswap")
        
        # Polygon
        polygon = initialize_polygon_chain(api_keys.get("polygon"))
        ChainRegistry.register("polygon", polygon)
        print("✅ Polygon: Uniswap V3, QuickSwap, Sushiswap, Balancer")
    
    except Exception as e:
        print(f"⚠️  EVM chains initialization failed: {e}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    registered = ChainRegistry.list_chains()
    
    print(f"\n📊 Total chains registered: {len(registered)}")
    print(f"   Chains: {', '.join(registered)}")
    print("=" * 80 + "\n")


def get_supported_chains() -> list:
    """
    Получает список всех поддерживаемых блокчейнов
    
    Returns:
        ["solana", "base", "arbitrum", ...]
    """
    return ChainRegistry.list_chains()


def get_chain_info(chain: str) -> Optional[Dict]:
    """
    Получает информацию о конкретном блокчейне
    
    Args:
        chain: Название блокчейна
    
    Returns:
        {
            "name": str,
            "type": str,
            "native_token": str,
            "dexes": List[str]
        }
    """
    return unified_api.get_chain_info(chain)


def get_all_chains_info() -> Dict:
    """
    Получает информацию обо всех зарегистрированных блокчейнах
    
    Returns:
        {
            "solana": {...},
            "base": {...},
            ...
        }
    """
    return unified_api.get_all_chains_info()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Initialization
    "initialize_all_chains",
    "get_supported_chains",
    "get_chain_info",
    "get_all_chains_info",
    
    # Main API
    "unified_api",
    
    # Registry
    "ChainRegistry"
]