# app/whales/discovery.py
import aiohttp
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set
from app import settings

class DiscoveryEngine:
    """Формирует watchlist.json для Discovery-режима (все сети)"""
    
    def __init__(self):
        self.watchlist_path = settings.WATCHLIST_FILE
        self.blacklist: Set[str] = set(settings.DISCOVERY_BLACKLIST)
        self.min_age_days = settings.MIN_TOKEN_AGE_DAYS
        self.top_n = settings.DISCOVERY_TOP_N_PER_CHAIN
        
    async def refresh_watchlist(self):
        """Обновляет watchlist со всех цепей"""
        print(f"🔍 [DISCOVERY] Запуск обновления watchlist (топ-{self.top_n} на цепь)")
        
        watchlist = {
            "updated_at": datetime.utcnow().isoformat(),
            "chains": {}
        }
        
        async with aiohttp.ClientSession() as session:
            # EVM chains
            evm_chains = ["ethereum", "bsc", "polygon", "arbitrum", "base", "avalanche"]
            for chain in evm_chains:
                try:
                    tokens = await self._fetch_evm_tokens(session, chain)
                    watchlist["chains"][chain] = tokens
                    print(f"  ✓ {chain}: {len(tokens)} токенов")
                except Exception as e:
                    print(f"  ✗ {chain}: ошибка - {e}")
                await asyncio.sleep(1)
            
            # Solana
            try:
                sol_tokens = await self._fetch_solana_tokens(session)
                watchlist["chains"]["solana"] = sol_tokens
                print(f"  ✓ solana: {len(sol_tokens)} токенов")
            except Exception as e:
                print(f"  ✗ solana: ошибка - {e}")
            
            # TRON
            try:
                tron_tokens = await self._fetch_tron_tokens(session)
                watchlist["chains"]["tron"] = tron_tokens
                print(f"  ✓ tron: {len(tron_tokens)} токенов")
            except Exception as e:
                print(f"  ✗ tron: ошибка - {e}")
            
            # Bitcoin
            watchlist["chains"]["bitcoin"] = [
                {"symbol": "BTC", "name": "Bitcoin", "volume_24h": 0, "market_cap": 0}
            ]
            print(f"  ✓ bitcoin: базовая поддержка")
        
        # Сохраняем
        with open(self.watchlist_path, 'w') as f:
            json.dump(watchlist, f, indent=2)
        
        total = sum(len(v) for v in watchlist["chains"].values())
        print(f"✅ [DISCOVERY] Watchlist обновлён: {total} токенов в {len(watchlist['chains'])} сетях")
        
    async def _fetch_evm_tokens(self, session: aiohttp.ClientSession, chain: str) -> List[Dict]:
        """Получает топ EVM-токены через CoinGecko"""
        platform_map = {
            "ethereum": "ethereum",
            "bsc": "binance-smart-chain",
            "polygon": "polygon-pos",
            "arbitrum": "arbitrum-one",
            "base": "base",
            "avalanche": "avalanche"
        }
        
        platform_id = platform_map.get(chain)
        if not platform_id:
            return []
        
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": False
        }
        
        if settings.COINGECKO_API_KEY:
            params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
        
        try:
            async with session.get(url, params=params, timeout=30) as resp:
                if resp.status == 429:
                    print(f"⚠️  [DISCOVERY] CoinGecko rate limit, используем fallback")
                    await asyncio.sleep(60)
                    return await self._fetch_evm_tokens_fallback(session, chain)
                
                if resp.status != 200:
                    raise Exception(f"CoinGecko API error: {resp.status}")
                
                data = await resp.json()
                
                tokens = []
                for coin in data:
                    platforms = coin.get("platforms", {})
                    contract = platforms.get(platform_id)
                    
                    if not contract:
                        continue
                    
                    if coin["symbol"].upper() in self.blacklist:
                        continue
                    
                    if self.min_age_days > 0:
                        atl_date = coin.get("atl_date")
                        if atl_date:
                            try:
                                age = (datetime.utcnow() - datetime.fromisoformat(atl_date.replace("Z", "+00:00"))).days
                                if age < self.min_age_days:
                                    continue
                            except:
                                pass
                    
                    tokens.append({
                        "symbol": coin["symbol"].upper(),
                        "name": coin["name"],
                        "contract": contract,
                        "volume_24h": coin.get("total_volume", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "coingecko_id": coin.get("id")
                    })
                    
                    if len(tokens) >= self.top_n:
                        break
                
                return tokens
                
        except Exception as e:
            print(f"⚠️  [DISCOVERY] Ошибка для {chain}: {e}")
            return []
    
    async def _fetch_evm_tokens_fallback(self, session: aiohttp.ClientSession, chain: str) -> List[Dict]:
        """Fallback: хардкод топ-токенов"""
        
        fallback_tokens = {
            "ethereum": [
                {"symbol": "ETH", "name": "Ethereum", "contract": None},
                {"symbol": "USDT", "name": "Tether USD", "contract": "0xdac17f958d2ee523a2206206994597c13d831ec7"},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},
                {"symbol": "WETH", "name": "Wrapped Ether", "contract": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"},
                {"symbol": "WBTC", "name": "Wrapped Bitcoin", "contract": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"},
            ],
            "bsc": [
                {"symbol": "BNB", "name": "BNB", "contract": None},
                {"symbol": "USDT", "name": "Tether USD", "contract": "0x55d398326f99059ff775485246999027b3197955"},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"},
            ],
            "polygon": [
                {"symbol": "MATIC", "name": "Polygon", "contract": None},
                {"symbol": "USDT", "name": "Tether USD", "contract": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f"},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"},
            ],
            "arbitrum": [
                {"symbol": "ETH", "name": "Ethereum", "contract": None},
                {"symbol": "USDT", "name": "Tether USD", "contract": "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9"},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0xaf88d065e77c8cc2239327c5edb3a432268e5831"},
            ],
            "base": [
                {"symbol": "ETH", "name": "Ethereum", "contract": None},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"},
            ],
            "avalanche": [
                {"symbol": "AVAX", "name": "Avalanche", "contract": None},
                {"symbol": "USDT", "name": "Tether USD", "contract": "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7"},
                {"symbol": "USDC", "name": "USD Coin", "contract": "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e"},
            ]
        }
        
        tokens = fallback_tokens.get(chain, [])
        for token in tokens:
            token["volume_24h"] = 0
            token["market_cap"] = 0
            token["coingecko_id"] = ""
        
        return tokens[:self.top_n]
    
    async def _fetch_solana_tokens(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Получает топ Solana SPL токены"""
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": False
        }
        
        if settings.COINGECKO_API_KEY:
            params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
        
        try:
            async with session.get(url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    raise Exception(f"CoinGecko API error: {resp.status}")
                
                data = await resp.json()
                
                tokens = []
                for coin in data:
                    platforms = coin.get("platforms", {})
                    mint = platforms.get("solana")
                    
                    if not mint:
                        continue
                    
                    if coin["symbol"].upper() in self.blacklist:
                        continue
                    
                    tokens.append({
                        "symbol": coin["symbol"].upper(),
                        "name": coin["name"],
                        "mint": mint,
                        "volume_24h": coin.get("total_volume", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "coingecko_id": coin.get("id")
                    })
                    
                    if len(tokens) >= self.top_n:
                        break
                
                return tokens
                
        except Exception as e:
            print(f"⚠️  [DISCOVERY] Ошибка Solana: {e}")
            return [
                {"symbol": "SOL", "name": "Solana", "mint": None, "volume_24h": 0, "market_cap": 0},
                {"symbol": "USDC", "name": "USD Coin", "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "volume_24h": 0, "market_cap": 0},
            ]
    
    async def _fetch_tron_tokens(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Получает топ TRON TRC20 токены"""
        return [
            {"symbol": "TRX", "name": "TRON", "contract": None, "volume_24h": 0, "market_cap": 0},
            {"symbol": "USDT", "name": "Tether USD", "contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "volume_24h": 0, "market_cap": 0},
            {"symbol": "USDC", "name": "USD Coin", "contract": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8", "volume_24h": 0, "market_cap": 0},
        ]
    
    def load_watchlist(self) -> Dict:
        """Загружает watchlist"""
        try:
            with open(self.watchlist_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"chains": {}}
    
    def is_in_watchlist(self, chain: str, symbol: str = None, contract: str = None) -> bool:
        """Проверяет наличие в watchlist"""
        watchlist = self.load_watchlist()
        chain_data = watchlist.get("chains", {}).get(chain, [])
        
        for token in chain_data:
            if symbol and token.get("symbol") == symbol.upper():
                return True
            if contract and token.get("contract") == contract:
                return True
            if contract and token.get("mint") == contract:
                return True
        
        return False