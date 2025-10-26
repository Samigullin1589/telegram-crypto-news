# app/whales/discovery.py
"""
DISCOVERY ENGINE v3.0

Интеллектуальное обнаружение топ-токенов для мониторинга:
- Multi-chain support (Ethereum, BSC, Solana, Base, Arbitrum, Polygon)
- Smart filtering (возраст, объем, ликвидность)
- Automatic blacklist management
- Performance optimization
"""

import aiohttp
import asyncio
import json
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app import settings


class DiscoveryEngine:
    """
    Движок автоматического обнаружения токенов для мониторинга
    """
    
    def __init__(self):
        self.watchlist_file = settings.WATCHLIST_FILE
        self.watchlist: Dict[str, Set[str]] = defaultdict(set)
        self.token_metadata: Dict[str, Dict] = {}
        
        # Chains для мониторинга
        self.chains = ["ethereum", "bsc", "solana", "base", "arbitrum", "polygon"]
        
        # API endpoints
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        self.coingecko_key = settings.COINGECKO_API_KEY
        
        # Кэш для rate limiting
        self.last_api_call = {}
        self.api_call_delay = 1.5  # секунды между запросами
        
        # Статистика
        self.stats = {
            "total_discovered": 0,
            "by_chain": defaultdict(int),
            "blacklisted": 0,
            "last_refresh": None
        }
        
        self._load_watchlist()
    
    # ========================================================================
    # MAIN DISCOVERY
    # ========================================================================
    
    async def refresh_watchlist(self) -> Dict[str, int]:
        """
        Обновляет watchlist новыми топовыми токенами
        
        Returns:
            {"chain": count} - количество токенов по каждому chain
        """
        
        print(f"\n{'=' * 80}")
        print(f"🔍 [DISCOVERY] Обновление watchlist")
        print(f"{'=' * 80}")
        
        start_time = datetime.utcnow()
        new_tokens_count = defaultdict(int)
        
        async with aiohttp.ClientSession() as session:
            # Получаем топ токены для каждого chain
            tasks = [
                self._discover_chain_tokens(chain, session)
                for chain in self.chains
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for chain, result in zip(self.chains, results):
                if isinstance(result, Exception):
                    print(f"❌ [DISCOVERY] Ошибка для {chain}: {result}")
                    continue
                
                if not result:
                    continue
                
                # Фильтруем и добавляем новые токены
                for token_data in result:
                    symbol = token_data.get("symbol", "").upper()
                    
                    if not symbol or len(symbol) > 10:
                        continue
                    
                    # Проверяем blacklist
                    if symbol in settings.DISCOVERY_BLACKLIST:
                        self.stats["blacklisted"] += 1
                        continue
                    
                    # Применяем умные фильтры
                    if not self._passes_quality_filters(token_data):
                        continue
                    
                    # Добавляем в watchlist
                    if symbol not in self.watchlist[chain]:
                        self.watchlist[chain].add(symbol)
                        new_tokens_count[chain] += 1
                        self.stats["by_chain"][chain] += 1
                        
                        # Сохраняем метаданные
                        self.token_metadata[f"{chain}:{symbol}"] = {
                            "name": token_data.get("name", ""),
                            "added_at": datetime.utcnow().isoformat(),
                            "market_cap": token_data.get("market_cap", 0),
                            "volume_24h": token_data.get("volume_24h", 0),
                            "price": token_data.get("price", 0)
                        }
        
        # Сохраняем обновленный watchlist
        self._save_watchlist()
        
        elapsed = (datetime.utcnow() - start_time).seconds
        self.stats["total_discovered"] = sum(len(tokens) for tokens in self.watchlist.values())
        self.stats["last_refresh"] = datetime.utcnow()
        
        print(f"\n{'=' * 80}")
        print(f"✅ [DISCOVERY] Обновление завершено за {elapsed}с")
        print(f"{'=' * 80}")
        
        # Выводим статистику
        print(f"\n📊 [STATS] Результаты:")
        for chain in self.chains:
            total = len(self.watchlist.get(chain, set()))
            new = new_tokens_count.get(chain, 0)
            print(f"   {chain:12s}: {total:4d} токенов (+{new} новых)")
        
        print(f"\n   Всего токенов: {self.stats['total_discovered']}")
        print(f"   Заблокировано: {self.stats['blacklisted']}")
        print(f"{'=' * 80}\n")
        
        return dict(new_tokens_count)
    
    async def _discover_chain_tokens(
        self, 
        chain: str, 
        session: aiohttp.ClientSession
    ) -> List[Dict]:
        """
        Получает топ токены для конкретного chain
        
        Args:
            chain: Название blockchain
            session: aiohttp сессия
        
        Returns:
            Список токенов с метаданными
        """
        
        print(f"🔍 [DISCOVERY] Запрос топ-{settings.DISCOVERY_TOP_N_PER_CHAIN} для {chain}")
        
        try:
            # Маппинг chain -> CoinGecko platform
            platform_map = {
                "ethereum": "ethereum",
                "bsc": "binance-smart-chain",
                "solana": "solana",
                "base": "base",
                "arbitrum": "arbitrum-one",
                "polygon": "polygon-pos"
            }
            
            platform_id = platform_map.get(chain)
            if not platform_id:
                print(f"⚠️  [DISCOVERY] Неизвестный chain: {chain}")
                return []
            
            # Rate limiting
            await self._wait_for_rate_limit(f"coingecko_{chain}")
            
            # CoinGecko API
            url = f"{self.coingecko_api}/coins/markets"
            params = {
                "vs_currency": "usd",
                "category": "cryptocurrency",
                "order": "volume_desc",
                "per_page": settings.DISCOVERY_TOP_N_PER_CHAIN,
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h",
                "locale": "en"
            }
            
            # Добавляем API key если есть
            if self.coingecko_key:
                params["x_cg_pro_api_key"] = self.coingecko_key
            
            headers = {
                "Accept": "application/json",
                "User-Agent": "CryptoCompass/3.0"
            }
            
            async with session.get(url, params=params, headers=headers, timeout=30) as response:
                if response.status == 429:
                    print(f"⚠️  [DISCOVERY] Rate limit для {chain}, жду...")
                    await asyncio.sleep(60)
                    return []
                
                if response.status != 200:
                    print(f"⚠️  [DISCOVERY] CoinGecko вернул {response.status} для {chain}")
                    return []
                
                data = await response.json()
            
            # Фильтруем по platform
            tokens = []
            for coin in data:
                # Проверяем что токен на нужном chain
                platforms = coin.get("platforms", {})
                
                # CoinGecko иногда не возвращает platforms, используем heuristic
                if platforms and platform_id not in platforms:
                    continue
                
                tokens.append({
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name", ""),
                    "market_cap": coin.get("market_cap", 0),
                    "volume_24h": coin.get("total_volume", 0),
                    "price": coin.get("current_price", 0),
                    "price_change_24h": coin.get("price_change_percentage_24h", 0),
                    "age_days": self._estimate_token_age(coin),
                    "chain": chain
                })
            
            print(f"✅ [DISCOVERY] {chain}: найдено {len(tokens)} токенов")
            return tokens
        
        except asyncio.TimeoutError:
            print(f"⏱️  [DISCOVERY] Timeout для {chain}")
            return []
        
        except Exception as e:
            print(f"❌ [DISCOVERY] Ошибка для {chain}: {e}")
            return []
    
    # ========================================================================
    # QUALITY FILTERS
    # ========================================================================
    
    def _passes_quality_filters(self, token_data: Dict) -> bool:
        """
        Применяет умные фильтры качества токена
        
        Фильтры:
        1. Минимальный возраст токена
        2. Минимальный объем торговли
        3. Минимальная капитализация
        4. Стабильность цены (не пампы/дампы)
        """
        
        # 1. Возраст токена
        age_days = token_data.get("age_days", 0)
        if age_days < settings.MIN_TOKEN_AGE_DAYS:
            return False
        
        # 2. Объем торговли
        volume_24h = token_data.get("volume_24h", 0)
        if volume_24h < 100_000:  # минимум $100k volume
            return False
        
        # 3. Капитализация
        market_cap = token_data.get("market_cap", 0)
        if market_cap < 1_000_000:  # минимум $1M market cap
            return False
        
        # 4. Стабильность цены (отфильтровываем экстремальные пампы/дампы)
        price_change = abs(token_data.get("price_change_24h", 0))
        if price_change > 200:  # больше ±200% за 24ч - подозрительно
            return False
        
        return True
    
    def _estimate_token_age(self, coin_data: Dict) -> int:
        """
        Оценивает возраст токена на основе данных CoinGecko
        
        Returns:
            Возраст в днях (приблизительный)
        """
        
        # CoinGecko не всегда предоставляет точную дату создания
        # Используем heuristics:
        
        # 1. Если есть ath_date (all-time high date)
        if "ath_date" in coin_data and coin_data["ath_date"]:
            try:
                ath_date = datetime.fromisoformat(coin_data["ath_date"].replace("Z", "+00:00"))
                days_since_ath = (datetime.utcnow() - ath_date).days
                
                # ATH обычно не в первый день, добавляем буфер
                return days_since_ath + 30
            except:
                pass
        
        # 2. По market cap rank (чем выше rank, тем старше обычно)
        market_cap_rank = coin_data.get("market_cap_rank", 9999)
        if market_cap_rank < 100:
            return 365  # топ-100 обычно старые проекты
        elif market_cap_rank < 500:
            return 180
        elif market_cap_rank < 2000:
            return 90
        
        # 3. Дефолт для новых/неизвестных
        return 30
    
    # ========================================================================
    # WATCHLIST MANAGEMENT
    # ========================================================================
    
    def is_in_watchlist(self, chain: str, asset: str) -> bool:
        """Проверяет находится ли актив в watchlist"""
        return asset.upper() in self.watchlist.get(chain, set())
    
    def get_watchlist_for_chain(self, chain: str) -> Set[str]:
        """Возвращает watchlist для конкретного chain"""
        return self.watchlist.get(chain, set()).copy()
    
    def get_full_watchlist(self) -> Dict[str, Set[str]]:
        """Возвращает полный watchlist"""
        return {chain: tokens.copy() for chain, tokens in self.watchlist.items()}
    
    def get_token_metadata(self, chain: str, asset: str) -> Optional[Dict]:
        """Получает метаданные токена"""
        key = f"{chain}:{asset.upper()}"
        return self.token_metadata.get(key)
    
    def add_manual_token(self, chain: str, asset: str, metadata: Dict = None):
        """
        Добавляет токен в watchlist вручную
        
        Args:
            chain: Blockchain
            asset: Символ токена
            metadata: Опциональные метаданные
        """
        
        symbol = asset.upper()
        
        if symbol not in self.watchlist[chain]:
            self.watchlist[chain].add(symbol)
            
            if metadata:
                self.token_metadata[f"{chain}:{symbol}"] = {
                    **metadata,
                    "added_at": datetime.utcnow().isoformat(),
                    "manual": True
                }
            
            self._save_watchlist()
            print(f"✅ [DISCOVERY] Вручную добавлен: {chain}:{symbol}")
    
    def remove_token(self, chain: str, asset: str):
        """Удаляет токен из watchlist"""
        
        symbol = asset.upper()
        
        if symbol in self.watchlist.get(chain, set()):
            self.watchlist[chain].discard(symbol)
            
            key = f"{chain}:{symbol}"
            if key in self.token_metadata:
                del self.token_metadata[key]
            
            self._save_watchlist()
            print(f"❌ [DISCOVERY] Удален: {chain}:{symbol}")
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _save_watchlist(self):
        """Сохраняет watchlist в файл"""
        
        try:
            data = {
                "watchlist": {
                    chain: list(tokens) 
                    for chain, tokens in self.watchlist.items()
                },
                "metadata": self.token_metadata,
                "stats": {
                    "total_discovered": self.stats["total_discovered"],
                    "by_chain": dict(self.stats["by_chain"]),
                    "blacklisted": self.stats["blacklisted"],
                    "last_refresh": self.stats["last_refresh"].isoformat() if self.stats["last_refresh"] else None
                },
                "version": "3.0",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            with open(self.watchlist_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 [DISCOVERY] Watchlist сохранен ({self.stats['total_discovered']} токенов)")
        
        except Exception as e:
            print(f"⚠️  [DISCOVERY] Ошибка сохранения watchlist: {e}")
    
    def _load_watchlist(self):
        """Загружает watchlist из файла"""
        
        try:
            with open(self.watchlist_file, 'r') as f:
                data = json.load(f)
            
            # Восстанавливаем watchlist
            for chain, tokens in data.get("watchlist", {}).items():
                self.watchlist[chain] = set(tokens)
            
            # Восстанавливаем метаданные
            self.token_metadata = data.get("metadata", {})
            
            # Восстанавливаем статистику
            stats = data.get("stats", {})
            self.stats["total_discovered"] = stats.get("total_discovered", 0)
            self.stats["by_chain"] = defaultdict(int, stats.get("by_chain", {}))
            self.stats["blacklisted"] = stats.get("blacklisted", 0)
            
            if last_refresh := stats.get("last_refresh"):
                self.stats["last_refresh"] = datetime.fromisoformat(last_refresh)
            
            print(f"📂 [DISCOVERY] Загружен watchlist ({self.stats['total_discovered']} токенов)")
            
            # Показываем статистику по chains
            for chain in self.chains:
                count = len(self.watchlist.get(chain, set()))
                if count > 0:
                    print(f"   {chain}: {count} токенов")
        
        except FileNotFoundError:
            print(f"📂 [DISCOVERY] Watchlist не найден, создам новый")
            self.watchlist = defaultdict(set)
            self.token_metadata = {}
        
        except Exception as e:
            print(f"⚠️  [DISCOVERY] Ошибка загрузки watchlist: {e}")
            self.watchlist = defaultdict(set)
            self.token_metadata = {}
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    async def _wait_for_rate_limit(self, key: str):
        """Rate limiting для API запросов"""
        
        if key in self.last_api_call:
            elapsed = (datetime.utcnow() - self.last_api_call[key]).total_seconds()
            
            if elapsed < self.api_call_delay:
                wait_time = self.api_call_delay - elapsed
                await asyncio.sleep(wait_time)
        
        self.last_api_call[key] = datetime.utcnow()
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict:
        """Возвращает статистику discovery"""
        
        return {
            "total_tokens": self.stats["total_discovered"],
            "by_chain": dict(self.stats["by_chain"]),
            "blacklisted": self.stats["blacklisted"],
            "last_refresh": self.stats["last_refresh"].isoformat() if self.stats["last_refresh"] else None,
            "chains_monitored": len([c for c in self.chains if self.watchlist.get(c)])
        }
    
    def print_stats(self):
        """Выводит статистику в консоль"""
        
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("📊 DISCOVERY ENGINE STATISTICS")
        print("=" * 80)
        
        print(f"\n🎯 Total Tokens: {stats['total_tokens']}")
        print(f"⛓️  Chains Monitored: {stats['chains_monitored']}/{len(self.chains)}")
        print(f"🚫 Blacklisted: {stats['blacklisted']}")
        print(f"🕐 Last Refresh: {stats['last_refresh'] or 'Never'}")
        
        print(f"\n📊 By Chain:")
        for chain, count in sorted(stats['by_chain'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {chain:12s}: {count:4d} tokens")
        
        print("\n" + "=" * 80 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_discovery_engine() -> DiscoveryEngine:
    """
    Создает instance Discovery Engine
    
    Usage:
        from app.whales.discovery import create_discovery_engine
        
        discovery = create_discovery_engine()
        await discovery.refresh_watchlist()
    """
    return DiscoveryEngine()