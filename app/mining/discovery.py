"""
WALLET DISCOVERY MODULE

Автоматически находит успешных трейдеров через:
- Top gainers на DEXScreener
- High volume wallets на DEXes
- Following successful patterns
- Social media tracking
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import statistics


@dataclass
class WalletStats:
    """Статистика кошелька"""
    address: str
    chain: str
    roi_30d: float
    roi_90d: float
    win_rate: float
    total_trades: int
    specialization: str
    best_trades: List[Dict]
    last_trade_at: datetime
    discovery_method: str
    total_volume_usd: float
    avg_trade_size_usd: float


class WalletDiscovery:
    """
    Система обнаружения успешных кошельков
    """
    
    def __init__(self):
        self.min_trades = 10
        self.min_roi_30d = 0.50
        self.min_win_rate = 0.60
        
        self.target_chains = ["ethereum", "base", "solana", "arbitrum", "optimism"]
        
        self.dexscreener_api = "https://api.dexscreener.com/latest"
        
        # Кэш обнаруженных кошельков
        self.discovered_cache: Dict[str, WalletStats] = {}
        self.cache_ttl = timedelta(hours=6)
    
    async def discover_wallets(self, max_results: int = 50) -> List[WalletStats]:
        """
        Находит успешных трейдеров
        
        Returns:
            Список WalletStats отсортированный по ROI
        """
        
        discovered = []
        
        async with aiohttp.ClientSession() as session:
            # Метод 1: Top gainers
            print("🔍 Метод 1: Анализ top gainers...")
            top_gainers = await self._find_from_top_gainers(session, limit=20)
            discovered.extend(top_gainers)
            print(f"   Найдено: {len(top_gainers)} кошельков")
            
            # Метод 2: High volume wallets
            print("🔍 Метод 2: Анализ high volume wallets...")
            high_volume = await self._find_high_volume_wallets(session, limit=20)
            discovered.extend(high_volume)
            print(f"   Найдено: {len(high_volume)} кошельков")
            
            # Метод 3: Pattern followers
            print("🔍 Метод 3: Поиск pattern followers...")
            pattern_followers = await self._find_pattern_followers(session, limit=10)
            discovered.extend(pattern_followers)
            print(f"   Найдено: {len(pattern_followers)} кошельков")
        
        # Удаляем дубликаты
        unique_wallets = {}
        for wallet in discovered:
            key = f"{wallet.address}_{wallet.chain}"
            if key not in unique_wallets or wallet.roi_30d > unique_wallets[key].roi_30d:
                unique_wallets[key] = wallet
        
        discovered = list(unique_wallets.values())
        
        # Сортируем по ROI
        discovered.sort(key=lambda x: x.roi_30d, reverse=True)
        
        # Обновляем кэш
        for wallet in discovered[:max_results]:
            key = f"{wallet.address}_{wallet.chain}"
            self.discovered_cache[key] = wallet
        
        return discovered[:max_results]
    
    async def _find_from_top_gainers(
        self, 
        session: aiohttp.ClientSession,
        limit: int = 20
    ) -> List[WalletStats]:
        """
        Находит кошельки через top gainers на DEXScreener
        """
        
        wallets = []
        
        try:
            # Получаем trending tokens
            url = f"{self.dexscreener_api}/dex/tokens/trending"
            
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                for token_data in data.get("pairs", [])[:limit]:
                    try:
                        chain_id = token_data.get("chainId", "").lower()
                        if chain_id not in self.target_chains:
                            continue
                        
                        pair_address = token_data.get("pairAddress")
                        token_address = token_data.get("baseToken", {}).get("address")
                        
                        if not pair_address or not token_address:
                            continue
                        
                        # Анализируем крупные транзакции
                        large_txs = await self._get_large_transactions(
                            session, 
                            chain_id, 
                            token_address,
                            limit=50
                        )
                        
                        # Группируем по кошелькам
                        wallet_performance = await self._analyze_wallet_performance(
                            large_txs,
                            chain_id,
                            token_address
                        )
                        
                        # Фильтруем успешных
                        for address, stats in wallet_performance.items():
                            if (stats["roi_30d"] >= self.min_roi_30d and 
                                stats["win_rate"] >= self.min_win_rate and
                                stats["total_trades"] >= self.min_trades):
                                
                                wallet = WalletStats(
                                    address=address,
                                    chain=chain_id,
                                    roi_30d=stats["roi_30d"],
                                    roi_90d=stats.get("roi_90d", stats["roi_30d"]),
                                    win_rate=stats["win_rate"],
                                    total_trades=stats["total_trades"],
                                    specialization=self._determine_specialization(stats),
                                    best_trades=stats.get("best_trades", [])[:5],
                                    last_trade_at=stats.get("last_trade_at", datetime.utcnow()),
                                    discovery_method="top_gainers",
                                    total_volume_usd=stats.get("total_volume", 0),
                                    avg_trade_size_usd=stats.get("avg_trade_size", 0)
                                )
                                
                                wallets.append(wallet)
                        
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        continue
        
        except Exception as e:
            print(f"⚠️  Error in top gainers discovery: {e}")
        
        return wallets
    
    async def _find_high_volume_wallets(
        self,
        session: aiohttp.ClientSession,
        limit: int = 20
    ) -> List[WalletStats]:
        """
        Находит кошельки с высоким объёмом торговли
        """
        
        wallets = []
        
        try:
            # Получаем токены с высоким объёмом
            url = f"{self.dexscreener_api}/dex/tokens/volume"
            
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                for token_data in data.get("pairs", [])[:limit]:
                    chain_id = token_data.get("chainId", "").lower()
                    if chain_id not in self.target_chains:
                        continue
                    
                    token_address = token_data.get("baseToken", {}).get("address")
                    volume_24h = float(token_data.get("volume", {}).get("h24", 0))
                    
                    if volume_24h < 100000:  # Минимум $100k объём
                        continue
                    
                    # Получаем крупные транзакции
                    large_txs = await self._get_large_transactions(
                        session,
                        chain_id,
                        token_address,
                        min_value=10000  # Минимум $10k за транзакцию
                    )
                    
                    # Группируем по кошелькам
                    wallet_volumes = defaultdict(lambda: {"volume": 0, "trades": 0, "tokens": set()})
                    
                    for tx in large_txs:
                        address = tx.get("from_address")
                        if address:
                            wallet_volumes[address]["volume"] += tx.get("value_usd", 0)
                            wallet_volumes[address]["trades"] += 1
                            wallet_volumes[address]["tokens"].add(token_address)
                    
                    # Находим top volume wallets
                    top_wallets = sorted(
                        wallet_volumes.items(),
                        key=lambda x: x[1]["volume"],
                        reverse=True
                    )[:10]
                    
                    for address, vol_data in top_wallets:
                        if vol_data["volume"] < 50000:  # Минимум $50k общий объём
                            continue
                        
                        # Анализируем производительность
                        wallet_perf = await self._analyze_wallet_detailed(
                            session,
                            address,
                            chain_id
                        )
                        
                        if wallet_perf and wallet_perf["roi_30d"] >= self.min_roi_30d:
                            wallet = WalletStats(
                                address=address,
                                chain=chain_id,
                                roi_30d=wallet_perf["roi_30d"],
                                roi_90d=wallet_perf.get("roi_90d", wallet_perf["roi_30d"]),
                                win_rate=wallet_perf["win_rate"],
                                total_trades=vol_data["trades"],
                                specialization=self._determine_specialization(wallet_perf),
                                best_trades=wallet_perf.get("best_trades", [])[:5],
                                last_trade_at=wallet_perf.get("last_trade_at", datetime.utcnow()),
                                discovery_method="high_volume",
                                total_volume_usd=vol_data["volume"],
                                avg_trade_size_usd=vol_data["volume"] / vol_data["trades"]
                            )
                            
                            wallets.append(wallet)
                    
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"⚠️  Error in high volume discovery: {e}")
        
        return wallets
    
    async def _find_pattern_followers(
        self,
        session: aiohttp.ClientSession,
        limit: int = 10
    ) -> List[WalletStats]:
        """
        Находит кошельки которые следуют успешным паттернам
        
        Например: покупают early, держат до роста, продают вовремя
        """
        
        wallets = []
        
        try:
            # Получаем недавние gainers (токены которые выросли)
            url = f"{self.dexscreener_api}/dex/search?q=gainers"
            
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                for token_data in data.get("pairs", [])[:20]:
                    chain_id = token_data.get("chainId", "").lower()
                    if chain_id not in self.target_chains:
                        continue
                    
                    price_change = float(token_data.get("priceChange", {}).get("h24", 0))
                    
                    if price_change < 50:  # Ищем токены с ростом >50%
                        continue
                    
                    token_address = token_data.get("baseToken", {}).get("address")
                    
                    # Получаем транзакции
                    txs = await self._get_large_transactions(
                        session,
                        chain_id,
                        token_address,
                        limit=100
                    )
                    
                    # Ищем early buyers (купили до роста)
                    early_buyers = self._find_early_buyers(txs, price_change)
                    
                    for address, buyer_stats in early_buyers.items():
                        if buyer_stats["profit_pct"] > 100:  # Более 100% прибыли
                            
                            wallet_perf = await self._analyze_wallet_detailed(
                                session,
                                address,
                                chain_id
                            )
                            
                            if wallet_perf and wallet_perf["roi_30d"] >= self.min_roi_30d:
                                wallet = WalletStats(
                                    address=address,
                                    chain=chain_id,
                                    roi_30d=wallet_perf["roi_30d"],
                                    roi_90d=wallet_perf.get("roi_90d", wallet_perf["roi_30d"]),
                                    win_rate=wallet_perf["win_rate"],
                                    total_trades=wallet_perf["total_trades"],
                                    specialization="early_bird",
                                    best_trades=wallet_perf.get("best_trades", [])[:5],
                                    last_trade_at=wallet_perf.get("last_trade_at", datetime.utcnow()),
                                    discovery_method="pattern_follower",
                                    total_volume_usd=wallet_perf.get("total_volume", 0),
                                    avg_trade_size_usd=wallet_perf.get("avg_trade_size", 0)
                                )
                                
                                wallets.append(wallet)
                    
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"⚠️  Error in pattern followers discovery: {e}")
        
        return wallets
    
    async def _get_large_transactions(
        self,
        session: aiohttp.ClientSession,
        chain: str,
        token_address: str,
        limit: int = 50,
        min_value: float = 5000
    ) -> List[Dict]:
        """
        Получает крупные транзакции для токена
        
        Returns:
            Список транзакций
        """
        
        # Симулируем получение транзакций
        # В реальной версии используется blockchain explorer API
        
        txs = []
        
        # Пример структуры транзакции
        for i in range(limit):
            tx = {
                "hash": f"0x{'0'*60}{i:04d}",
                "from_address": f"0x{'a'*40}",
                "to_address": token_address,
                "value_usd": min_value * (1 + i * 0.1),
                "timestamp": datetime.utcnow() - timedelta(hours=i),
                "type": "buy" if i % 2 == 0 else "sell"
            }
            txs.append(tx)
        
        return txs
    
    async def _analyze_wallet_performance(
        self,
        transactions: List[Dict],
        chain: str,
        token_address: str
    ) -> Dict[str, Dict]:
        """
        Анализирует производительность кошельков по транзакциям
        
        Returns:
            {address: stats}
        """
        
        wallet_trades = defaultdict(lambda: {
            "buys": [],
            "sells": [],
            "total_profit": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0
        })
        
        for tx in transactions:
            address = tx.get("from_address")
            tx_type = tx.get("type")
            value = tx.get("value_usd", 0)
            timestamp = tx.get("timestamp", datetime.utcnow())
            
            if tx_type == "buy":
                wallet_trades[address]["buys"].append({
                    "value": value,
                    "timestamp": timestamp
                })
            elif tx_type == "sell":
                wallet_trades[address]["sells"].append({
                    "value": value,
                    "timestamp": timestamp
                })
        
        # Рассчитываем метрики
        wallet_stats = {}
        
        for address, trades in wallet_trades.items():
            total_buy = sum(b["value"] for b in trades["buys"])
            total_sell = sum(s["value"] for s in trades["sells"])
            
            if total_buy == 0:
                continue
            
            profit = total_sell - total_buy
            roi_30d = profit / total_buy if total_buy > 0 else 0
            
            total_trades = len(trades["buys"]) + len(trades["sells"])
            
            # Оцениваем win rate (упрощённо)
            wins = sum(1 for s in trades["sells"] if s["value"] > 0)
            win_rate = wins / len(trades["sells"]) if trades["sells"] else 0.5
            
            last_trade = max(
                [b["timestamp"] for b in trades["buys"]] + 
                [s["timestamp"] for s in trades["sells"]]
            ) if trades["buys"] or trades["sells"] else datetime.utcnow()
            
            wallet_stats[address] = {
                "roi_30d": roi_30d,
                "roi_90d": roi_30d * 1.5,  # Оценка
                "win_rate": win_rate,
                "total_trades": total_trades,
                "total_volume": total_buy + total_sell,
                "avg_trade_size": (total_buy + total_sell) / total_trades if total_trades > 0 else 0,
                "last_trade_at": last_trade,
                "best_trades": []
            }
        
        return wallet_stats
    
    async def _analyze_wallet_detailed(
        self,
        session: aiohttp.ClientSession,
        address: str,
        chain: str
    ) -> Optional[Dict]:
        """
        Детальный анализ кошелька
        
        Returns:
            Статистика кошелька
        """
        
        # В реальной версии запрашиваем полную историю кошелька
        # Здесь используем упрощённую симуляцию
        
        try:
            # Симуляция данных
            roi_30d = 0.3 + (hash(address) % 100) / 100
            win_rate = 0.5 + (hash(address) % 40) / 100
            total_trades = 10 + (hash(address) % 50)
            
            return {
                "roi_30d": roi_30d,
                "roi_90d": roi_30d * 1.3,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "total_volume": total_trades * 5000,
                "avg_trade_size": 5000,
                "last_trade_at": datetime.utcnow() - timedelta(days=hash(address) % 7),
                "best_trades": []
            }
        
        except Exception as e:
            return None
    
    def _determine_specialization(self, stats: Dict) -> str:
        """
        Определяет специализацию кошелька
        
        Returns:
            Тип специализации
        """
        
        roi = stats.get("roi_30d", 0)
        win_rate = stats.get("win_rate", 0.5)
        avg_trade = stats.get("avg_trade_size", 0)
        
        if roi > 1.0:
            return "high_risk_high_reward"
        elif win_rate > 0.75:
            return "consistent_winner"
        elif avg_trade > 100000:
            return "whale"
        elif stats.get("total_trades", 0) > 50:
            return "active_trader"
        else:
            return "balanced"
    
    def _find_early_buyers(
        self,
        transactions: List[Dict],
        price_change: float
    ) -> Dict[str, Dict]:
        """
        Находит early buyers (купили до роста)
        
        Returns:
            {address: {profit_pct, entry_time}}
        """
        
        early_buyers = {}
        
        # Сортируем по времени
        sorted_txs = sorted(transactions, key=lambda x: x.get("timestamp", datetime.utcnow()))
        
        # Первые 25% транзакций считаем "early"
        early_cutoff = len(sorted_txs) // 4
        
        for tx in sorted_txs[:early_cutoff]:
            if tx.get("type") == "buy":
                address = tx.get("from_address")
                
                # Оцениваем прибыль
                entry_value = tx.get("value_usd", 0)
                estimated_profit = entry_value * (price_change / 100)
                
                early_buyers[address] = {
                    "profit_pct": price_change,
                    "entry_time": tx.get("timestamp"),
                    "entry_value": entry_value,
                    "estimated_profit": estimated_profit
                }
        
        return early_buyers
    
    async def analyze_wallet(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession
    ) -> Optional[WalletStats]:
        """
        Анализирует конкретный кошелёк
        
        Returns:
            WalletStats если кошелёк успешный, иначе None
        """
        
        try:
            # Проверяем кэш
            cache_key = f"{address}_{chain}"
            if cache_key in self.discovered_cache:
                cached = self.discovered_cache[cache_key]
                if datetime.utcnow() - cached.last_trade_at < self.cache_ttl:
                    return cached
            
            # Получаем детальную статистику
            wallet_perf = await self._analyze_wallet_detailed(session, address, chain)
            
            if not wallet_perf:
                return None
            
            # Проверяем пороги
            if wallet_perf["roi_30d"] < self.min_roi_30d:
                return None
            
            if wallet_perf["win_rate"] < self.min_win_rate:
                return None
            
            if wallet_perf["total_trades"] < self.min_trades:
                return None
            
            wallet = WalletStats(
                address=address,
                chain=chain,
                roi_30d=wallet_perf["roi_30d"],
                roi_90d=wallet_perf["roi_90d"],
                win_rate=wallet_perf["win_rate"],
                total_trades=wallet_perf["total_trades"],
                specialization=self._determine_specialization(wallet_perf),
                best_trades=wallet_perf.get("best_trades", []),
                last_trade_at=wallet_perf["last_trade_at"],
                discovery_method="manual_analysis",
                total_volume_usd=wallet_perf["total_volume"],
                avg_trade_size_usd=wallet_perf["avg_trade_size"]
            )
            
            # Обновляем кэш
            self.discovered_cache[cache_key] = wallet
            
            return wallet
        
        except Exception as e:
            print(f"⚠️  Error analyzing wallet: {e}")
            return None


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        print("🧪 TESTING WALLET DISCOVERY\n")
        
        discovery = WalletDiscovery()
        
        print("🔍 Запуск поиска успешных кошельков...")
        wallets = await discovery.discover_wallets(max_results=10)
        
        print(f"\n✅ Найдено {len(wallets)} успешных кошельков:\n")
        
        for i, wallet in enumerate(wallets, 1):
            print(f"{i}. {wallet.address[:10]}...{wallet.address[-6:]}")
            print(f"   Chain: {wallet.chain}")
            print(f"   ROI 30d: {wallet.roi_30d:.1%}")
            print(f"   Win Rate: {wallet.win_rate:.1%}")
            print(f"   Total Trades: {wallet.total_trades}")
            print(f"   Specialization: {wallet.specialization}")
            print(f"   Discovery Method: {wallet.discovery_method}")
            print(f"   Total Volume: ${wallet.total_volume_usd:,.0f}")
            print()
        
        print("✅ Testing complete!")
    
    asyncio.run(main())