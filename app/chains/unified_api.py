# app/chains/unified_api.py
"""
UNIFIED MULTI-CHAIN API

Единый интерфейс для работы со всеми блокчейнами.
Автоматически выбирает нужный parser и нормализует данные.
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

from app.chains.base import ChainBase, TransactionEvent, ChainRegistry


class UnifiedChainAPI:
    """
    Единый API для всех блокчейнов
    
    Usage:
        api = UnifiedChainAPI()
        
        # Парсинг транзакций
        event = await api.parse_transaction("ethereum", "0x123...")
        
        # Мониторинг кошелька на всех chains
        events = await api.monitor_wallet_all_chains("0xABC...")
        
        # Cross-chain анализ
        analysis = await api.analyze_wallet_cross_chain("0xABC...")
    """
    
    def __init__(self):
        self.registry = ChainRegistry
    
    # ========================================================================
    # SINGLE CHAIN OPERATIONS
    # ========================================================================
    
    async def parse_transaction(self, chain: str, tx_hash: str) -> Optional[TransactionEvent]:
        """
        Парсит транзакцию на любом блокчейне
        
        Args:
            chain: Название блокчейна (ethereum, solana, base, etc)
            tx_hash: Hash транзакции
        
        Returns:
            TransactionEvent или None
        """
        
        chain_instance = self.registry.get(chain)
        
        if not chain_instance:
            print(f"⚠️  Chain '{chain}' not supported")
            return None
        
        try:
            event = await chain_instance.parse_transaction(tx_hash)
            return event
        
        except Exception as e:
            print(f"❌ Error parsing transaction on {chain}: {e}")
            return None
    
    async def get_token_price(self, chain: str, token_address: str) -> Optional[float]:
        """
        Получает цену токена на любом блокчейне
        
        Args:
            chain: Название блокчейна
            token_address: Адрес токена
        
        Returns:
            Цена в USD или None
        """
        
        chain_instance = self.registry.get(chain)
        
        if not chain_instance:
            return None
        
        try:
            price = await chain_instance.get_token_price(token_address)
            return price
        
        except Exception as e:
            print(f"❌ Error getting token price on {chain}: {e}")
            return None
    
    async def get_wallet_balance(
        self, 
        chain: str, 
        wallet_address: str, 
        token_address: Optional[str] = None
    ) -> float:
        """
        Получает баланс кошелька на любом блокчейне
        
        Args:
            chain: Название блокчейна
            wallet_address: Адрес кошелька
            token_address: Адрес токена (None = нативный)
        
        Returns:
            Баланс
        """
        
        chain_instance = self.registry.get(chain)
        
        if not chain_instance:
            return 0.0
        
        try:
            balance = await chain_instance.get_wallet_balance(wallet_address, token_address)
            return balance
        
        except Exception as e:
            print(f"❌ Error getting wallet balance on {chain}: {e}")
            return 0.0
    
    # ========================================================================
    # MULTI-CHAIN OPERATIONS
    # ========================================================================
    
    async def parse_transactions_multi_chain(
        self, 
        transactions: List[Dict[str, str]]
    ) -> List[TransactionEvent]:
        """
        Парсит транзакции на разных chains параллельно
        
        Args:
            transactions: [{"chain": "ethereum", "tx_hash": "0x..."}, ...]
        
        Returns:
            Список событий
        """
        
        tasks = [
            self.parse_transaction(tx["chain"], tx["tx_hash"])
            for tx in transactions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем успешные
        events = []
        for result in results:
            if isinstance(result, TransactionEvent):
                events.append(result)
        
        return events
    
    async def monitor_wallet_all_chains(
        self, 
        wallet_address: str, 
        lookback_blocks: int = 100
    ) -> Dict[str, List[TransactionEvent]]:
        """
        Мониторит кошелёк на ВСЕХ поддерживаемых chains
        
        Args:
            wallet_address: Адрес кошелька (нормализуется для каждого chain)
            lookback_blocks: Сколько блоков назад смотреть
        
        Returns:
            {
                "ethereum": [TransactionEvent, ...],
                "solana": [...],
                ...
            }
        """
        
        all_chains = self.registry.get_all()
        
        results = {}
        
        for chain_name, chain_instance in all_chains.items():
            try:
                # TODO: Реализовать мониторинг последних блоков
                # Пока заглушка
                results[chain_name] = []
            
            except Exception as e:
                print(f"⚠️  Error monitoring {chain_name}: {e}")
                results[chain_name] = []
        
        return results
    
    async def get_wallet_balances_all_chains(
        self, 
        wallet_address: str
    ) -> Dict[str, float]:
        """
        Получает балансы кошелька на всех chains
        
        Returns:
            {
                "ethereum": 1.5,  # ETH
                "solana": 10.2,   # SOL
                ...
            }
        """
        
        all_chains = self.registry.get_all()
        
        tasks = []
        chain_names = []
        
        for chain_name, chain_instance in all_chains.items():
            tasks.append(chain_instance.get_wallet_balance(wallet_address))
            chain_names.append(chain_name)
        
        balances = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for chain_name, balance in zip(chain_names, balances):
            if isinstance(balance, (int, float)):
                result[chain_name] = balance
            else:
                result[chain_name] = 0.0
        
        return result
    
    # ========================================================================
    # CROSS-CHAIN ANALYSIS
    # ========================================================================
    
    async def analyze_wallet_cross_chain(
        self, 
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Анализирует активность кошелька на всех chains
        
        Находит:
        - На каких chains активен
        - Общий объём торговли
        - Любимые DEXes
        - Паттерны (покупает один токен на разных chains)
        
        Returns:
            {
                "total_volume_usd": float,
                "active_chains": List[str],
                "favorite_dexes": Dict[str, int],
                "cross_chain_tokens": List[str],
                "risk_score": int
            }
        """
        
        print(f"🔍 [CROSS-CHAIN] Analyzing wallet: {wallet_address[:10]}...")
        
        # Получаем события на всех chains
        all_events = await self.monitor_wallet_all_chains(wallet_address)
        
        # Фильтруем пустые
        active_chains = [chain for chain, events in all_events.items() if events]
        
        # Считаем объём
        total_volume = 0
        dex_usage = {}
        tokens_by_chain = {}
        
        for chain, events in all_events.items():
            for event in events:
                # Объём
                total_volume += event.amount_out_usd
                
                # DEX usage
                dex_usage[event.dex_name] = dex_usage.get(event.dex_name, 0) + 1
                
                # Токены
                if chain not in tokens_by_chain:
                    tokens_by_chain[chain] = set()
                tokens_by_chain[chain].add(event.token_out)
        
        # Находим токены которые покупал на разных chains
        cross_chain_tokens = []
        if len(tokens_by_chain) > 1:
            # Упрощённая логика - можно улучшить
            all_tokens = set()
            for tokens in tokens_by_chain.values():
                all_tokens.update(tokens)
            
            for token in all_tokens:
                chains_with_token = sum(1 for tokens in tokens_by_chain.values() if token in tokens)
                if chains_with_token > 1:
                    cross_chain_tokens.append(token)
        
        # Risk score (чем больше chains использует - тем опытнее)
        risk_score = min(100, len(active_chains) * 20 + len(dex_usage) * 5)
        
        return {
            "wallet": wallet_address,
            "total_volume_usd": total_volume,
            "active_chains": active_chains,
            "active_chains_count": len(active_chains),
            "favorite_dexes": dex_usage,
            "cross_chain_tokens": cross_chain_tokens,
            "risk_score": risk_score,
            "is_sophisticated": len(active_chains) >= 3,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def detect_cross_chain_pattern(
        self, 
        events_by_chain: Dict[str, List[TransactionEvent]]
    ) -> Dict[str, Any]:
        """
        Обнаруживает cross-chain паттерны
        
        Например:
        - Кит покупает одинаковый токен на Ethereum и Base
        - Арбитраж между chains
        - Миграция ликвидности
        
        Returns:
            {
                "pattern_type": str,
                "confidence": int,
                "details": Dict
            }
        """
        
        # TODO: Реализовать продвинутую логику
        
        # Простая проверка: одинаковые токены на разных chains
        tokens_by_chain = {}
        for chain, events in events_by_chain.items():
            tokens_by_chain[chain] = set(e.token_out for e in events)
        
        # Проверяем пересечения
        if len(tokens_by_chain) > 1:
            chains = list(tokens_by_chain.keys())
            common_tokens = tokens_by_chain[chains[0]]
            
            for chain in chains[1:]:
                common_tokens &= tokens_by_chain[chain]
            
            if common_tokens:
                return {
                    "pattern_type": "same_token_multi_chain",
                    "confidence": 85,
                    "details": {
                        "tokens": list(common_tokens),
                        "chains": chains
                    }
                }
        
        return {
            "pattern_type": "none",
            "confidence": 0,
            "details": {}
        }
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def list_supported_chains(self) -> List[str]:
        """Список всех поддерживаемых chains"""
        return self.registry.list_chains()
    
    def get_chain_info(self, chain: str) -> Optional[Dict]:
        """Получает информацию о chain"""
        chain_instance = self.registry.get(chain)
        
        if not chain_instance:
            return None
        
        return {
            "name": chain_instance.name,
            "type": chain_instance.chain_type.value,
            "native_token": chain_instance.native_token,
            "supported_dexes": list(chain_instance.known_dexes.values())
        }
    
    def get_all_chains_info(self) -> Dict[str, Dict]:
        """Информация о всех chains"""
        result = {}
        
        for chain_name in self.registry.list_chains():
            info = self.get_chain_info(chain_name)
            if info:
                result[chain_name] = info
        
        return result


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Создаём глобальный instance для удобства
unified_api = UnifiedChainAPI()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def parse_tx(chain: str, tx_hash: str) -> Optional[TransactionEvent]:
    """
    Convenience function для парсинга транзакции
    
    Usage:
        from app.chains.unified_api import parse_tx
        
        event = await parse_tx("ethereum", "0x123...")
    """
    return await unified_api.parse_transaction(chain, tx_hash)


async def analyze_wallet(wallet_address: str) -> Dict:
    """
    Convenience function для cross-chain анализа
    
    Usage:
        from app.chains.unified_api import analyze_wallet
        
        analysis = await analyze_wallet("0xABC...")
        print(f"Active on {analysis['active_chains_count']} chains")
    """
    return await unified_api.analyze_wallet_cross_chain(wallet_address)


def list_chains() -> List[str]:
    """
    Convenience function для списка chains
    
    Usage:
        from app.chains.unified_api import list_chains
        
        chains = list_chains()
        print(f"Supported: {chains}")
    """
    return unified_api.list_supported_chains()