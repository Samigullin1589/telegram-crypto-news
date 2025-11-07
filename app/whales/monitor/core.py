# app/whales/monitor/core.py
"""
Blockchain Monitor Core v6.0
Multi-chain monitoring with dynamic asset management
"""

import asyncio
import aiohttp
import warnings
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from app.config import config
from app.whales.normalize import WhaleEvent
from app.whales.monitor.circuit_breaker import CircuitBreaker
from app.whales.monitor.cache import TransactionCache
from app.whales.monitor.filters import EventFilter
from app.whales.monitor.dex_detector import DEXDetector
from app.whales.monitor.asset_manager import AssetManager
from app.whales.monitor.evm_provider import EVMProvider
from app.whales.monitor.solana_provider import SolanaProvider
from app.whales.monitor.tron_provider import TronProvider

warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')


class BlockchainMonitor:
    """Универсальный монитор всех блокчейнов"""
    
    SUPPORTED_CHAINS = [
        'ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism',
        'base', 'avalanche', 'fantom', 'cronos', 'moonbeam',
        'solana', 'tron'
    ]
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = None
        
        self.circuit_breakers = {
            chain: CircuitBreaker(failure_threshold=3, timeout=120)
            for chain in self.SUPPORTED_CHAINS
        }
        
        self.tx_cache = TransactionCache(ttl_seconds=3600)
        self.event_filter = EventFilter()
        self.dex_detector = DEXDetector()
        
        cache_dir = config.data_dir / 'cache'
        self.asset_manager = AssetManager(cache_dir)
        
        self.evm_provider: Optional[EVMProvider] = None
        self.solana_provider: Optional[SolanaProvider] = None
        self.tron_provider: Optional[TronProvider] = None
        
        self.stats = {
            "requests_made": defaultdict(int),
            "events_found": defaultdict(int),
            "cache_hits": 0,
            "errors": defaultdict(int),
            "circuit_breaker_trips": defaultdict(int),
            "chains": {},
            "tracked_assets": 0
        }
    
    async def __aenter__(self):
        """Создает aiohttp сессию и инициализирует asset manager"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "CryptoCompass/6.0",
                "Accept": "application/json"
            }
        )
        
        await self.asset_manager.initialize()
        self.stats["tracked_assets"] = len(self.asset_manager.get_top_assets())
        
        self.evm_provider = EVMProvider(
            self.session, self.rate_limiter, self.tx_cache, self.dex_detector
        )
        self.solana_provider = SolanaProvider(
            self.session, self.rate_limiter, self.tx_cache, self.dex_detector
        )
        self.tron_provider = TronProvider(
            self.session, self.rate_limiter, self.tx_cache
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает aiohttp сессию"""
        if self.session:
            await self.session.close()
    
    async def fetch_events(
        self,
        start_time: datetime,
        chains: Optional[List[str]] = None,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """Получает события со всех блокчейнов"""
        
        if not self.session:
            raise RuntimeError("BlockchainMonitor должен использоваться с async context manager")
        
        chains_to_monitor = chains or self.SUPPORTED_CHAINS
        
        chains_to_monitor = [
            chain for chain in chains_to_monitor
            if chain in self.SUPPORTED_CHAINS
        ]
        
        if not chains_to_monitor:
            print("⚠️ [MONITOR] Нет доступных chains")
            return []
        
        if not assets:
            assets = self.asset_manager.get_top_assets(limit=100)
        
        print(f"🔍 [MONITOR] Сканирую {len(chains_to_monitor)} chains: {', '.join(chains_to_monitor)}")
        print(f"💎 [MONITOR] Отслеживаю {len(assets)} активов")
        
        min_threshold = getattr(config.whale, 'min_usd_threshold', 50000)
        print(f"💰 [MONITOR] Минимальный порог: ${min_threshold:,.0f}")
        
        tasks = [
            self._fetch_chain_events(chain, start_time, assets)
            for chain in chains_to_monitor
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_events = []
        for chain, result in zip(chains_to_monitor, results):
            if isinstance(result, Exception):
                print(f"❌ [MONITOR] Ошибка {chain}: {result}")
                self.stats["errors"][chain] += 1
                continue
            
            if result:
                filtered_events = [
                    event for event in result
                    if not self.event_filter.should_filter(event, chain)
                ]
                
                all_events.extend(filtered_events)
                self.stats["events_found"][chain] += len(filtered_events)
                print(f"✅ [MONITOR] {chain}: найдено {len(filtered_events)} событий")
        
        unique_events = {}
        for event in all_events:
            if event.tx_hash not in unique_events:
                unique_events[event.tx_hash] = event
        
        all_events = list(unique_events.values())
        all_events.sort(key=lambda e: e.tx_time_utc, reverse=True)
        
        print(f"🎯 [MONITOR] Всего уникальных событий: {len(all_events)}")
        
        return all_events
    
    async def _fetch_chain_events(
        self,
        chain: str,
        start_time: datetime,
        assets: Optional[List[str]] = None
    ) -> List[WhaleEvent]:
        """Получает события для конкретного chain"""
        
        if not self.circuit_breakers[chain].can_execute():
            print(f"⚠️ [MONITOR] {chain} circuit breaker OPEN, пропускаю")
            self.stats["circuit_breaker_trips"][chain] += 1
            return []
        
        try:
            evm_chains = [
                'ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism',
                'base', 'avalanche', 'fantom', 'cronos', 'moonbeam'
            ]
            
            if chain in evm_chains:
                events = await self.evm_provider.fetch_events(chain, start_time, assets)
            elif chain == 'solana':
                events = await self.solana_provider.fetch_events(start_time, assets)
            elif chain == 'tron':
                events = await self.tron_provider.fetch_events(start_time, assets)
            else:
                print(f"⚠️ [MONITOR] Неизвестный chain: {chain}")
                return []
            
            self.circuit_breakers[chain].record_success()
            self.stats["requests_made"][chain] += 1
            
            return events
        
        except Exception as e:
            print(f"❌ [MONITOR] Ошибка {chain}: {e}")
            self.circuit_breakers[chain].record_failure()
            self.stats["errors"][chain] += 1
            return []
    
    async def update_assets(self):
        """Обновляет список отслеживаемых активов"""
        await self.asset_manager.update_assets()
        self.stats["tracked_assets"] = len(self.asset_manager.get_top_assets())
    
    def get_stats(self) -> Dict:
        """Возвращает статистику мониторинга"""
        filter_stats = self.event_filter.get_stats()
        
        return {
            "requests_made": dict(self.stats["requests_made"]),
            "events_found": dict(self.stats["events_found"]),
            "cache_hits": self.stats["cache_hits"],
            "errors": dict(self.stats["errors"]),
            "circuit_breaker_trips": dict(self.stats["circuit_breaker_trips"]),
            "tracked_assets": self.stats["tracked_assets"],
            "supported_chains": len(self.SUPPORTED_CHAINS),
            "circuit_breaker_states": {
                chain: breaker.state
                for chain, breaker in self.circuit_breakers.items()
            },
            **filter_stats
        }
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("📊 BLOCKCHAIN MONITOR STATISTICS v6.0")
        print("=" * 80)
        
        print(f"\n💎 Tracked Assets: {stats['tracked_assets']}")
        print(f"🔗 Supported Chains: {stats['supported_chains']}")
        
        print(f"\n📡 Requests Made:")
        for chain, count in stats["requests_made"].items():
            print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n🐋 Events Found:")
        for chain, count in stats["events_found"].items():
            print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n🚫 Events Filtered:")
        for chain, count in stats.get("events_filtered", {}).items():
            if count > 0:
                print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n💾 Cache Hits: {stats['cache_hits']}")
        
        print(f"\n❌ Errors:")
        for chain, count in stats["errors"].items():
            if count > 0:
                print(f"   {chain:12s}: {count:4d}")
        
        print(f"\n⚡ Circuit Breaker States:")
        for chain, state in stats["circuit_breaker_states"].items():
            emoji = "✅" if state == "CLOSED" else "⚠️" if state == "HALF_OPEN" else "🔴"
            print(f"   {chain:12s}: {emoji} {state}")
        
        print("\n" + "=" * 80 + "\n")