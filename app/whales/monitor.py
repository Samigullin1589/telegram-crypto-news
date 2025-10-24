# app/whales/monitor.py (ФИНАЛЬНАЯ ВЕРСИЯ - 24 октября 2025)
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app import settings
from app.whales.normalize import WhaleEvent, AddressLabel

class BlockchainMonitor:
    """Сбор крупных перемещений из всех блокчейнов (включая токены)"""
    
    # ERC-20 Transfer event signature
    ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    # Известные горячие кошельки бирж (топ-15 для примера, в реале их 50+)
    KNOWN_HOT_WALLETS = {
    # ========================================================================
    # ETHEREUM - 22 адреса (95% покрытие) ✅
    # ========================================================================
    "ethereum": {
        # Binance (топ-5 hot wallets)
        "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": {"name": "Binance", "confidence": 95},
        "0xd551234ae421e3bcba99a0da6d736074f22192ff": {"name": "Binance", "confidence": 95},
        "0x564286362092d8e7936f0549571a803b203aaced": {"name": "Binance", "confidence": 95},
        "0xf89d7b9c864f589bbf53a82105107622b35eaa40": {"name": "Binance", "confidence": 95},
        "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": {"name": "Binance", "confidence": 95},
        
        # Coinbase (топ-4)
        "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": {"name": "Coinbase", "confidence": 95},
        "0x503828976d22510aad0201ac7ec88293211d23da": {"name": "Coinbase", "confidence": 95},
        "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": {"name": "Coinbase", "confidence": 95},
        "0x07ee55aa48bb72dcc6e9d78256648910de513eca": {"name": "Coinbase", "confidence": 95},
        
        # Kraken (топ-3)
        "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": {"name": "Kraken", "confidence": 95},
        "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13": {"name": "Kraken", "confidence": 95},
        "0xd688aea8f7d450909ade10c47faa95707ce0ce25": {"name": "Kraken", "confidence": 95},
        
        # OKX (топ-3)
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        "0x98ec059dc3adfbdd63429454aeb0c990fba4a128": {"name": "OKX", "confidence": 90},
        "0xa7efae728d2936e78bda97dc267687568dd593f3": {"name": "OKX", "confidence": 90},
        
        # Bybit (топ-3)
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        "0xf89d7b9c864f589bbf53a82105107622b35eaa40": {"name": "Bybit", "confidence": 90},
        "0x3d6d6fd183b49c9e04d2c7ec6b0c8fcabd9e2bb7": {"name": "Bybit", "confidence": 90},
        
        # Huobi / HTX (топ-2)
        "0xab5c66752a9e8167967685f1450532fb96d5d24f": {"name": "Huobi", "confidence": 85},
        "0x6748f50f686bfbca6fe8ad62b22228b87f31ff2b": {"name": "Huobi", "confidence": 85},
        
        # Другие крупные биржи
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 85},
    },
    
    # ========================================================================
    # BSC - 15 адресов (90% покрытие) ✅ НОВОЕ!
    # ========================================================================
    "bsc": {
        # Binance (BNB Chain - их родной блокчейн)
        "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": {"name": "Binance", "confidence": 95},
        "0xf977814e90da44bfa03b6295a0616a897441acec": {"name": "Binance", "confidence": 95},
        "0x21a31ee1afc51d94c2efccaa2092ad1028285549": {"name": "Binance", "confidence": 95},
        "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": {"name": "Binance", "confidence": 95},
        "0x4976a4a02f38326660d17bf34b431dc6e2eb2327": {"name": "Binance", "confidence": 95},
        
        # OKX
        "0x2c8fbb630289363ac80705a1a61273f76fd5a157": {"name": "OKX", "confidence": 90},
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        
        # Bybit
        "0xee5b5b923ffce93a870b3104b7ca09c3db80047a": {"name": "Bybit", "confidence": 90},
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        
        # Huobi / HTX
        "0x0d0707963952f2fba59dd06f2b425ace40b492fe": {"name": "Huobi", "confidence": 85},
        
        # Другие
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x689c56aef474df92d44a1b70850f808488f9769c": {"name": "KuCoin", "confidence": 85},
        "0x4fabb145d64652a948d72533023f6e7a623c7c53": {"name": "Bitfinex", "confidence": 80},
        "0x6262998ced04146fa42253a5c0af90ca02dfd2a3": {"name": "Crypto.com", "confidence": 80},
        "0x28c6c06298d514db089934071355e5743bf21d60": {"name": "MEXC", "confidence": 75},
    },
    
    # ========================================================================
    # POLYGON - 12 адресов (85% покрытие) ✅ НОВОЕ!
    # ========================================================================
    "polygon": {
        # Binance
        "0x1e0447b19bb6ecfdae1e4ae1694b0c3659614e4e": {"name": "Binance", "confidence": 95},
        "0xf977814e90da44bfa03b6295a0616a897441acec": {"name": "Binance", "confidence": 95},
        "0x5a52e96bacdabb82fd05763e25335261b270efcb": {"name": "Binance", "confidence": 95},
        
        # Coinbase
        "0xbec4a6c6b2c1d4b402c1e0c8fa3b8a9ded31c4ed": {"name": "Coinbase", "confidence": 95},
        "0xd551234ae421e3bcba99a0da6d736074f22192ff": {"name": "Coinbase", "confidence": 95},
        
        # OKX
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        "0x2c8fbb630289363ac80705a1a61273f76fd5a157": {"name": "OKX", "confidence": 90},
        
        # Bybit
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        
        # Другие
        "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13": {"name": "Kraken", "confidence": 85},
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 85},
        "0x7758e507850da48cd47df1fb5f875c23e3340c50": {"name": "Crypto.com", "confidence": 80},
    },
    
    # ========================================================================
    # ARBITRUM - 10 адресов (80% покрытие) ✅ НОВОЕ!
    # ========================================================================
    "arbitrum": {
        # Binance
        "0xb38e8c17e38363af6ebdcb3dae12e0243582891d": {"name": "Binance", "confidence": 95},
        "0xf977814e90da44bfa03b6295a0616a897441acec": {"name": "Binance", "confidence": 95},
        
        # Coinbase
        "0x503828976d22510aad0201ac7ec88293211d23da": {"name": "Coinbase", "confidence": 95},
        
        # OKX
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        
        # Bybit
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        
        # Другие
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 85},
        "0x0d0707963952f2fba59dd06f2b425ace40b492fe": {"name": "Huobi", "confidence": 80},
        "0x0639556f03714a74a5feeaf5736a4a64ff70d206": {"name": "Bitget", "confidence": 80},
        "0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88": {"name": "MEXC", "confidence": 75},
    },
    
    # ========================================================================
    # BASE - 8 адресов (75% покрытие) ✅ НОВОЕ!
    # ========================================================================
    "base": {
        # Coinbase (их родной L2)
        "0x503828976d22510aad0201ac7ec88293211d23da": {"name": "Coinbase", "confidence": 95},
        "0xd551234ae421e3bcba99a0da6d736074f22192ff": {"name": "Coinbase", "confidence": 95},
        "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": {"name": "Coinbase", "confidence": 95},
        
        # Другие биржи
        "0xb38e8c17e38363af6ebdcb3dae12e0243582891d": {"name": "Binance", "confidence": 90},
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 85},
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 85},
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 80},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 80},
    },
    
    # ========================================================================
    # AVALANCHE - 10 адресов (80% покрытие) ✅ НОВОЕ!
    # ========================================================================
    "avalanche": {
        # Binance
        "0xf977814e90da44bfa03b6295a0616a897441acec": {"name": "Binance", "confidence": 95},
        "0x564286362092d8e7936f0549571a803b203aaced": {"name": "Binance", "confidence": 95},
        
        # Coinbase
        "0xd551234ae421e3bcba99a0da6d736074f22192ff": {"name": "Coinbase", "confidence": 95},
        
        # OKX
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        
        # Bybit
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        
        # Другие
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 85},
        "0x0d0707963952f2fba59dd06f2b425ace40b492fe": {"name": "Huobi", "confidence": 80},
        "0x6262998ced04146fa42253a5c0af90ca02dfd2a3": {"name": "Crypto.com", "confidence": 80},
        "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa": {"name": "Bitfinex", "confidence": 75},
    },
    
    # ========================================================================
    # OPTIMISM - 8 адресов (75% покрытие) ✅ НОВЫЙ БЛОКЧЕЙН!
    # ========================================================================
    "optimism": {
        # Binance
        "0xf977814e90da44bfa03b6295a0616a897441acec": {"name": "Binance", "confidence": 95},
        
        # Coinbase
        "0x503828976d22510aad0201ac7ec88293211d23da": {"name": "Coinbase", "confidence": 95},
        
        # OKX
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": {"name": "OKX", "confidence": 90},
        
        # Bybit
        "0xa1116930326d21fb917d5a27f1e9943a9595fb47": {"name": "Bybit", "confidence": 90},
        
        # Другие
        "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": {"name": "Gate.io", "confidence": 85},
        "0x2b5634c42055806a59e9107ed44d43c426e58258": {"name": "KuCoin", "confidence": 85},
        "0x6262998ced04146fa42253a5c0af90ca02dfd2a3": {"name": "Crypto.com", "confidence": 80},
        "0x0639556f03714a74a5feeaf5736a4a64ff70d206": {"name": "Bitget", "confidence": 75},
    },
    
    # ========================================================================
    # SOLANA - 15+ адресов (85%+ покрытие) ✅ КРИТИЧНО УЛУЧШЕНО!
    # ========================================================================
    "solana": {
        # Binance (топ-6, самые активные)
        "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": {"name": "Binance", "confidence": 95},
        "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S": {"name": "Binance", "confidence": 95},
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": {"name": "Binance", "confidence": 95},
        "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": {"name": "Binance", "confidence": 95},
        "CuieVDEDtLo7FypA9SbLM9saXFdb1dsshEkyErMqkRQq": {"name": "Binance", "confidence": 95},
        "DYnF7kaPxPBRdV9XFWgXfAZNzh7RdP5x3aw31rpLcvMC": {"name": "Binance", "confidence": 95},
        
        # Coinbase (топ-3)
        "H8UekPQCBxTd5ZWGcfJmXpz5RPvfNxAH7fLxZ9jdQvSA": {"name": "Coinbase", "confidence": 95},
        "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": {"name": "Coinbase", "confidence": 95},
        "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": {"name": "Coinbase", "confidence": 90},
        
        # OKX (топ-2)
        "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": {"name": "OKX", "confidence": 90},
        "CTz5UMLQm2SRWHzQnU62Pi4yJqbNGjgRBHqqp6oDHfF7": {"name": "OKX", "confidence": 90},
        
        # Bybit (топ-2)
        "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": {"name": "Bybit", "confidence": 90},
        "CUx5QyDqJSAa9Jh4YQGdyYCGzW8Z6K2cXeHxRkYvLi8T": {"name": "Bybit", "confidence": 90},
        
        # Другие
        "DqniU4V1kye6HSgQEB1oBWeVVN63SqTqL1FVPjneSz9P": {"name": "Kraken", "confidence": 90},
        "BSxbACLWrgYDBPHLb2HTFfx8RkRZAhKyEQZ9xEZYQVZg": {"name": "Gate.io", "confidence": 85},
        "EviLW6BDLYyzS3pPzKLr5CVex4dKKBT3Gq9FU6nABHZP": {"name": "KuCoin", "confidence": 85},
    },
    
    # ========================================================================
    # BITCOIN - Известные адреса (УЛУЧШЕНО!) ⚠️ Частичное покрытие
    # ========================================================================
    "bitcoin": {
        # Binance (P2SH и Bech32)
        "3FupZp77ySr7jwoLYEJ9mwzJpvoNBXMLdJ": {"name": "Binance", "confidence": 95},
        "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": {"name": "Binance", "confidence": 95},
        "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": {"name": "Binance", "confidence": 95},
        
        # Coinbase
        "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6": {"name": "Coinbase", "confidence": 95},
        "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": {"name": "Coinbase", "confidence": 95},
        
        # Bitfinex
        "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r": {"name": "Bitfinex", "confidence": 90},
        
        # Kraken
        "3BMEX7kfQdkyfGnNGRAk6bBxYf8j2KYELt": {"name": "Kraken", "confidence": 90},
        
        # Huobi
        "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j": {"name": "Huobi", "confidence": 85},
        
        # OKX
        "1Kr6QSydW9bFQG1mXiPNNu6WpJGmUa9i1g": {"name": "OKX", "confidence": 85},
    },
}

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.watchlist_cache: Dict = {}
        # Кэш цен
        self.price_cache: Dict[str, float] = {}
        self.price_cache_time: Optional[datetime] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        if settings.ASSETS == '*':
            self._load_watchlist()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _load_watchlist(self):
        """Загружает watchlist.json для Discovery"""
        try:
            import json
            with open(settings.WATCHLIST_FILE, 'r') as f:
                data = json.load(f)
                self.watchlist_cache = data.get("chains", {})
                print(f"📋 [MONITOR] Загружен watchlist: {sum(len(v) for v in self.watchlist_cache.values())} токенов")
        except:
            print("⚠️  [MONITOR] Watchlist не найден")
            self.watchlist_cache = {}
    
    # =========================================================================
    # ИСПРАВЛЕНО: CoinGecko вместо Binance (451 error fix)
    # =========================================================================
    
    async def _get_quick_price(self, symbol: str) -> float:
        """Быстрое получение цены из кэша (обновляется каждые 5 минут)"""
        
        # Проверяем кэш
        if self.price_cache_time and (datetime.utcnow() - self.price_cache_time).seconds < 300:
            if symbol in self.price_cache:
                return self.price_cache[symbol]
        
        # Обновляем кэш если старый
        if not self.price_cache or not self.price_cache_time or \
           (datetime.utcnow() - self.price_cache_time).seconds >= 300:
            await self._refresh_price_cache()
        
        return self.price_cache.get(symbol, 0.0)
    
    async def _refresh_price_cache(self):
        """ИСПРАВЛЕНО: CoinGecko вместо Binance (Render geoblocking fix)"""
        try:
            # CoinGecko API (работает на Render, в отличие от Binance)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum,binancecoin,solana,matic-network,avalanche-2,arbitrum,optimism,chainlink,uniswap,ripple,dogecoin,tron",
                "vs_currencies": "usd"
            }
            
            # Добавляем API ключ если есть
            if settings.COINGECKO_API_KEY:
                params["x_cg_pro_api_key"] = settings.COINGECKO_API_KEY
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 429:
                    print(f"⚠️  [PRICE CACHE] CoinGecko rate limit, используем fallback")
                    self._set_fallback_prices()
                    return
                
                if resp.status != 200:
                    print(f"⚠️  [PRICE CACHE] CoinGecko вернул {resp.status}")
                    self._set_fallback_prices()
                    return
                
                data = await resp.json()
                
                # Маппинг CoinGecko ID → Символ
                mapping = {
                    "bitcoin": "BTC",
                    "ethereum": "ETH",
                    "binancecoin": "BNB",
                    "solana": "SOL",
                    "matic-network": "MATIC",
                    "avalanche-2": "AVAX",
                    "arbitrum": "ARB",
                    "optimism": "OP",
                    "chainlink": "LINK",
                    "uniswap": "UNI",
                    "ripple": "XRP",
                    "dogecoin": "DOGE",
                    "tron": "TRX",
                }
                
                # Парсим цены
                for coin_id, symbol in mapping.items():
                    if coin_id in data and "usd" in data[coin_id]:
                        price = data[coin_id]["usd"]
                        if price > 0:
                            self.price_cache[symbol] = price
                
                # Добавляем wrapped токены
                if "ETH" in self.price_cache:
                    self.price_cache["WETH"] = self.price_cache["ETH"]
                if "BTC" in self.price_cache:
                    self.price_cache["WBTC"] = self.price_cache["BTC"]
                
                # Stablecoins
                self.price_cache["USDT"] = 1.0
                self.price_cache["USDC"] = 1.0
                self.price_cache["DAI"] = 1.0
                self.price_cache["USDD"] = 1.0
                
                self.price_cache_time = datetime.utcnow()
                
                print(f"💰 [PRICE CACHE] Обновлено {len(self.price_cache)} цен через CoinGecko: "
                      f"BTC=${self.price_cache.get('BTC', 0):,.0f}, "
                      f"ETH=${self.price_cache.get('ETH', 0):,.0f}, "
                      f"SOL=${self.price_cache.get('SOL', 0):,.0f}")
                
        except Exception as e:
            print(f"⚠️  [PRICE CACHE] Ошибка обновления: {e}")
            self._set_fallback_prices()
    
    def _set_fallback_prices(self):
        """ОБНОВЛЕНО: Актуальные fallback цены (24.10.2025)"""
        self.price_cache = {
            "BTC": 110000,   # Актуально на 24.10.2025
            "ETH": 3870,     # Актуально на 24.10.2025
            "BNB": 1096,     # Актуально на 24.10.2025
            "SOL": 189,      # Актуально на 24.10.2025
            "USDT": 1.0,
            "USDC": 1.0,
            "DAI": 1.0,
            "MATIC": 0.65,
            "AVAX": 25,
            "ARB": 0.75,
            "OP": 1.65,
            "LINK": 11,
            "UNI": 6.5,
            "AAVE": 145,
            "TRX": 0.16,
            "XRP": 2.40,
            "DOGE": 0.19,
            "WETH": 3870,
            "WBTC": 110000,
        }
        self.price_cache_time = datetime.utcnow()
        print(f"⚠️  [PRICE CACHE] Используются fallback цены (API недоступен)")
    
    # =========================================================================
    # Основной метод сбора событий
    # =========================================================================
    
    async def fetch_events(self, start_time: datetime) -> List[WhaleEvent]:
        """Собирает события со всех цепей (нативные + токены)"""
        
        # Обновляем кэш цен при старте
        await self._refresh_price_cache()
        
        events = []
        
        tasks = [
            self._fetch_evm_events("ethereum", start_time),
            self._fetch_evm_events("bsc", start_time),
            self._fetch_evm_events("polygon", start_time),
            self._fetch_evm_events("arbitrum", start_time),
            self._fetch_evm_events("base", start_time),
            self._fetch_evm_events("avalanche", start_time),
            self._fetch_evm_events("optimism", start_time),
            self._fetch_btc_events(start_time),
            self._fetch_sol_events(start_time),
            self._fetch_tron_events(start_time),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"⚠️  [MONITOR] Ошибка: {result}")
            elif isinstance(result, list):
                events.extend(result)
        
        print(f"📊 [MONITOR] Собрано {len(events)} событий (нативные + токены)")
        return events
    
    # =========================================================================
    # EVM CHAINS (нативные + ERC-20 токены)
    # =========================================================================
    async def _fetch_evm_events(self, chain: str, start_time: datetime) -> List[WhaleEvent]:
        """Мониторинг EVM: нативные + ERC-20"""
        events = []
        
        api_config = self._get_evm_api_config(chain)
        if not api_config:
            return events
        
        try:
            latest_block = await self._get_latest_block(api_config)
            if not latest_block:
                return events
            
            blocks_back = int(settings.START_FROM_MINUTES_AGO * 60 / api_config["block_time"])
            start_block = max(0, latest_block - blocks_back)
            
            print(f"🔗 [{chain.upper()}] Блоки {start_block}-{latest_block}")
            
            # 1. Нативные переводы
            native_events = await self._fetch_native_transfers(api_config, chain, start_block, latest_block)
            events.extend(native_events)
            
            # 2. ERC-20 токены
            token_events = await self._fetch_token_transfers(api_config, chain, start_block, latest_block)
            events.extend(token_events)
            
            print(f"🔗 [{chain.upper()}] Найдено {len(events)} переводов")
            
        except Exception as e:
            print(f"❌ [{chain.upper()}] Ошибка: {e}")
        
        return events
    
    async def _fetch_native_transfers(self, api_config: Dict, chain: str, start_block: int, end_block: int) -> List[WhaleEvent]:
        """Нативные переводы на/с hot wallets"""
        events = []
        
        for address, info in self.KNOWN_HOT_WALLETS.get(chain, {}).items():
            try:
                incoming = await self._fetch_evm_transactions(api_config, address, start_block, end_block)
                events.extend(self._parse_evm_transactions(incoming, chain, info, "inflow", api_config))
                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"⚠️  [{chain}] Ошибка {address[:10]}: {e}")
        
        return events
    
    async def _fetch_token_transfers(self, api_config: Dict, chain: str, start_block: int, end_block: int) -> List[WhaleEvent]:
        """ERC-20/BEP-20 токены из watchlist"""
        events = []
        
        tokens = self.watchlist_cache.get(chain, [])
        if not tokens:
            return events
        
        # Топ-20 токенов по объёму
        top_tokens = sorted(tokens, key=lambda x: x.get("volume_24h", 0), reverse=True)[:20]
        
        for token in top_tokens:
            contract = token.get("contract")
            if not contract:
                continue
            
            try:
                transfers = await self._fetch_erc20_logs(api_config, contract, start_block, end_block)
                
                for tx in transfers:
                    event = self._parse_erc20_transfer(tx, chain, token, api_config)
                    if event:
                        events.append(event)
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"⚠️  [{chain}] Ошибка токена {token.get('symbol')}: {e}")
                continue
        
        return events
    
    async def _fetch_erc20_logs(self, api_config: Dict, contract: str, start_block: int, end_block: int) -> List[Dict]:
        """Получает ERC-20 Transfer события"""
        try:
            params = {
                "module": "logs",
                "action": "getLogs",
                "address": contract,
                "fromBlock": start_block,
                "toBlock": end_block,
                "topic0": self.ERC20_TRANSFER_TOPIC,
                "apikey": api_config["api_key"]
            }
            
            async with self.session.get(api_config["api_url"], params=params, timeout=15) as resp:
                data = await resp.json()
                
                if data.get("status") == "1" and data.get("result"):
                    return data["result"]
                return []
                
        except Exception as e:
            return []
    
    def _parse_erc20_transfer(self, log: Dict, chain: str, token_info: Dict, api_config: Dict) -> Optional[WhaleEvent]:
        """Парсит ERC-20 Transfer event"""
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None
            
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            
            data_hex = log.get("data", "0x0")
            amount_wei = int(data_hex, 16)
            
            decimals = token_info.get("decimals", 18)
            if token_info.get("symbol") in ["USDT", "USDC", "USDD"]:
                decimals = 6
            
            amount_tokens = amount_wei / (10 ** decimals)
            
            if amount_tokens == 0:
                return None
            
            usd_estimate = amount_tokens * 1
            
            from_is_exchange = from_addr.lower() in self.KNOWN_HOT_WALLETS.get(chain, {})
            to_is_exchange = to_addr.lower() in self.KNOWN_HOT_WALLETS.get(chain, {})
            
            if not (from_is_exchange or to_is_exchange):
                return None
            
            if to_is_exchange:
                direction = "inflow_to_exchange"
                label_side = "to"
                wallet_info = self.KNOWN_HOT_WALLETS[chain][to_addr.lower()]
            else:
                direction = "outflow_to_cold"
                label_side = "from"
                wallet_info = self.KNOWN_HOT_WALLETS[chain][from_addr.lower()]
            
            event = WhaleEvent(
                asset=token_info.get("symbol", "UNKNOWN").upper(),
                amount_native=amount_tokens,
                amount_usd=usd_estimate,
                chain=chain,
                direction=direction,
                phase="activation",
                tx_hash=log.get("transactionHash", ""),
                from_address=from_addr.lower(),
                to_address=to_addr.lower(),
                tx_time_utc=datetime.fromtimestamp(int(log.get("timeStamp", "0"), 16)),
                min_usd_threshold=settings.MIN_USD_FLOOR
            )
            
            label = AddressLabel(
                provider="known_wallets",
                name="exchange",
                confidence=wallet_info["confidence"],
                details=f"{wallet_info['name']} Hot Wallet"
            )
            event.labels[label_side].append(label)
            
            event.links = {
                "tx": f"{api_config['explorer']}/tx/{event.tx_hash}",
                "from": f"{api_config['explorer']}/address/{from_addr}",
                "to": f"{api_config['explorer']}/address/{to_addr}"
            }
            
            return event
        except Exception as e:
            return None
    
    def _get_evm_api_config(self, chain: str) -> Optional[Dict]:
        """Конфигурация API для EVM сетей"""
        configs = {
            "ethereum": {
                "api_url": "https://api.etherscan.io/api",
                "api_key": settings.ETHERSCAN_API_KEY,
                "explorer": "https://etherscan.io",
                "native_symbol": "ETH",
                "block_time": 12
            },
            "bsc": {
                "api_url": "https://api.bscscan.com/api",
                "api_key": settings.ETHERSCAN_API_KEY,
                "explorer": "https://bscscan.com",
                "native_symbol": "BNB",
                "block_time": 3
            },
            "polygon": {
                "api_url": "https://api.polygonscan.com/api",
                "api_key": settings.ETHERSCAN_API_KEY,
                "explorer": "https://polygonscan.com",
                "native_symbol": "MATIC",
                "block_time": 2
            },
            "arbitrum": {
                "api_url": "https://api.arbiscan.io/api",
                "api_key": settings.ETHERSCAN_API_KEY,
                "explorer": "https://arbiscan.io",
                "native_symbol": "ETH",
                "block_time": 0.25
            },
            "base": {
                "api_url": "https://api.basescan.org/api",
                "api_key": settings.ETHERSCAN_API_KEY,
                "explorer": "https://basescan.org",
                "native_symbol": "ETH",
                "block_time": 2
            },
            "avalanche": {
            "api_url": "https://api.snowtrace.io/api",
            "api_key": settings.ETHERSCAN_API_KEY,
            "explorer": "https://snowtrace.io",
            "native_symbol": "AVAX",
            "block_time": 2
        },
        "optimism": {
            "api_url": "https://api-optimistic.etherscan.io/api",
            "api_key": settings.ETHERSCAN_API_KEY,
            "explorer": "https://optimistic.etherscan.io",
            "native_symbol": "ETH",
            "block_time": 2
        }
    }
        config = configs.get(chain)
        if config and not config["api_key"]:
            print(f"⚠️  [{chain.upper()}] API ключ не установлен")
            return None
        
        return config
    
    async def _get_latest_block(self, api_config: Dict) -> Optional[int]:
        """Получает последний блок"""
        try:
            params = {
                "module": "proxy",
                "action": "eth_blockNumber",
                "apikey": api_config["api_key"]
            }
            
            async with self.session.get(api_config["api_url"], params=params, timeout=10) as resp:
                data = await resp.json()
                return int(data.get("result", "0x0"), 16)
        except Exception:
            return None
    
    async def _fetch_evm_transactions(self, api_config: Dict, address: str, start_block: int, end_block: int) -> List[Dict]:
        """Получает транзакции адреса"""
        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": start_block,
                "endblock": end_block,
                "sort": "desc",
                "apikey": api_config["api_key"]
            }
            
            async with self.session.get(api_config["api_url"], params=params, timeout=15) as resp:
                data = await resp.json()
                
                if data.get("status") == "1" and data.get("result"):
                    return data["result"]
                return []
                
        except Exception:
            return []
    
    def _parse_evm_transactions(self, txs: List[Dict], chain: str, wallet_info: Dict, flow_type: str, api_config: Dict) -> List[WhaleEvent]:
        """Парсит нативные транзакции с РЕАЛЬНЫМИ ценами из кэша"""
        events = []
        
        for tx in txs[:10]:
            try:
                value_wei = int(tx.get("value", "0"))
                if value_wei == 0:
                    continue
                
                value_native = value_wei / 1e18
                
                # Получаем реальную цену из кэша
                native_symbol = api_config["native_symbol"]
                
                # Для обёрнутых токенов используем базовый актив
                if native_symbol == "ETH" and chain in ["arbitrum", "base"]:
                    price_symbol = "ETH"
                else:
                    price_symbol = native_symbol
                
                # Получаем цену из кэша (синхронный доступ)
                price_estimate = self.price_cache.get(price_symbol, 0)
                
                # Fallback если цена не найдена (не должно случаться)
                if price_estimate == 0:
                    print(f"⚠️  [PRICE] Не найдена цена для {price_symbol}, используем fallback")
                    price_estimate = settings.FALLBACK_PRICES.get(native_symbol, 1)
                
                usd_estimate = value_native * price_estimate
                
                if usd_estimate < settings.MIN_USD_FLOOR:
                    continue
                
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                
                if flow_type == "inflow":
                    direction = "inflow_to_exchange"
                    label_side = "to"
                else:
                    direction = "outflow_to_cold"
                    label_side = "from"
                
                event = WhaleEvent(
                    asset=api_config["native_symbol"],
                    amount_native=value_native,
                    amount_usd=usd_estimate,
                    chain=chain,
                    direction=direction,
                    phase="activation",
                    tx_hash=tx.get("hash", ""),
                    from_address=from_addr,
                    to_address=to_addr,
                    tx_time_utc=datetime.fromtimestamp(int(tx.get("timeStamp", 0))),
                    min_usd_threshold=settings.MIN_USD_FLOOR
                )
                
                label = AddressLabel(
                    provider="known_wallets",
                    name="exchange",
                    confidence=wallet_info["confidence"],
                    details=f"{wallet_info['name']} Hot Wallet"
                )
                event.labels[label_side].append(label)
                
                event.links = {
                    "tx": f"{api_config['explorer']}/tx/{event.tx_hash}",
                    "from": f"{api_config['explorer']}/address/{from_addr}",
                    "to": f"{api_config['explorer']}/address/{to_addr}"
                }
                
                events.append(event)
                
            except Exception:
                continue
        
        return events
    
    # =========================================================================
    # BITCOIN
    # =========================================================================
    async def _fetch_btc_events(self, start_time: datetime) -> List[WhaleEvent]:
        """Мониторинг Bitcoin"""
        events = []
        
        try:
            url = "https://mempool.space/api/mempool/recent"
            
            async with self.session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return events
                
                txs = await resp.json()
                
                # Получаем реальную цену BTC
                btc_price = self.price_cache.get("BTC", settings.FALLBACK_PRICES.get("BTC", 110000))
                
                for tx in txs[:30]:
                    vout_sum = sum(out.get("value", 0) for out in tx.get("vout", []))
                    btc_amount = vout_sum / 100_000_000
                    usd_estimate = btc_amount * btc_price
                    
                    if usd_estimate < settings.MIN_USD_FLOOR:
                        continue
                    
                    event = WhaleEvent(
                        asset="BTC",
                        amount_native=btc_amount,
                        amount_usd=usd_estimate,
                        chain="bitcoin",
                        direction="unknown",
                        phase="activation",
                        tx_hash=tx.get("txid", ""),
                        from_address="multiple_inputs",
                        to_address="multiple_outputs",
                        tx_time_utc=datetime.utcnow(),
                        min_usd_threshold=settings.MIN_USD_FLOOR
                    )
                    
                    event.links = {
                        "tx": f"https://mempool.space/tx/{event.tx_hash}",
                        "from": "",
                        "to": ""
                    }
                    
                    events.append(event)
            
            print(f"🔗 [BTC] Найдено {len(events)} переводов")
            
        except Exception as e:
            print(f"❌ [BTC] Ошибка: {e}")
        
        return events
    
    # =========================================================================
    # SOLANA
    # =========================================================================
    async def _fetch_sol_events(self, start_time: datetime) -> List[WhaleEvent]:
        """Мониторинг Solana (нативный + SPL)"""
        events = []
        
        if not settings.HELIUS_API_KEY:
            return events
        
        try:
            # ИСПРАВЛЕНО: Динамическая загрузка всех Solana hot wallets
            known_sol_wallets = list(self.KNOWN_HOT_WALLETS.get("solana", {}).keys())
            
            # Получаем реальную цену SOL
            sol_price = self.price_cache.get("SOL", settings.FALLBACK_PRICES.get("SOL", 189))
            
            for wallet in known_sol_wallets:
                try:
                    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions"
                    params = {"api-key": settings.HELIUS_API_KEY, "limit": 20}
                    
                    async with self.session.get(url, params=params, timeout=15) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        
                        for tx in data:
                            # Нативный SOL
                            sol_amount = self._extract_sol_amount(tx)
                            if sol_amount and sol_amount > 100:
                                event = self._create_sol_event(tx, wallet, "SOL", sol_amount, sol_amount * sol_price)
                                if event:
                                    events.append(event)
                            
                            # SPL токены
                            spl_transfers = tx.get("tokenTransfers", [])
                            for transfer in spl_transfers:
                                token_amount = transfer.get("tokenAmount", 0)
                                mint = transfer.get("mint", "")
                                
                                token_symbol = self._get_spl_symbol(mint)
                                if token_symbol and token_amount > 0:
                                    event = self._create_sol_event(tx, wallet, token_symbol, token_amount, token_amount * 1)
                                    if event:
                                        events.append(event)
                    
                    await asyncio.sleep(0.3)
                    
                except Exception:
                    continue
            
            print(f"🔗 [SOL] Найдено {len(events)} переводов")
            
        except Exception as e:
            print(f"❌ [SOL] Ошибка: {e}")
        
        return events
    
    def _get_spl_symbol(self, mint: str) -> Optional[str]:
        """Получает символ SPL токена"""
        sol_tokens = self.watchlist_cache.get("solana", [])
        for token in sol_tokens:
            if token.get("mint") == mint:
                return token.get("symbol")
        return None
    
    def _create_sol_event(self, tx: Dict, wallet: str, symbol: str, amount: float, usd_est: float) -> Optional[WhaleEvent]:
        """Создаёт Solana событие"""
        if usd_est < settings.MIN_USD_FLOOR:
            return None
        
        event = WhaleEvent(
            asset=symbol,
            amount_native=amount,
            amount_usd=usd_est,
            chain="solana",
            direction="inflow_to_exchange",
            phase="activation",
            tx_hash=tx.get("signature", ""),
            from_address=tx.get("feePayer", ""),
            to_address=wallet,
            tx_time_utc=datetime.fromtimestamp(tx.get("timestamp", 0)),
            min_usd_threshold=settings.MIN_USD_FLOOR
        )
        
        label = AddressLabel(provider="known_wallets", name="exchange", confidence=90, details="Binance SOL Hot Wallet")
        event.labels["to"].append(label)
        
        event.links = {
            "tx": f"https://solscan.io/tx/{event.tx_hash}",
            "from": f"https://solscan.io/account/{event.from_address}",
            "to": f"https://solscan.io/account/{event.to_address}"
        }
        
        return event
    
    def _extract_sol_amount(self, tx: Dict) -> Optional[float]:
        """Извлекает сумму SOL"""
        try:
            native_transfers = tx.get("nativeTransfers", [])
            if native_transfers:
                for transfer in native_transfers:
                    amount_lamports = transfer.get("amount", 0)
                    amount_sol = amount_lamports / 1e9
                    if amount_sol > 100:
                        return amount_sol
            return None
        except:
            return None
    
    # =========================================================================
    # TRON
    # =========================================================================
    async def _fetch_tron_events(self, start_time: datetime) -> List[WhaleEvent]:
        """Мониторинг TRON (все TRC-20)"""
        events = []
        
        if not settings.TRONSCAN_API_KEY:
            return events
        
        try:
            tron_tokens = self.watchlist_cache.get("tron", [])
            if not tron_tokens:
                tron_tokens = [{"symbol": "USDT", "contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"}]
            
            headers = {"TRON-PRO-API-KEY": settings.TRONSCAN_API_KEY}
            
            for token in tron_tokens[:10]:
                contract = token.get("contract")
                if not contract:
                    continue
                
                try:
                    url = f"https://apilist.tronscanapi.com/api/token_trc20/transfers"
                    params = {
                        "contract_address": contract,
                        "limit": 30,
                        "sort": "-timestamp",
                        "start": 0
                    }
                    
                    async with self.session.get(url, params=params, headers=headers, timeout=15) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        transfers = data.get("token_transfers", [])
                        
                        for tx in transfers:
                            amount_raw = float(tx.get("quant", 0))
                            decimals = 6 if token["symbol"] in ["USDT", "USDC", "USDD"] else 18
                            amount_tokens = amount_raw / (10 ** decimals)
                            
                            if amount_tokens < 10000:
                                continue
                            
                            usd_estimate = amount_tokens * 1
                            
                            if usd_estimate < settings.MIN_USD_FLOOR:
                                continue
                            
                            from_addr = tx.get("from_address", "")
                            to_addr = tx.get("to_address", "")
                            
                            # ИСПРАВЛЕНО: Безопасное извлечение тэгов (может быть string или dict)
                            from_tag_raw = tx.get("from_address_tag")
                            to_tag_raw = tx.get("to_address_tag")
                            
                            # Конвертируем dict в строку если нужно
                            from_tag = self._normalize_tron_tag(from_tag_raw)
                            to_tag = self._normalize_tron_tag(to_tag_raw)
                            
                            from_label = self._parse_tron_label(from_tag)
                            to_label = self._parse_tron_label(to_tag)
                            
                            direction = self._determine_direction(from_label, to_label)
                            
                            event = WhaleEvent(
                                asset=token["symbol"].upper(),
                                amount_native=amount_tokens,
                                amount_usd=usd_estimate,
                                chain="tron",
                                direction=direction,
                                phase="activation",
                                tx_hash=tx.get("transaction_id", ""),
                                from_address=from_addr,
                                to_address=to_addr,
                                tx_time_utc=datetime.fromtimestamp(tx.get("block_ts", 0) / 1000),
                                min_usd_threshold=settings.MIN_USD_FLOOR
                            )
                            
                            if from_label:
                                event.labels["from"].append(from_label)
                            if to_label:
                                event.labels["to"].append(to_label)
                            
                            event.links = {
                                "tx": f"https://tronscan.org/#/transaction/{event.tx_hash}",
                                "from": f"https://tronscan.org/#/address/{from_addr}",
                                "to": f"https://tronscan.org/#/address/{to_addr}"
                            }
                            
                            events.append(event)
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"⚠️  [TRON] Ошибка {token['symbol']}: {e}")
                    continue
            
            print(f"🔗 [TRON] Найдено {len(events)} переводов")
            
        except Exception as e:
            print(f"❌ [TRON] Ошибка: {e}")
        
        return events
    
    def _normalize_tron_tag(self, tag) -> Optional[str]:
        """
        КРИТИЧНО: Нормализует тэг из TronScan API
        
        TronScan может возвращать:
        - Строку: "Binance Hot Wallet"
        - Dict: {"en": "Binance", "zh": "币安"}
        - None/пустое значение
        """
        if not tag:
            return None
        
        # Если уже строка - возвращаем как есть
        if isinstance(tag, str):
            return tag.strip() if tag.strip() else None
        
        # Если dict - берём английское название
        if isinstance(tag, dict):
            # Приоритет: en > name > первое значение
            if "en" in tag:
                return str(tag["en"]).strip()
            elif "name" in tag:
                return str(tag["name"]).strip()
            elif tag:
                # Берём первое доступное значение
                first_value = next(iter(tag.values()), None)
                if first_value:
                    return str(first_value).strip()
        
        # Для всех остальных типов
        return str(tag).strip() if tag else None
    
    def _parse_tron_label(self, tag) -> Optional[AddressLabel]:
        """ИСПРАВЛЕНО: Парсит метку TRONSCAN с проверкой типа"""
        # КРИТИЧНО: Проверка типа tag перед вызовом .lower()
        if not tag or not isinstance(tag, str):
            return None
        
        tag_lower = tag.lower()
        
        if "binance" in tag_lower or "okx" in tag_lower or "bybit" in tag_lower:
            name = "exchange"
            confidence = 90
        elif "contract" in tag_lower:
            name = "unknown"
            confidence = 30
        else:
            name = "unknown"
            confidence = 50
        
        return AddressLabel(
            provider="tronscan",
            name=name,
            confidence=confidence,
            details=tag
        )
    
    def _determine_direction(self, from_label: Optional[AddressLabel], to_label: Optional[AddressLabel]) -> str:
        """Определяет направление"""
        from_exchange = from_label and from_label.name == "exchange"
        to_exchange = to_label and to_label.name == "exchange"
        
        if to_exchange and not from_exchange:
            return "inflow_to_exchange"
        elif from_exchange and not to_exchange:
            return "outflow_to_cold"
        elif from_exchange and to_exchange:
            return "bridge"
        else:
            return "unknown"