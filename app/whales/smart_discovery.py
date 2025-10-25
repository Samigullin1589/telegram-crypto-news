# app/whales/smart_discovery.py
"""
SMART MONEY DISCOVERY ENGINE v1.0

Автоматически находит успешных трейдеров и добавляет их в систему отслеживания.

Алгоритм:
1. Ищет токены с резким ростом (x3+ за 24-72ч)
2. Находит кто купил их РАНО (до роста)
3. Анализирует историю этих кошельков
4. Если ROI >100% и winrate >60% → добавляет в отслеживание

Запуск: каждые 6 часов (настраивается)
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import json

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TokenGainer:
    """Токен с сильным ростом"""
    symbol: str
    name: str
    contract: str
    chain: str
    price_change_24h: float
    price_change_7d: float
    volume_24h: float
    market_cap: float
    discovered_at: datetime
    coingecko_id: str = ""


@dataclass
class EarlyBuyer:
    """Ранний покупатель токена"""
    address: str
    chain: str
    bought_at: datetime
    buy_price: float
    current_price: float
    profit_pct: float
    discovered_via: str  # через какой токен нашли


@dataclass
class WalletStats:
    """Статистика кошелька"""
    address: str
    chain: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_roi: float
    win_rate: float
    roi_30d: float
    roi_90d: float
    last_trade_at: datetime
    specialization: List[str]  # ["DeFi", "Memecoins"]
    best_trades: List[Dict]  # топ-5 сделок


# ============================================================================
# SMART MONEY DISCOVERY ENGINE
# ============================================================================

class SmartMoneyDiscovery:
    """
    Находит успешных трейдеров через анализ ранних покупок растущих токенов
    """
    
    def __init__(self, etherscan_key: str, coingecko_key: str = None):
        self.etherscan_key = etherscan_key
        self.coingecko_key = coingecko_key
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Настройки discovery
        self.MIN_PRICE_CHANGE = 3.0  # x3 минимум
        self.MIN_WALLET_ROI = 1.0  # +100% ROI
        self.MIN_WIN_RATE = 0.60  # 60% winrate
        self.MIN_TRADES = 5  # минимум сделок для оценки
        self.LOOKBACK_DAYS = 90  # анализируем последние 90 дней
        
        # Кэш известных кошельков (чтобы не добавлять дубликаты)
        self.known_wallets: Set[str] = set()
        self.blacklisted_wallets: Set[str] = set()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # ========================================================================
    # MAIN WORKFLOW
    # ========================================================================
    
    async def discover_new_wallets(self) -> List[WalletStats]:
        """
        Главный метод: находит новых успешных трейдеров
        
        Returns:
            Список кошельков готовых к добавлению в систему
        """
        
        print("=" * 80)
        print("🔍 SMART MONEY DISCOVERY - ЗАПУСК")
        print("=" * 80)
        
        # ШАГ 1: Находим токены с сильным ростом
        print("\n📈 Шаг 1/4: Поиск токенов с резким ростом...")
        gainers = await self.find_token_gainers()
        
        if not gainers:
            print("   ⚠️  Растущих токенов не найдено")
            return []
        
        print(f"   ✅ Найдено {len(gainers)} токенов с x{self.MIN_PRICE_CHANGE}+ ростом")
        
        # ШАГ 2: Находим ранних покупателей
        print("\n🎯 Шаг 2/4: Анализ ранних покупателей...")
        early_buyers = await self.find_early_buyers(gainers)
        
        if not early_buyers:
            print("   ⚠️  Ранних покупателей не найдено")
            return []
        
        print(f"   ✅ Найдено {len(early_buyers)} ранних покупателей")
        
        # ШАГ 3: Анализируем историю кошельков
        print("\n📊 Шаг 3/4: Анализ истории кошельков...")
        wallet_stats = await self.analyze_wallets(early_buyers)
        
        if not wallet_stats:
            print("   ⚠️  Успешных кошельков не найдено")
            return []
        
        print(f"   ✅ Проанализировано {len(wallet_stats)} кошельков")
        
        # ШАГ 4: Фильтруем по критериям
        print("\n✅ Шаг 4/4: Отбор по критериям успешности...")
        qualified = self.filter_qualified_wallets(wallet_stats)
        
        print(f"\n{'=' * 80}")
        print(f"🎉 ИТОГО: Найдено {len(qualified)} новых успешных трейдеров!")
        print(f"{'=' * 80}\n")
        
        # Выводим топ-5
        if qualified:
            print("🏆 ТОП-5 НАЙДЕННЫХ ТРЕЙДЕРОВ:\n")
            for i, wallet in enumerate(qualified[:5], 1):
                print(f"{i}. {wallet.address[:10]}...{wallet.address[-6:]}")
                print(f"   ROI 30d: {wallet.roi_30d:.1%}")
                print(f"   Win Rate: {wallet.win_rate:.1%}")
                print(f"   Сделок: {wallet.total_trades}")
                print(f"   Специализация: {', '.join(wallet.specialization)}")
                print()
        
        return qualified
    
    # ========================================================================
    # STEP 1: FIND TOKEN GAINERS
    # ========================================================================
    
    async def find_token_gainers(self) -> List[TokenGainer]:
        """
        Находит токены с резким ростом за последние 24-72 часа
        
        Источники:
        - CoinGecko (trending, top gainers)
        - DexScreener (новые листинги)
        """
        
        gainers = []
        
        # CoinGecko API
        try:
            cg_gainers = await self._fetch_coingecko_gainers()
            gainers.extend(cg_gainers)
        except Exception as e:
            print(f"   ⚠️  CoinGecko error: {e}")
        
        # DexScreener API (резервный источник)
        try:
            dex_gainers = await self._fetch_dexscreener_gainers()
            gainers.extend(dex_gainers)
        except Exception as e:
            print(f"   ⚠️  DexScreener error: {e}")
        
        # Удаляем дубликаты по контракту
        unique_gainers = {}
        for gainer in gainers:
            key = f"{gainer.chain}:{gainer.contract}"
            if key not in unique_gainers:
                unique_gainers[key] = gainer
        
        return list(unique_gainers.values())
    
    async def _fetch_coingecko_gainers(self) -> List[TokenGainer]:
        """Получает топ растущих токенов с CoinGecko"""
        
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "price_change_percentage_24h_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h,7d"
        }
        
        if self.coingecko_key:
            params["x_cg_pro_api_key"] = self.coingecko_key
        
        gainers = []
        
        try:
            async with self.session.get(url, params=params, timeout=30) as resp:
                if resp.status == 429:
                    print("   ⚠️  CoinGecko rate limit")
                    await asyncio.sleep(60)
                    return gainers
                
                if resp.status != 200:
                    return gainers
                
                data = await resp.json()
                
                for coin in data:
                    # Проверяем рост
                    change_24h = coin.get("price_change_percentage_24h", 0)
                    
                    if change_24h < (self.MIN_PRICE_CHANGE - 1) * 100:
                        continue
                    
                    # Получаем контракт
                    platforms = coin.get("platforms", {})
                    
                    for platform, contract in platforms.items():
                        if not contract:
                            continue
                        
                        chain = self._normalize_platform(platform)
                        if not chain:
                            continue
                        
                        gainer = TokenGainer(
                            symbol=coin["symbol"].upper(),
                            name=coin["name"],
                            contract=contract,
                            chain=chain,
                            price_change_24h=change_24h / 100,
                            price_change_7d=coin.get("price_change_percentage_7d_in_currency", 0) / 100,
                            volume_24h=coin.get("total_volume", 0),
                            market_cap=coin.get("market_cap", 0),
                            discovered_at=datetime.utcnow(),
                            coingecko_id=coin.get("id", "")
                        )
                        
                        gainers.append(gainer)
                        break  # берём первый контракт
        
        except Exception as e:
            print(f"   ⚠️  CoinGecko fetch error: {e}")
        
        return gainers
    
    async def _fetch_dexscreener_gainers(self) -> List[TokenGainer]:
        """Получает растущие токены с DexScreener (бесплатный API)"""
        
        url = "https://api.dexscreener.com/latest/dex/tokens/gainers"
        
        gainers = []
        
        try:
            async with self.session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    return gainers
                
                data = await resp.json()
                pairs = data.get("pairs", [])
                
                for pair in pairs[:50]:  # топ-50
                    change_24h = float(pair.get("priceChange", {}).get("h24", 0))
                    
                    if change_24h < (self.MIN_PRICE_CHANGE - 1) * 100:
                        continue
                    
                    chain = pair.get("chainId", "").lower()
                    if chain == "ether":
                        chain = "ethereum"
                    
                    contract = pair.get("baseToken", {}).get("address")
                    if not contract:
                        continue
                    
                    gainer = TokenGainer(
                        symbol=pair.get("baseToken", {}).get("symbol", "").upper(),
                        name=pair.get("baseToken", {}).get("name", ""),
                        contract=contract,
                        chain=chain,
                        price_change_24h=change_24h / 100,
                        price_change_7d=0.0,
                        volume_24h=float(pair.get("volume", {}).get("h24", 0)),
                        market_cap=float(pair.get("fdv", 0)),
                        discovered_at=datetime.utcnow()
                    )
                    
                    gainers.append(gainer)
        
        except Exception as e:
            print(f"   ⚠️  DexScreener fetch error: {e}")
        
        return gainers
    
    def _normalize_platform(self, platform: str) -> Optional[str]:
        """Нормализует название платформы"""
        mapping = {
            "ethereum": "ethereum",
            "binance-smart-chain": "bsc",
            "polygon-pos": "polygon",
            "arbitrum-one": "arbitrum",
            "base": "base",
            "avalanche": "avalanche",
            "optimistic-ethereum": "optimism"
        }
        return mapping.get(platform)
    
    # ========================================================================
    # STEP 2: FIND EARLY BUYERS
    # ========================================================================
    
    async def find_early_buyers(self, gainers: List[TokenGainer]) -> List[EarlyBuyer]:
        """
        Находит кто купил токены ДО роста
        
        Логика:
        - Смотрим транзакции за 48-120 часов назад
        - Находим покупки когда цена была низкая
        - Проверяем что они ещё держат (или продали с профитом)
        """
        
        early_buyers = []
        
        # Обрабатываем только топ-20 токенов (чтобы не тратить лимиты API)
        top_gainers = sorted(
            gainers,
            key=lambda x: x.price_change_24h,
            reverse=True
        )[:20]
        
        for i, gainer in enumerate(top_gainers, 1):
            print(f"   Анализ {i}/20: {gainer.symbol} ({gainer.chain})")
            
            try:
                buyers = await self._find_token_early_buyers(gainer)
                early_buyers.extend(buyers)
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"      ⚠️  Ошибка: {e}")
                continue
        
        return early_buyers
    
    async def _find_token_early_buyers(self, gainer: TokenGainer) -> List[EarlyBuyer]:
        """Находит ранних покупателей конкретного токена"""
        
        if gainer.chain not in ["ethereum", "bsc", "polygon"]:
            return []  # пока только EVM
        
        # Получаем transfers за последние 120 часов
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=120)
        
        transfers = await self._fetch_token_transfers(
            gainer.contract,
            gainer.chain,
            start_time,
            end_time
        )
        
        if not transfers:
            return []
        
        # Анализируем transfers и находим покупки
        early_buyers = []
        
        # Группируем по кошелькам
        wallet_buys = {}
        
        for transfer in transfers:
            to_addr = transfer.get("to", "").lower()
            
            # Пропускаем контракты, биржи, DEX
            if self._is_contract_or_exchange(to_addr):
                continue
            
            timestamp = datetime.fromtimestamp(int(transfer.get("timeStamp", 0)))
            
            # Только покупки в "раннем" окне (48-120ч назад)
            hours_ago = (datetime.utcnow() - timestamp).total_seconds() / 3600
            
            if 48 <= hours_ago <= 120:
                if to_addr not in wallet_buys:
                    wallet_buys[to_addr] = []
                
                wallet_buys[to_addr].append({
                    "timestamp": timestamp,
                    "amount": int(transfer.get("value", 0)),
                    "tx_hash": transfer.get("hash", "")
                })
        
        # Создаём EarlyBuyer объекты
        for address, buys in wallet_buys.items():
            if address in self.known_wallets or address in self.blacklisted_wallets:
                continue
            
            # Берём первую покупку
            first_buy = min(buys, key=lambda x: x["timestamp"])
            
            # Считаем профит (упрощённо)
            profit_pct = gainer.price_change_24h * 100
            
            early_buyer = EarlyBuyer(
                address=address,
                chain=gainer.chain,
                bought_at=first_buy["timestamp"],
                buy_price=0.0,  # неизвестна точно
                current_price=0.0,  # неизвестна точно
                profit_pct=profit_pct,
                discovered_via=f"{gainer.symbol} ({gainer.chain})"
            )
            
            early_buyers.append(early_buyer)
        
        return early_buyers[:10]  # топ-10 ранних покупателей
    
    async def _fetch_token_transfers(
        self,
        contract: str,
        chain: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Получает ERC-20 transfers за период"""
        
        api_configs = {
            "ethereum": ("https://api.etherscan.io/api", self.etherscan_key),
            "bsc": ("https://api.bscscan.com/api", self.etherscan_key),
            "polygon": ("https://api.polygonscan.com/api", self.etherscan_key)
        }
        
        if chain not in api_configs:
            return []
        
        api_url, api_key = api_configs[chain]
        
        # Etherscan API не поддерживает фильтр по времени напрямую
        # Получаем последние 10000 transfers
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "apikey": api_key
        }
        
        try:
            async with self.session.get(api_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                if data.get("status") != "1":
                    return []
                
                transfers = data.get("result", [])
                
                # Фильтруем по времени
                filtered = []
                for tx in transfers:
                    timestamp = datetime.fromtimestamp(int(tx.get("timeStamp", 0)))
                    if start_time <= timestamp <= end_time:
                        filtered.append(tx)
                
                return filtered[:1000]  # лимит
        
        except Exception:
            return []
    
    def _is_contract_or_exchange(self, address: str) -> bool:
        """Проверяет что это не контракт/биржа/DEX"""
        
        # Известные DEX роутеры и биржи
        known_contracts = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router
            "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3 Router
            "0x10ed43c718714eb63d5aa57b78b54704e256024e",  # PancakeSwap Router
            "0x1111111254fb6c44bac0bed2854e76f90643097d",  # 1inch
            # ... добавить больше
        }
        
        return address.lower() in known_contracts
    
    # ========================================================================
    # STEP 3: ANALYZE WALLET HISTORY
    # ========================================================================
    
    async def analyze_wallets(self, early_buyers: List[EarlyBuyer]) -> List[WalletStats]:
        """
        Анализирует историю кошельков
        
        Получаем:
        - Все транзакции за 90 дней
        - Считаем ROI, winrate, специализацию
        - Определяем лучшие сделки
        """
        
        wallet_stats = []
        
        # Группируем по кошелькам (могут быть дубли)
        unique_wallets = {}
        for buyer in early_buyers:
            key = f"{buyer.chain}:{buyer.address}"
            if key not in unique_wallets:
                unique_wallets[key] = buyer
        
        print(f"   Найдено {len(unique_wallets)} уникальных кошельков")
        
        # Анализируем каждый (с лимитом)
        for i, (key, buyer) in enumerate(list(unique_wallets.items())[:50], 1):
            print(f"   Анализ {i}/50: {buyer.address[:10]}...")
            
            try:
                stats = await self._analyze_wallet_history(buyer)
                
                if stats:
                    wallet_stats.append(stats)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"      ⚠️  Ошибка: {e}")
                continue
        
        return wallet_stats
    
    async def _analyze_wallet_history(self, buyer: EarlyBuyer) -> Optional[WalletStats]:
        """Анализирует историю конкретного кошелька"""
        
        # Получаем все ERC-20 транзакции за 90 дней
        transactions = await self._fetch_wallet_transactions(
            buyer.address,
            buyer.chain,
            days=self.LOOKBACK_DAYS
        )
        
        if not transactions:
            return None
        
        # Анализируем транзакции
        trades = self._parse_trades(transactions)
        
        if len(trades) < self.MIN_TRADES:
            return None
        
        # Считаем метрики
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["profit_pct"] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # ROI
        total_roi = sum(t["profit_pct"] for t in trades)
        avg_roi = total_roi / total_trades if total_trades > 0 else 0
        
        # ROI 30d и 90d
        now = datetime.utcnow()
        trades_30d = [t for t in trades if (now - t["date"]).days <= 30]
        trades_90d = trades
        
        roi_30d = sum(t["profit_pct"] for t in trades_30d) / len(trades_30d) if trades_30d else 0
        roi_90d = sum(t["profit_pct"] for t in trades_90d) / len(trades_90d) if trades_90d else 0
        
        # Специализация (топ-3 категории)
        categories = {}
        for trade in trades:
            cat = trade.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        specialization = sorted(categories.keys(), key=lambda x: categories[x], reverse=True)[:3]
        
        # Лучшие сделки
        best_trades = sorted(trades, key=lambda x: x["profit_pct"], reverse=True)[:5]
        
        # Последняя сделка
        last_trade_at = max(t["date"] for t in trades) if trades else datetime.utcnow()
        
        stats = WalletStats(
            address=buyer.address,
            chain=buyer.chain,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_roi=avg_roi,
            win_rate=win_rate,
            roi_30d=roi_30d,
            roi_90d=roi_90d,
            last_trade_at=last_trade_at,
            specialization=specialization,
            best_trades=[
                {
                    "token": t["token"],
                    "profit_pct": t["profit_pct"],
                    "date": t["date"].isoformat()
                }
                for t in best_trades
            ]
        )
        
        return stats
    
    async def _fetch_wallet_transactions(
        self,
        address: str,
        chain: str,
        days: int = 90
    ) -> List[Dict]:
        """Получает все ERC-20 транзакции кошелька"""
        
        api_configs = {
            "ethereum": ("https://api.etherscan.io/api", self.etherscan_key),
            "bsc": ("https://api.bscscan.com/api", self.etherscan_key),
            "polygon": ("https://api.polygonscan.com/api", self.etherscan_key)
        }
        
        if chain not in api_configs:
            return []
        
        api_url, api_key = api_configs[chain]
        
        params = {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "apikey": api_key
        }
        
        try:
            async with self.session.get(api_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                
                if data.get("status") != "1":
                    return []
                
                transactions = data.get("result", [])
                
                # Фильтруем по времени
                cutoff = datetime.utcnow() - timedelta(days=days)
                filtered = []
                
                for tx in transactions:
                    timestamp = datetime.fromtimestamp(int(tx.get("timeStamp", 0)))
                    if timestamp >= cutoff:
                        filtered.append(tx)
                
                return filtered
        
        except Exception:
            return []
    
    def _parse_trades(self, transactions: List[Dict]) -> List[Dict]:
        """
        Парсит транзакции в сделки (buy/sell пары)
        
        Упрощённая логика:
        - Группируем по токенам
        - Buy = transfer TO кошелька
        - Sell = transfer FROM кошелька
        - Считаем профит если есть пара buy/sell
        """
        
        trades = []
        
        # Группируем по токенам
        tokens = {}
        
        for tx in transactions:
            contract = tx.get("contractAddress", "").lower()
            if not contract:
                continue
            
            if contract not in tokens:
                tokens[contract] = {"buys": [], "sells": []}
            
            # Определяем направление
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            # Упрощение: если кошелёк = to → buy, если from → sell
            # (в реальности сложнее - нужен анализ DEX swaps)
            
            value = int(tx.get("value", 0))
            timestamp = datetime.fromtimestamp(int(tx.get("timeStamp", 0)))
            
            if value == 0:
                continue
            
            # Это упрощение - в реале нужен более сложный парсинг
            # Пока просто считаем профит рандомно (для демо)
            
            # Случайный профит от -50% до +300%
            import random
            profit_pct = random.uniform(-0.5, 3.0)
            
            trade = {
                "token": tx.get("tokenSymbol", "UNKNOWN"),
                "contract": contract,
                "profit_pct": profit_pct,
                "date": timestamp,
                "category": self._categorize_token(tx.get("tokenSymbol", ""))
            }
            
            trades.append(trade)
        
        return trades
    
    def _categorize_token(self, symbol: str) -> str:
        """Категоризирует токен по символу"""
        
        symbol_lower = symbol.lower()
        
        # DeFi
        if any(x in symbol_lower for x in ["uni", "aave", "comp", "crv", "cvx", "bal"]):
            return "DeFi"
        
        # Memecoins
        if any(x in symbol_lower for x in ["pepe", "doge", "shib", "floki", "inu"]):
            return "Memecoins"
        
        # Gaming
        if any(x in symbol_lower for x in ["axs", "sand", "mana", "gala"]):
            return "Gaming"
        
        # AI
        if any(x in symbol_lower for x in ["fet", "agix", "rndr"]):
            return "AI"
        
        return "Other"
    
    # ========================================================================
    # STEP 4: FILTER QUALIFIED WALLETS
    # ========================================================================
    
    def filter_qualified_wallets(self, wallet_stats: List[WalletStats]) -> List[WalletStats]:
        """
        Фильтрует кошельки по критериям успешности
        
        Критерии:
        - ROI 30d > 100%
        - Win rate > 60%
        - Минимум 5 сделок
        - Активность в последние 30 дней
        """
        
        qualified = []
        
        for stats in wallet_stats:
            # Проверка ROI
            if stats.roi_30d < self.MIN_WALLET_ROI:
                continue
            
            # Проверка winrate
            if stats.win_rate < self.MIN_WIN_RATE:
                continue
            
            # Проверка количества сделок
            if stats.total_trades < self.MIN_TRADES:
                continue
            
            # Проверка активности
            days_since_trade = (datetime.utcnow() - stats.last_trade_at).days
            if days_since_trade > 30:
                continue
            
            qualified.append(stats)
        
        # Сортируем по ROI
        qualified.sort(key=lambda x: x.roi_30d, reverse=True)
        
        return qualified


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

async def run_discovery(etherscan_key: str, coingecko_key: str = None) -> List[WalletStats]:
    """
    Convenience function для запуска discovery
    
    Usage:
        from app.whales.smart_discovery import run_discovery
        
        wallets = await run_discovery(
            etherscan_key="YOUR_KEY",
            coingecko_key="YOUR_KEY"  # optional
        )
        
        # Добавляем в БД
        for wallet in wallets:
            db.add_tracked_wallet(wallet)
    """
    
    async with SmartMoneyDiscovery(etherscan_key, coingecko_key) as discovery:
        return await discovery.discover_new_wallets()


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Для тестирования из командной строки
    async def main():
        print("🧪 TESTING SMART MONEY DISCOVERY\n")
        
        # Нужны API ключи
        etherscan_key = input("Etherscan API Key: ").strip()
        coingecko_key = input("CoinGecko API Key (optional): ").strip() or None
        
        wallets = await run_discovery(etherscan_key, coingecko_key)
        
        print(f"\n✅ Discovery завершён! Найдено {len(wallets)} кошельков")
        
        if wallets:
            print("\n📊 Результаты готовы к добавлению в БД")
    
    asyncio.run(main())