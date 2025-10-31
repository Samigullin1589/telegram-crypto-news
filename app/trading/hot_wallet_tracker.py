"""
HOT WALLET TRACKER
Отслеживание движений на горячие кошельки бирж и крупных игроков
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import json


@dataclass
class WalletMovement:
    """Движение на hot wallet"""
    chain: str
    asset: str
    wallet_address: str
    wallet_label: str  # "Binance Hot Wallet", "Smart Money #123"
    
    # Транзакция
    tx_hash: str
    direction: str  # 'inflow', 'outflow'
    amount_native: float
    amount_usd: float
    
    # От кого / кому
    from_address: str
    to_address: str
    from_label: Optional[str] = None
    to_label: Optional[str] = None
    
    # Временные метки
    timestamp: datetime = None
    detected_at: datetime = None
    
    # Цена на момент движения
    price_at_move: Optional[float] = None
    
    # Анализ
    is_accumulation: bool = False  # Накопление перед ростом
    is_distribution: bool = False  # Распределение перед падением
    confidence: float = 0.0
    
    # Исторический контекст
    similar_moves_count: int = 0  # Сколько раз было похожее движение
    avg_price_change_1h: Optional[float] = None
    avg_price_change_4h: Optional[float] = None
    avg_price_change_24h: Optional[float] = None
    avg_price_change_7d: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'chain': self.chain,
            'asset': self.asset,
            'wallet': {
                'address': self.wallet_address,
                'label': self.wallet_label
            },
            'transaction': {
                'hash': self.tx_hash,
                'direction': self.direction,
                'amount_native': self.amount_native,
                'amount_usd': self.amount_usd
            },
            'addresses': {
                'from': self.from_address,
                'to': self.to_address,
                'from_label': self.from_label,
                'to_label': self.to_label
            },
            'timestamps': {
                'transaction': self.timestamp.isoformat() if self.timestamp else None,
                'detected': self.detected_at.isoformat() if self.detected_at else None
            },
            'price_context': {
                'at_move': self.price_at_move
            },
            'analysis': {
                'is_accumulation': self.is_accumulation,
                'is_distribution': self.is_distribution,
                'confidence': self.confidence,
                'historical': {
                    'similar_moves': self.similar_moves_count,
                    'avg_change_1h': self.avg_price_change_1h,
                    'avg_change_4h': self.avg_price_change_4h,
                    'avg_change_24h': self.avg_price_change_24h,
                    'avg_change_7d': self.avg_price_change_7d
                }
            }
        }


class PriceHistoryCache:
    """Кэш исторических цен"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 минут
    
    def get(self, asset: str, timestamp: datetime) -> Optional[float]:
        """Получить цену из кэша"""
        key = f"{asset}_{timestamp.strftime('%Y%m%d%H%M')}"
        
        if key in self.cache:
            cached = self.cache[key]
            if (datetime.utcnow() - cached['cached_at']).seconds < self.cache_ttl:
                return cached['price']
        
        return None
    
    def set(self, asset: str, timestamp: datetime, price: float):
        """Сохранить цену в кэш"""
        key = f"{asset}_{timestamp.strftime('%Y%m%d%H%M')}"
        self.cache[key] = {
            'price': price,
            'cached_at': datetime.utcnow()
        }


