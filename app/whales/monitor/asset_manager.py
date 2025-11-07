# app/whales/monitor/asset_manager.py
"""
Dynamic Asset Manager v1.0
Auto-updates top crypto assets from CoinGecko
"""

import asyncio
import aiohttp
from typing import List, Set, Dict, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path


class AssetManager:
    """Управление списком отслеживаемых активов"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / 'top_assets.json'
        self.last_update: Optional[datetime] = None
        self.update_interval = timedelta(hours=24)
        
        self.top_assets: List[str] = []
        self.asset_metadata: Dict[str, Dict] = {}
        
        self.default_assets = [
            'BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'XRP', 'USDC', 'ADA', 'AVAX', 'DOGE',
            'TRX', 'DOT', 'MATIC', 'DAI', 'LINK', 'TON', 'WBTC', 'SHIB', 'UNI', 'LTC',
            'BCH', 'LEO', 'ATOM', 'XLM', 'XMR', 'OKB', 'ICP', 'ETC', 'FIL', 'APT',
            'HBAR', 'ARB', 'VET', 'MKR', 'LDO', 'INJ', 'NEAR', 'STX', 'QNT', 'RUNE',
            'AAVE', 'GRT', 'OP', 'ALGO', 'EOS', 'IMX', 'SAND', 'MANA', 'FTM', 'THETA'
        ]
        
        self.stablecoin_blacklist = {
            'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'FRAX', 'PYUSD'
        }
    
    async def initialize(self):
        """Инициализация - загружает кэш или обновляет"""
        if self._load_from_cache():
            print(f"✅ [ASSETS] Загружено {len(self.top_assets)} активов из кэша")
            
            if self._should_update():
                print(f"🔄 [ASSETS] Кэш устарел, обновляю...")
                await self.update_assets()
        else:
            print(f"📥 [ASSETS] Кэш не найден, загружаю топ активы...")
            await self.update_assets()
    
    async def update_assets(self, top_n: int = 200):
        """Обновляет список топ активов из CoinGecko"""
        try:
            async with aiohttp.ClientSession() as session:
                assets = await self._fetch_top_assets(session, top_n)
                
                if assets:
                    self.top_assets = assets
                    self.last_update = datetime.utcnow()
                    self._save_to_cache()
                    
                    print(f"✅ [ASSETS] Обновлено: {len(self.top_assets)} активов")
                else:
                    print(f"⚠️ [ASSETS] Не удалось обновить, используем кэш")
        
        except Exception as e:
            print(f"❌ [ASSETS] Ошибка обновления: {e}")
            
            if not self.top_assets:
                self.top_assets = self.default_assets.copy()
                print(f"📋 [ASSETS] Используем дефолтный список: {len(self.top_assets)} активов")
    
    async def _fetch_top_assets(
        self,
        session: aiohttp.ClientSession,
        top_n: int
    ) -> List[str]:
        """Получает топ N монет из CoinGecko"""
        try:
            url = 'https://api.coingecko.com/api/v3/coins/markets'
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': min(top_n, 250),
                'page': 1,
                'sparkline': False,
                'locale': 'en'
            }
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 429:
                    await asyncio.sleep(60)
                    return []
                
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                assets = []
                for coin in data:
                    symbol = coin.get('symbol', '').upper()
                    
                    if symbol in self.stablecoin_blacklist:
                        continue
                    
                    if not symbol or len(symbol) > 10:
                        continue
                    
                    market_cap = coin.get('market_cap', 0)
                    if market_cap < 1_000_000:
                        continue
                    
                    assets.append(symbol)
                    
                    self.asset_metadata[symbol] = {
                        'name': coin.get('name', ''),
                        'market_cap': market_cap,
                        'volume_24h': coin.get('total_volume', 0),
                        'price': coin.get('current_price', 0)
                    }
                
                return assets
        
        except asyncio.TimeoutError:
            print(f"⏱️ [ASSETS] Timeout при загрузке из CoinGecko")
            return []
        
        except Exception as e:
            print(f"❌ [ASSETS] Ошибка загрузки: {e}")
            return []
    
    def get_top_assets(self, limit: Optional[int] = None) -> List[str]:
        """Возвращает список топ активов"""
        if limit:
            return self.top_assets[:limit]
        return self.top_assets.copy()
    
    def is_tracked(self, symbol: str) -> bool:
        """Проверяет отслеживается ли актив"""
        return symbol.upper() in self.top_assets
    
    def get_metadata(self, symbol: str) -> Optional[Dict]:
        """Возвращает метаданные актива"""
        return self.asset_metadata.get(symbol.upper())
    
    def _should_update(self) -> bool:
        """Проверяет нужно ли обновить список"""
        if not self.last_update:
            return True
        
        return datetime.utcnow() - self.last_update > self.update_interval
    
    def _load_from_cache(self) -> bool:
        """Загружает список из кэша"""
        try:
            if not self.cache_file.exists():
                return False
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.top_assets = data.get('assets', [])
            self.asset_metadata = data.get('metadata', {})
            
            last_update_str = data.get('last_update')
            if last_update_str:
                self.last_update = datetime.fromisoformat(last_update_str)
            
            return bool(self.top_assets)
        
        except Exception as e:
            print(f"⚠️ [ASSETS] Ошибка загрузки кэша: {e}")
            return False
    
    def _save_to_cache(self):
        """Сохраняет список в кэш"""
        try:
            data = {
                'assets': self.top_assets,
                'metadata': self.asset_metadata,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️ [ASSETS] Ошибка сохранения кэша: {e}")