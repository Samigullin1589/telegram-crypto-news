# app/whales/discovery/engine.py
"""
Главный движок Discovery Engine
"""

import aiohttp
import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime
from collections import defaultdict

from app import settings
from app.whales.discovery.models import TokenData, DiscoveryStats
from app.whales.discovery.filters import TokenQualityFilter
from app.whales.discovery.providers import CoinGeckoProvider
from app.whales.discovery.storage import WatchlistStorage


class DiscoveryEngine:
    """Движок автоматического обнаружения токенов для мониторинга"""
    
    SUPPORTED_CHAINS = ['ethereum', 'bsc', 'solana', 'base', 'arbitrum', 'polygon']
    
    def __init__(self):
        self.storage_path = self._get_storage_path()
        self.storage = WatchlistStorage(self.storage_path)
        
        self.watchlist: Dict[str, Set[str]] = defaultdict(set)
        self.token_metadata: Dict[str, TokenData] = {}
        self.stats = DiscoveryStats()
        
        self.chains = self.SUPPORTED_CHAINS.copy()
        
        self.quality_filter = TokenQualityFilter(
            min_age_days=getattr(settings, 'MIN_TOKEN_AGE_DAYS', 30),
            min_volume_usd=100_000,
            min_market_cap_usd=1_000_000,
            max_price_change_percent=200
        )
        
        self.provider = CoinGeckoProvider(
            api_key=getattr(settings, 'COINGECKO_API_KEY', None)
        )
        
        self.tokens_per_chain = getattr(settings, 'DISCOVERY_TOP_N_PER_CHAIN', 50)
        self.blacklist = set(getattr(settings, 'DISCOVERY_BLACKLIST', []))
        
        self._load_watchlist()
    
    def _get_storage_path(self) -> str:
        """Определяет путь к файлу хранения watchlist"""
        if hasattr(settings, 'WATCHLIST_FILE'):
            return settings.WATCHLIST_FILE
        
        data_dir = getattr(settings, 'DATA_DIR', 'data')
        
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
            except OSError:
                data_dir = os.path.join(os.getcwd(), 'data')
                os.makedirs(data_dir, exist_ok=True)
        
        return os.path.join(data_dir, 'watchlist.json')
    
    async def refresh_watchlist(self) -> Dict[str, int]:
        """
        Обновляет watchlist новыми топовыми токенами
        
        Returns:
            Словарь с количеством новых токенов по каждому chain
        """
        print(f'\n{"=" * 80}')
        print(f'🔍 [DISCOVERY] Обновление watchlist')
        print(f'{"=" * 80}')
        
        start_time = datetime.utcnow()
        new_tokens_count = defaultdict(int)
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._discover_chain_tokens(chain, session)
                for chain in self.chains
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for chain, result in zip(self.chains, results):
                if isinstance(result, Exception):
                    print(f'❌ [DISCOVERY] Ошибка для {chain}: {result}')
                    continue
                
                if not result:
                    continue
                
                for token_data in result:
                    new_count = self._process_discovered_token(chain, token_data)
                    new_tokens_count[chain] += new_count
        
        self._save_watchlist()
        
        elapsed = (datetime.utcnow() - start_time).seconds
        self._update_stats()
        
        self._print_refresh_summary(new_tokens_count, elapsed)
        
        return dict(new_tokens_count)
    
    async def _discover_chain_tokens(
        self,
        chain: str,
        session: aiohttp.ClientSession
    ) -> List[Dict]:
        """Получает топ токены для конкретного chain"""
        print(f'🔍 [DISCOVERY] Запрос топ-{self.tokens_per_chain} для {chain}')
        
        return await self.provider.get_top_tokens(
            chain=chain,
            limit=self.tokens_per_chain,
            session=session
        )
    
    def _process_discovered_token(self, chain: str, token_data: Dict) -> int:
        """
        Обрабатывает обнаруженный токен
        
        Returns:
            1 если токен добавлен, 0 если пропущен
        """
        symbol = token_data.get('symbol', '').upper()
        
        if not self._validate_token_symbol(symbol):
            return 0
        
        if self._is_blacklisted(symbol):
            self.stats.blacklisted += 1
            return 0
        
        if not self.quality_filter.passes_all_filters(token_data):
            return 0
        
        if symbol in self.watchlist[chain]:
            return 0
        
        self._add_token_to_watchlist(chain, symbol, token_data)
        return 1
    
    def _validate_token_symbol(self, symbol: str) -> bool:
        """Валидация символа токена"""
        return bool(symbol) and len(symbol) <= 10
    
    def _is_blacklisted(self, symbol: str) -> bool:
        """Проверка в blacklist"""
        return symbol in self.blacklist
    
    def _add_token_to_watchlist(self, chain: str, symbol: str, token_data: Dict):
        """Добавляет токен в watchlist"""
        self.watchlist[chain].add(symbol)
        
        token = TokenData(
            symbol=symbol,
            name=token_data.get('name', ''),
            chain=chain,
            market_cap=token_data.get('market_cap', 0),
            volume_24h=token_data.get('volume_24h', 0),
            price=token_data.get('price', 0),
            price_change_24h=token_data.get('price_change_24h', 0),
            age_days=token_data.get('age_days', 0),
            added_at=datetime.utcnow(),
            manual=False
        )
        
        self.token_metadata[f'{chain}:{symbol}'] = token
    
    def _update_stats(self):
        """Обновляет статистику"""
        self.stats.total_discovered = sum(
            len(tokens) for tokens in self.watchlist.values()
        )
        
        self.stats.by_chain = {
            chain: len(tokens)
            for chain, tokens in self.watchlist.items()
            if tokens
        }
        
        self.stats.last_refresh = datetime.utcnow()
    
    def _print_refresh_summary(self, new_tokens_count: Dict[str, int], elapsed: int):
        """Выводит итоги обновления"""
        print(f'\n{"=" * 80}')
        print(f'✅ [DISCOVERY] Обновление завершено за {elapsed}с')
        print(f'{"=" * 80}')
        
        print(f'\n📊 [STATS] Результаты:')
        for chain in self.chains:
            total = len(self.watchlist.get(chain, set()))
            new = new_tokens_count.get(chain, 0)
            print(f'   {chain:12s}: {total:4d} токенов (+{new} новых)')
        
        print(f'\n   Всего токенов: {self.stats.total_discovered}')
        print(f'   Заблокировано: {self.stats.blacklisted}')
        print(f'{"=" * 80}\n')
    
    def is_in_watchlist(self, chain: str, asset: str) -> bool:
        """Проверяет находится ли актив в watchlist"""
        return asset.upper() in self.watchlist.get(chain, set())
    
    def get_watchlist_for_chain(self, chain: str) -> Set[str]:
        """Возвращает watchlist для конкретного chain"""
        return self.watchlist.get(chain, set()).copy()
    
    def get_full_watchlist(self) -> Dict[str, Set[str]]:
        """Возвращает полный watchlist"""
        return {chain: tokens.copy() for chain, tokens in self.watchlist.items()}
    
    def get_token_metadata(self, chain: str, asset: str) -> Optional[TokenData]:
        """Получает метаданные токена"""
        key = f'{chain}:{asset.upper()}'
        return self.token_metadata.get(key)
    
    def add_manual_token(
        self,
        chain: str,
        asset: str,
        metadata: Optional[Dict] = None
    ):
        """Добавляет токен в watchlist вручную"""
        symbol = asset.upper()
        
        if symbol in self.watchlist[chain]:
            print(f'ℹ️  [DISCOVERY] Токен уже существует: {chain}:{symbol}')
            return
        
        self.watchlist[chain].add(symbol)
        
        token = TokenData(
            symbol=symbol,
            name=metadata.get('name', symbol) if metadata else symbol,
            chain=chain,
            market_cap=metadata.get('market_cap', 0) if metadata else 0,
            volume_24h=metadata.get('volume_24h', 0) if metadata else 0,
            price=metadata.get('price', 0) if metadata else 0,
            added_at=datetime.utcnow(),
            manual=True
        )
        
        self.token_metadata[f'{chain}:{symbol}'] = token
        self._save_watchlist()
        
        print(f'✅ [DISCOVERY] Вручную добавлен: {chain}:{symbol}')
    
    def remove_token(self, chain: str, asset: str):
        """Удаляет токен из watchlist"""
        symbol = asset.upper()
        
        if symbol not in self.watchlist.get(chain, set()):
            print(f'ℹ️  [DISCOVERY] Токен не найден: {chain}:{symbol}')
            return
        
        self.watchlist[chain].discard(symbol)
        
        key = f'{chain}:{symbol}'
        if key in self.token_metadata:
            del self.token_metadata[key]
        
        self._save_watchlist()
        print(f'❌ [DISCOVERY] Удален: {chain}:{symbol}')
    
    def _save_watchlist(self):
        """Сохраняет watchlist в файл"""
        self.storage.save(self.watchlist, self.token_metadata, self.stats)
    
    def _load_watchlist(self):
        """Загружает watchlist из файла"""
        watchlist, metadata, stats = self.storage.load()
        
        self.watchlist = watchlist
        self.token_metadata = metadata
        self.stats = stats
        
        if self.stats.total_discovered > 0:
            print(f'\n📊 [DISCOVERY] Загружено по chains:')
            for chain in self.chains:
                count = len(self.watchlist.get(chain, set()))
                if count > 0:
                    print(f'   {chain}: {count} токенов')
    
    def get_stats(self) -> Dict:
        """Возвращает статистику discovery"""
        return {
            'total_tokens': self.stats.total_discovered,
            'by_chain': dict(self.stats.by_chain),
            'blacklisted': self.stats.blacklisted,
            'last_refresh': (
                self.stats.last_refresh.isoformat()
                if self.stats.last_refresh
                else None
            ),
            'chains_monitored': len([
                c for c in self.chains
                if self.watchlist.get(c)
            ])
        }
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        stats = self.get_stats()
        
        print('\n' + '=' * 80)
        print('📊 DISCOVERY ENGINE STATISTICS')
        print('=' * 80)
        
        print(f'\n🎯 Total Tokens: {stats["total_tokens"]}')
        print(f'⛓️  Chains Monitored: {stats["chains_monitored"]}/{len(self.chains)}')
        print(f'🚫 Blacklisted: {stats["blacklisted"]}')
        print(f'🕐 Last Refresh: {stats["last_refresh"] or "Never"}')
        
        print(f'\n📊 By Chain:')
        for chain, count in sorted(
            stats['by_chain'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f'   {chain:12s}: {count:4d} tokens')
        
        print('\n' + '=' * 80 + '\n')