class HotWalletTracker:
    """
    Отслеживание движений на горячие кошельки
    
    Функции:
    - Мониторинг притоков/оттоков на биржевые hot wallets
    - Определение accumulation/distribution паттернов
    - Отслеживание smart money кошельков
    - Анализ исторических данных для предсказаний
    - Clustering связанных транзакций
    """
    
    def __init__(self, coingecko_key: Optional[str] = None):
        # База известных hot wallets
        self.hot_wallets = self._load_hot_wallets()
        
        # Smart money кошельки (будут добавляться через Discovery)
        self.smart_wallets: Dict[str, Dict] = {}
        
        # История движений для анализа паттернов
        self.movement_history = deque(maxlen=10000)
        
        # Кластеры связанных транзакций
        self.clusters: Dict[str, List[WalletMovement]] = defaultdict(list)
        
        # Кэш цен
        self.price_cache = PriceHistoryCache()
        self.coingecko_key = coingecko_key
        
        # Статистика
        self.stats = {
            'total_tracked': 0,
            'accumulation_signals': 0,
            'distribution_signals': 0,
            'accurate_predictions': 0,
            'total_predictions': 0
        }
        
        print("🔥 [HOT_WALLET] Tracker инициализирован")
        print(f"   Отслеживается {len(self.hot_wallets)} hot wallets")
    
    async def track_movement(
        self,
        movement: WalletMovement,
        session: aiohttp.ClientSession
    ) -> Optional[WalletMovement]:
        """
        Анализ движения на hot wallet
        
        Returns:
            Обогащенное движение с анализом или None если не значимо
        """
        
        try:
            # Проверяем является ли это hot wallet
            if not self._is_hot_wallet(movement.wallet_address):
                return None
            
            # Добавляем метку wallet
            movement.wallet_label = self._get_wallet_label(movement.wallet_address)
            
            # Получаем цену на момент движения
            movement.price_at_move = await self._get_price_at_time(
                movement.asset,
                movement.timestamp or movement.detected_at,
                session
            )
            
            # Определяем accumulation/distribution
            movement = await self._analyze_pattern(movement, session)
            
            # Ищем похожие движения в истории и анализируем результаты
            movement = await self._enrich_with_history(movement, session)
            
            # Кластеризация
            self._add_to_cluster(movement)
            
            # Сохраняем в историю
            self.movement_history.append(movement)
            self.stats['total_tracked'] += 1
            
            # Обновляем статистику
            if movement.is_accumulation:
                self.stats['accumulation_signals'] += 1
            elif movement.is_distribution:
                self.stats['distribution_signals'] += 1
            
            return movement
            
        except Exception as e:
            print(f"❌ [HOT_WALLET] Ошибка анализа: {e}")
            return None
    
    async def _get_price_at_time(
        self,
        asset: str,
        timestamp: datetime,
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """
        РЕАЛЬНОЕ получение цены актива в указанное время
        
        Использует:
        1. CoinGecko historical API
        2. Binance klines (если CoinGecko недоступен)
        """
        
        # Проверяем кэш
        cached_price = self.price_cache.get(asset, timestamp)
        if cached_price:
            return cached_price
        
        price = None
        
        # Попытка 1: CoinGecko
        try:
            price = await self._fetch_coingecko_historical_price(asset, timestamp, session)
        except Exception as e:
            print(f"⚠️ [PRICE] CoinGecko ошибка для {asset}: {e}")
        
        # Попытка 2: Binance (если CoinGecko не сработал)
        if not price:
            try:
                price = await self._fetch_binance_historical_price(asset, timestamp, session)
            except Exception as e:
                print(f"⚠️ [PRICE] Binance ошибка для {asset}: {e}")
        
        # Кэшируем
        if price:
            self.price_cache.set(asset, timestamp, price)
        
        return price
    
    async def _fetch_coingecko_historical_price(
        self,
        asset: str,
        timestamp: datetime,
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """Получение исторической цены с CoinGecko"""
        
        coin_id = self._get_coingecko_id(asset)
        if not coin_id:
            return None
        
        # Форматируем дату (dd-mm-yyyy)
        date_str = timestamp.strftime('%d-%m-%Y')
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
        params = {
            'date': date_str,
            'localization': 'false'
        }
        
        if self.coingecko_key:
            params['x_cg_pro_api_key'] = self.coingecko_key
        
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 429:
                await asyncio.sleep(60)
                return None
            
            if resp.status != 200:
                return None
            
            data = await resp.json()
            
            # Извлекаем цену
            price = data.get('market_data', {}).get('current_price', {}).get('usd')
            return float(price) if price else None
    
    async def _fetch_binance_historical_price(
        self,
        asset: str,
        timestamp: datetime,
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """Получение исторической цены с Binance"""
        
        symbol = f"{asset}USDT"
        
        # Конвертируем в миллисекунды
        start_time = int(timestamp.timestamp() * 1000)
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': '1h',
            'startTime': start_time,
            'limit': 1
        }
        
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                return None
            
            data = await resp.json()
            
            if not data:
                return None
            
            # Binance kline format: [open_time, open, high, low, close, ...]
            close_price = float(data[0][4])
            return close_price
    
    async def _enrich_with_history(
        self,
        movement: WalletMovement,
        session: aiohttp.ClientSession
    ) -> WalletMovement:
        """
        РЕАЛЬНОЕ обогащение историческими данными
        
        Ищет похожие движения в прошлом и рассчитывает
        реальное изменение цены после них используя исторические данные
        """
        
        # Ищем похожие движения
        similar_moves = self._find_similar_moves(movement)
        
        if not similar_moves:
            return movement
        
        movement.similar_moves_count = len(similar_moves)
        
        # Анализируем изменение цены после каждого похожего движения
        price_changes_1h = []
        price_changes_4h = []
        price_changes_24h = []
        price_changes_7d = []
        
        for similar in similar_moves:
            # Цена на момент движения
            price_at_move = similar.price_at_move
            if not price_at_move:
                continue
            
            move_time = similar.timestamp or similar.detected_at
            
            # Получаем цены после движения
            # 1 час спустя
            price_1h = await self._get_price_at_time(
                similar.asset,
                move_time + timedelta(hours=1),
                session
            )
            if price_1h:
                change_1h = ((price_1h - price_at_move) / price_at_move) * 100
                price_changes_1h.append(change_1h)
            
            # 4 часа спустя
            price_4h = await self._get_price_at_time(
                similar.asset,
                move_time + timedelta(hours=4),
                session
            )
            if price_4h:
                change_4h = ((price_4h - price_at_move) / price_at_move) * 100
                price_changes_4h.append(change_4h)
            
            # 24 часа спустя
            price_24h = await self._get_price_at_time(
                similar.asset,
                move_time + timedelta(hours=24),
                session
            )
            if price_24h:
                change_24h = ((price_24h - price_at_move) / price_at_move) * 100
                price_changes_24h.append(change_24h)
            
            # 7 дней спустя
            price_7d = await self._get_price_at_time(
                similar.asset,
                move_time + timedelta(days=7),
                session
            )
            if price_7d:
                change_7d = ((price_7d - price_at_move) / price_at_move) * 100
                price_changes_7d.append(change_7d)
        
        # Рассчитываем средние значения
        if price_changes_1h:
            movement.avg_price_change_1h = sum(price_changes_1h) / len(price_changes_1h)
        
        if price_changes_4h:
            movement.avg_price_change_4h = sum(price_changes_4h) / len(price_changes_4h)
        
        if price_changes_24h:
            movement.avg_price_change_24h = sum(price_changes_24h) / len(price_changes_24h)
        
        if price_changes_7d:
            movement.avg_price_change_7d = sum(price_changes_7d) / len(price_changes_7d)
        
        return movement
    
    def _is_hot_wallet(self, address: str) -> bool:
        """Проверка является ли адрес hot wallet"""
        address_lower = address.lower()
        return address_lower in self.hot_wallets or address_lower in self.smart_wallets
    
    def _get_wallet_label(self, address: str) -> str:
        """Получение метки кошелька"""
        address_lower = address.lower()
        
        if address_lower in self.hot_wallets:
            return self.hot_wallets[address_lower]['label']
        elif address_lower in self.smart_wallets:
            return self.smart_wallets[address_lower]['label']
        else:
            return "Unknown Wallet"
    
    async def _analyze_pattern(
        self,
        movement: WalletMovement,
        session: aiohttp.ClientSession
    ) -> WalletMovement:
        """
        Определение accumulation/distribution паттерна
        
        Accumulation сигналы:
        - Большие притоки на биржевые hot wallets
        - Серия последовательных пополнений
        - Рост балансов перед историческими ралли
        
        Distribution сигналы:
        - Большие оттоки с биржевых hot wallets
        - Массовые выводы на cold storage
        - Снижение балансов перед падениями
        """
        
        # Получаем последние движения этого кошелька
        recent_moves = self._get_recent_moves(
            movement.wallet_address,
            movement.asset,
            hours=24
        )
        
        # Анализ accumulation
        if movement.direction == 'inflow':
            # Проверяем на серию притоков
            inflows = [m for m in recent_moves if m.direction == 'inflow']
            
            if len(inflows) >= 3:  # 3+ притока за 24ч
                total_inflow = sum(m.amount_usd for m in inflows)
                
                if total_inflow > 1_000_000:  # $1M+
                    movement.is_accumulation = True
                    movement.confidence = min(90, 60 + len(inflows) * 5)
        
        # Анализ distribution
        elif movement.direction == 'outflow':
            # Проверяем на серию оттоков
            outflows = [m for m in recent_moves if m.direction == 'outflow']
            
            if len(outflows) >= 3:  # 3+ оттока за 24ч
                total_outflow = sum(m.amount_usd for m in outflows)
                
                if total_outflow > 1_000_000:  # $1M+
                    movement.is_distribution = True
                    movement.confidence = min(90, 60 + len(outflows) * 5)
        
        return movement
    
    def _get_recent_moves(
        self,
        wallet_address: str,
        asset: str,
        hours: int = 24
    ) -> List[WalletMovement]:
        """Получение недавних движений кошелька"""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            m for m in self.movement_history
            if m.wallet_address.lower() == wallet_address.lower()
            and m.asset == asset
            and m.detected_at >= cutoff
        ]
    
    def _find_similar_moves(
        self,
        movement: WalletMovement,
        tolerance: float = 0.3
    ) -> List[WalletMovement]:
        """Поиск похожих движений в истории"""
        
        similar = []
        target_amount = movement.amount_usd
        
        for historical in self.movement_history:
            # Тот же asset и направление
            if (historical.asset != movement.asset or 
                historical.direction != movement.direction):
                continue
            
            # Примерно похожая сумма (±30%)
            if target_amount > 0:
                amount_ratio = historical.amount_usd / target_amount
                if not (1 - tolerance <= amount_ratio <= 1 + tolerance):
                    continue
            
            # Не совсем недавнее (минимум 7 дней назад)
            days_ago = (datetime.utcnow() - historical.detected_at).days
            if days_ago < 7:
                continue
            
            # Должна быть цена на момент движения
            if not historical.price_at_move:
                continue
            
            similar.append(historical)
        
        return similar[:10]  # Топ-10 похожих
    
    def _add_to_cluster(self, movement: WalletMovement):
        """Добавление в кластер связанных транзакций"""
        
        # Кластер = движения одного актива в течение короткого времени
        cluster_key = f"{movement.asset}_{movement.detected_at.strftime('%Y%m%d%H')}"
        self.clusters[cluster_key].append(movement)
        
        # Очистка старых кластеров
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.clusters = {
            k: v for k, v in self.clusters.items()
            if v and v[0].detected_at >= cutoff
        }
    
    def get_cluster_analysis(self, asset: str, hours: int = 6) -> Optional[Dict]:
        """
        Анализ кластера движений
        
        Возвращает агрегированную информацию о движениях актива
        """
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        relevant_moves = [
            m for cluster in self.clusters.values()
            for m in cluster
            if m.asset == asset and m.detected_at >= cutoff
        ]
        
        if not relevant_moves:
            return None
        
        total_inflow = sum(m.amount_usd for m in relevant_moves if m.direction == 'inflow')
        total_outflow = sum(m.amount_usd for m in relevant_moves if m.direction == 'outflow')
        net_flow = total_inflow - total_outflow
        
        accumulation_count = sum(1 for m in relevant_moves if m.is_accumulation)
        distribution_count = sum(1 for m in relevant_moves if m.is_distribution)
        
        return {
            'asset': asset,
            'period_hours': hours,
            'total_moves': len(relevant_moves),
            'inflow_usd': total_inflow,
            'outflow_usd': total_outflow,
            'net_flow_usd': net_flow,
            'accumulation_signals': accumulation_count,
            'distribution_signals': distribution_count,
            'dominant_signal': 'ACCUMULATION' if net_flow > 0 else 'DISTRIBUTION' if net_flow < 0 else 'NEUTRAL',
            'confidence': min(100, abs(net_flow) / 1_000_000 * 20)
        }
    
    def add_smart_wallet(
        self,
        address: str,
        chain: str,
        label: str,
        metadata: Optional[Dict] = None
    ):
        """Добавление smart money кошелька для отслеживания"""
        
        self.smart_wallets[address.lower()] = {
            'label': label,
            'chain': chain,
            'added_at': datetime.utcnow(),
            'metadata': metadata or {}
        }
        
        print(f"✅ [HOT_WALLET] Добавлен smart wallet: {label}")
    
    def _get_coingecko_id(self, asset: str) -> Optional[str]:
        """Маппинг символов на CoinGecko IDs"""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'MATIC': 'matic-network',
            'DOT': 'polkadot',
            'AVAX': 'avalanche-2',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'ATOM': 'cosmos',
            'NEAR': 'near',
            'APT': 'aptos',
            'ARB': 'arbitrum',
            'OP': 'optimism',
            'LTC': 'litecoin',
            'AAVE': 'aave',
            'USDT': 'tether',
            'USDC': 'usd-coin'
        }
        
        return mapping.get(asset.upper())
    
    def _load_hot_wallets(self) -> Dict[str, Dict]:
        """Загрузка базы известных hot wallets"""
        
        # Биржевые hot wallets (Ethereum/EVM chains)
        wallets = {
            # Binance
            '0x28c6c06298d514db089934071355e5743bf21d60': {'label': 'Binance Hot Wallet 1', 'exchange': 'Binance', 'type': 'hot'},
            '0x21a31ee1afc51d94c2efccaa2092ad1028285549': {'label': 'Binance Hot Wallet 2', 'exchange': 'Binance', 'type': 'hot'},
            '0xdfd5293d8e347dfe59e90efd55b2956a1343963d': {'label': 'Binance Hot Wallet 3', 'exchange': 'Binance', 'type': 'hot'},
            '0x564286362092d8e7936f0549571a803b203aaced': {'label': 'Binance Hot Wallet 4', 'exchange': 'Binance', 'type': 'hot'},
            
            # Coinbase
            '0x71660c4005ba85c37ccec55d0c4493e66fe775d3': {'label': 'Coinbase Hot Wallet', 'exchange': 'Coinbase', 'type': 'hot'},
            '0x503828976d22510aad0201ac7ec88293211d23da': {'label': 'Coinbase 2', 'exchange': 'Coinbase', 'type': 'hot'},
            '0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740': {'label': 'Coinbase 3', 'exchange': 'Coinbase', 'type': 'hot'},
            
            # Kraken
            '0x2910543af39aba0cd09dbb2d50200b3e800a63d2': {'label': 'Kraken Hot Wallet', 'exchange': 'Kraken', 'type': 'hot'},
            '0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13': {'label': 'Kraken 2', 'exchange': 'Kraken', 'type': 'hot'},
            
            # Bitfinex
            '0x1151314c646ce4e0efd76d1af4760ae66a9fe30f': {'label': 'Bitfinex Hot Wallet', 'exchange': 'Bitfinex', 'type': 'hot'},
            '0x876eabf441b2ee5b5b0554fd502a8e0600950cfa': {'label': 'Bitfinex 2', 'exchange': 'Bitfinex', 'type': 'hot'},
            
            # OKX
            '0x98ec059dc3adfbdd63429454aeb0c990fba4a128': {'label': 'OKX Hot Wallet', 'exchange': 'OKX', 'type': 'hot'},
            '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': {'label': 'OKX 2', 'exchange': 'OKX', 'type': 'hot'},
            
            # Bybit
            '0xf89d7b9c864f589bbf53a82105107622b35eaa40': {'label': 'Bybit Hot Wallet', 'exchange': 'Bybit', 'type': 'hot'},
            
            # Gate.io
            '0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c': {'label': 'Gate.io Hot Wallet', 'exchange': 'Gate.io', 'type': 'hot'},
            
            # Huobi
            '0xab5c66752a9e8167967685f1450532fb96d5d24f': {'label': 'Huobi Hot Wallet', 'exchange': 'Huobi', 'type': 'hot'},
            
            # KuCoin
            '0x2b5634c42055806a59e9107ed44d43c426e58258': {'label': 'KuCoin Hot Wallet', 'exchange': 'KuCoin', 'type': 'hot'}
        }
        
        return wallets
    
    def get_stats(self) -> Dict:
        """Статистика работы трекера"""
        
        accuracy = 0.0
        if self.stats['total_predictions'] > 0:
            accuracy = (self.stats['accurate_predictions'] / self.stats['total_predictions']) * 100
        
        return {
            'total_tracked': self.stats['total_tracked'],
            'hot_wallets_count': len(self.hot_wallets),
            'smart_wallets_count': len(self.smart_wallets),
            'accumulation_signals': self.stats['accumulation_signals'],
            'distribution_signals': self.stats['distribution_signals'],
            'prediction_accuracy': accuracy,
            'active_clusters': len(self.clusters),
            'history_size': len(self.movement_history)
        }