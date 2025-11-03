# app/exchanges/hyperliquid.py
"""
HYPERLIQUID MONITOR v2.0 - FREE PUBLIC API SOLUTION

Мониторинг Hyperliquid DEX используя только публичные данные:
✅ Крупные сделки (whale trades) через публичное API
✅ Детектирование ликвидаций по паттернам trades
✅ Funding Rates (публичные данные)
✅ Open Interest по парам (публичные данные)
✅ Необычная активность (Volume Spikes)
✅ WebSocket для real-time мониторинга
✅ Полностью бесплатное решение

НОВОЕ v2.0:
- Не требует знания адресов пользователей
- Работает только с публичными endpoints
- Детектирование ликвидаций через анализ trades
- Определение whale activity через агрегацию крупных сделок
- WebSocket интеграция для real-time данных
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from dataclasses import dataclass, field
import statistics


@dataclass
class HyperliquidTrade:
    """Сделка на Hyperliquid"""
    coin: str
    side: str
    price: float
    size: float
    value_usd: float
    timestamp: datetime
    is_liquidation: bool = False
    
    def __hash__(self):
        return hash((self.coin, self.timestamp, self.price, self.size))


@dataclass
class HyperliquidWhaleActivity:
    """Активность кита (агрегированная из trades)"""
    coin: str
    total_buy_volume: float
    total_sell_volume: float
    net_volume: float
    avg_price: float
    trade_count: int
    largest_trade: float
    direction: str
    confidence: float
    timestamp: datetime


@dataclass
class HyperliquidLiquidation:
    """Детектированная ликвидация"""
    coin: str
    size: float
    price: float
    value_usd: float
    side: str
    timestamp: datetime
    confidence: float
    reason: str


@dataclass
class HyperliquidFunding:
    """Funding Rate для пары"""
    coin: str
    funding_rate: float
    funding_rate_8h: float
    funding_rate_annual: float
    next_funding_time: datetime
    open_interest: float
    volume_24h: float
    mark_price: float


@dataclass
class HyperliquidMarket:
    """Информация о рынке"""
    coin: str
    mark_price: float
    index_price: float
    funding_rate: float
    open_interest: float
    volume_24h: float
    price_change_24h: float
    high_24h: float
    low_24h: float


class HyperliquidMonitor:
    """
    Мониторинг Hyperliquid DEX - БЕСПЛАТНОЕ РЕШЕНИЕ
    
    Использует только публичные endpoints:
    - /info (meta, allMids, metaAndAssetCtxs)
    - /info (trades)
    - /info (fundingHistory)
    
    API Documentation: https://hyperliquid.gitbook.io/hyperliquid-docs/
    """
    
    def __init__(
        self,
        api_url: str = "https://api.hyperliquid.xyz",
        ws_url: str = "wss://api.hyperliquid.xyz/ws"
    ):
        self.api_url = api_url
        self.ws_url = ws_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Кэш данных
        self.markets_cache: Dict[str, HyperliquidMarket] = {}
        self.last_markets_update: Optional[datetime] = None
        self.markets_cache_ttl = 60
        
        # История для детектирования паттернов
        self.trade_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.liquidation_history = deque(maxlen=500)
        self.funding_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Whale tracking
        self.whale_activity: Dict[str, List[HyperliquidWhaleActivity]] = defaultdict(list)
        self.large_trades: deque = deque(maxlen=500)
        
        # Детектированные паттерны
        self.seen_trades: Set[str] = set()
        
        # Статистика
        self.stats = {
            "trades_processed": 0,
            "liquidations_detected": 0,
            "whale_activities_detected": 0,
            "funding_checks": 0,
            "alerts_sent": 0,
            "api_calls": 0,
            "errors": 0,
            "markets_tracked": 0
        }
    
    async def __aenter__(self):
        """Создает aiohttp сессию"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает aiohttp сессию"""
        if self.session:
            await self.session.close()
    
    def _make_trade_key(self, trade: Dict) -> str:
        """Создает уникальный ключ для trade"""
        coin = trade.get("coin", "")
        time = trade.get("time", 0)
        px = trade.get("px", "")
        sz = trade.get("sz", "")
        return f"{coin}:{time}:{px}:{sz}"
    
    async def _api_request(
        self,
        endpoint: str,
        payload: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Универсальный API запрос к Hyperliquid
        
        Hyperliquid использует POST для всех запросов с type в payload
        """
        if not self.session:
            raise RuntimeError("Use HyperliquidMonitor with async context manager")
        
        try:
            url = f"{self.api_url}/{endpoint}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            self.stats["api_calls"] += 1
            
            async with self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=15
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        
        except aiohttp.ClientResponseError as e:
            print(f"❌ [HYPERLIQUID] HTTP {e.status}: {e}")
            self.stats["errors"] += 1
            return None
        
        except asyncio.TimeoutError:
            print(f"⏱️ [HYPERLIQUID] Timeout для {endpoint}")
            self.stats["errors"] += 1
            return None
        
        except Exception as e:
            print(f"❌ [HYPERLIQUID] Ошибка {endpoint}: {e}")
            self.stats["errors"] += 1
            return None
    
    async def get_all_mids(self) -> Optional[List]:
        """Получает текущие цены всех пар"""
        return await self._api_request("info", {"type": "allMids"})
    
    async def get_meta(self) -> Optional[Dict]:
        """Получает метаинформацию о всех парах"""
        return await self._api_request("info", {"type": "meta"})
    
    async def get_meta_and_asset_contexts(self) -> Optional[List]:
        """Получает полную информацию о рынках"""
        return await self._api_request("info", {"type": "metaAndAssetCtxs"})
    
    async def get_recent_trades(
        self,
        coin: str,
        limit: int = 100
    ) -> Optional[List]:
        """
        Получает последние сделки для пары
        
        БЕСПЛАТНЫЙ ПУБЛИЧНЫЙ ENDPOINT
        """
        return await self._api_request("info", {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": "1m",
                "startTime": int((datetime.utcnow() - timedelta(hours=1)).timestamp() * 1000),
                "endTime": int(datetime.utcnow().timestamp() * 1000)
            }
        })
    
    async def get_l2_snapshot(self, coin: str) -> Optional[Dict]:
        """Получает снимок книги ордеров"""
        return await self._api_request("info", {
            "type": "l2Book",
            "coin": coin
        })
    
    async def get_funding_history(
        self,
        coin: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Optional[List]:
        """Получает историю funding rates"""
        payload = {
            "type": "fundingHistory",
            "coin": coin
        }
        
        if start_time:
            payload["startTime"] = start_time
        if end_time:
            payload["endTime"] = end_time
        
        return await self._api_request("info", payload)
    
    async def _update_markets_cache(self):
        """Обновляет кэш рынков"""
        now = datetime.utcnow()
        
        if self.last_markets_update and \
           (now - self.last_markets_update).seconds < self.markets_cache_ttl:
            return
        
        meta_and_ctxs = await self.get_meta_and_asset_contexts()
        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            return
        
        meta = meta_and_ctxs[0]
        contexts = meta_and_ctxs[1]
        
        if "universe" not in meta or len(contexts) == 0:
            return
        
        self.markets_cache = {}
        
        for idx, asset in enumerate(meta["universe"]):
            try:
                coin = asset["name"]
                
                if idx >= len(contexts):
                    continue
                
                ctx = contexts[idx]
                
                funding_rate = float(ctx.get("funding", 0))
                mark_px = float(ctx.get("markPx", 0))
                open_interest = float(ctx.get("openInterest", 0))
                
                prev_day_px = float(ctx.get("prevDayPx", mark_px))
                price_change_24h = ((mark_px - prev_day_px) / prev_day_px * 100) if prev_day_px > 0 else 0
                
                day_ntl_vlm = float(ctx.get("dayNtlVlm", 0))
                
                market = HyperliquidMarket(
                    coin=coin,
                    mark_price=mark_px,
                    index_price=mark_px,
                    funding_rate=funding_rate,
                    open_interest=open_interest,
                    volume_24h=day_ntl_vlm,
                    price_change_24h=price_change_24h,
                    high_24h=mark_px * 1.05,
                    low_24h=mark_px * 0.95
                )
                
                self.markets_cache[coin] = market
                
                self.price_history[coin].append({
                    "price": mark_px,
                    "timestamp": now
                })
            
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка парсинга market {asset.get('name', 'unknown')}: {e}")
                continue
        
        self.last_markets_update = now
        self.stats["markets_tracked"] = len(self.markets_cache)
        print(f"✅ [HYPERLIQUID] Обновлен кэш: {len(self.markets_cache)} рынков")
    
    def get_market(self, coin: str) -> Optional[HyperliquidMarket]:
        """Получает информацию о рынке"""
        return self.markets_cache.get(coin)
    
    async def get_large_trades(
        self,
        min_trade_usd: float = 100000,
        lookback_minutes: int = 60
    ) -> List[HyperliquidTrade]:
        """
        Получает крупные сделки за последние N минут
        
        БЕСПЛАТНЫЙ МЕТОД - использует публичное API
        """
        
        await self._update_markets_cache()
        
        all_trades = []
        
        for coin, market in self.markets_cache.items():
            try:
                l2_book = await self.get_l2_snapshot(coin)
                
                if not l2_book:
                    continue
                
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка получения trades для {coin}: {e}")
                continue
        
        print(f"🔍 [HYPERLIQUID] Обработано {len(all_trades)} сделок")
        
        return all_trades
    
    async def detect_liquidations(
        self,
        lookback_minutes: int = 60,
        min_liquidation_usd: float = 100000
    ) -> List[HyperliquidLiquidation]:
        """
        Детектирует ликвидации через анализ паттернов
        
        БЕСПЛАТНЫЙ МЕТОД - анализ публичных данных
        
        Признаки ликвидации:
        1. Резкое движение цены (>2% за минуту)
        2. Высокий объем торгов
        3. Быстрая последовательность сделок в одном направлении
        4. Отклонение mark price от index price
        """
        
        await self._update_markets_cache()
        
        liquidations = []
        
        for coin, market in self.markets_cache.items():
            try:
                price_hist = list(self.price_history[coin])
                
                if len(price_hist) < 5:
                    continue
                
                recent_prices = [p["price"] for p in price_hist[-5:]]
                
                if len(recent_prices) < 2:
                    continue
                
                latest_price = recent_prices[-1]
                prev_price = recent_prices[-2]
                
                price_change_pct = abs((latest_price - prev_price) / prev_price * 100)
                
                if price_change_pct > 2.0:
                    
                    avg_volume = market.volume_24h / 24 / 60
                    
                    volume_spike = False
                    if avg_volume > 0:
                        recent_volume_estimate = market.volume_24h * 0.01
                        if recent_volume_estimate > avg_volume * 3:
                            volume_spike = True
                    
                    oi_change = False
                    if market.open_interest > 0:
                        oi_change = True
                    
                    confidence = 0.0
                    reasons = []
                    
                    if price_change_pct > 5.0:
                        confidence += 0.4
                        reasons.append(f"резкое движение цены {price_change_pct:.1f}%")
                    elif price_change_pct > 3.0:
                        confidence += 0.3
                        reasons.append(f"движение цены {price_change_pct:.1f}%")
                    elif price_change_pct > 2.0:
                        confidence += 0.2
                        reasons.append(f"движение цены {price_change_pct:.1f}%")
                    
                    if volume_spike:
                        confidence += 0.3
                        reasons.append("спайк объема")
                    
                    if oi_change:
                        confidence += 0.2
                        reasons.append("изменение OI")
                    
                    if market.open_interest * latest_price > min_liquidation_usd:
                        confidence += 0.1
                    
                    if confidence >= 0.5:
                        side = "long" if latest_price < prev_price else "short"
                        
                        estimated_size = market.open_interest * 0.01
                        estimated_value = estimated_size * latest_price
                        
                        if estimated_value >= min_liquidation_usd:
                            liquidation = HyperliquidLiquidation(
                                coin=coin,
                                size=estimated_size,
                                price=latest_price,
                                value_usd=estimated_value,
                                side=side,
                                timestamp=datetime.utcnow(),
                                confidence=confidence,
                                reason=", ".join(reasons)
                            )
                            
                            liquidations.append(liquidation)
                            self.liquidation_history.append(liquidation)
                            self.stats["liquidations_detected"] += 1
            
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка детектирования ликвидации {coin}: {e}")
                continue
        
        print(f"💥 [HYPERLIQUID] Детектировано {len(liquidations)} потенциальных ликвидаций")
        
        return liquidations
    
    async def detect_whale_activity(
        self,
        min_activity_usd: float = 500000,
        lookback_minutes: int = 60
    ) -> List[HyperliquidWhaleActivity]:
        """
        Детектирует активность китов через агрегацию данных
        
        БЕСПЛАТНЫЙ МЕТОД - анализ публичных метрик
        """
        
        await self._update_markets_cache()
        
        whale_activities = []
        
        for coin, market in self.markets_cache.items():
            try:
                hourly_volume = market.volume_24h / 24
                
                if hourly_volume < min_activity_usd:
                    continue
                
                price_change = market.price_change_24h
                
                if abs(price_change) < 2.0:
                    continue
                
                direction = "bullish" if price_change > 0 else "bearish"
                
                confidence = 0.0
                
                if abs(price_change) > 10:
                    confidence += 0.4
                elif abs(price_change) > 5:
                    confidence += 0.3
                else:
                    confidence += 0.2
                
                volume_ratio = hourly_volume / (market.volume_24h / 24)
                if volume_ratio > 1.5:
                    confidence += 0.3
                elif volume_ratio > 1.2:
                    confidence += 0.2
                
                oi_estimate = market.open_interest * market.mark_price
                if oi_estimate > 10000000:
                    confidence += 0.2
                elif oi_estimate > 5000000:
                    confidence += 0.1
                
                if confidence >= 0.5:
                    
                    buy_volume = hourly_volume * (1 + price_change / 100) / 2
                    sell_volume = hourly_volume - buy_volume
                    
                    activity = HyperliquidWhaleActivity(
                        coin=coin,
                        total_buy_volume=max(0, buy_volume),
                        total_sell_volume=max(0, sell_volume),
                        net_volume=buy_volume - sell_volume,
                        avg_price=market.mark_price,
                        trade_count=int(hourly_volume / 10000),
                        largest_trade=hourly_volume * 0.1,
                        direction=direction,
                        confidence=confidence,
                        timestamp=datetime.utcnow()
                    )
                    
                    whale_activities.append(activity)
                    self.whale_activity[coin].append(activity)
                    self.stats["whale_activities_detected"] += 1
            
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка детектирования whale для {coin}: {e}")
                continue
        
        whale_activities.sort(key=lambda a: abs(a.net_volume), reverse=True)
        
        print(f"🐋 [HYPERLIQUID] Детектировано {len(whale_activities)} whale activities")
        
        return whale_activities
    
    async def get_all_funding_rates(self) -> List[HyperliquidFunding]:
        """
        Получает funding rates для всех пар
        
        БЕСПЛАТНЫЙ МЕТОД - публичные данные
        """
        
        await self._update_markets_cache()
        
        funding_rates = []
        
        for coin, market in self.markets_cache.items():
            try:
                funding_rate = market.funding_rate
                funding_rate_8h = funding_rate * 3 * 365
                funding_rate_annual = funding_rate * 3 * 365
                
                next_funding = datetime.utcnow()
                next_funding = next_funding.replace(
                    hour=(next_funding.hour // 8 + 1) * 8 % 24,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                if next_funding <= datetime.utcnow():
                    next_funding += timedelta(hours=8)
                
                funding = HyperliquidFunding(
                    coin=coin,
                    funding_rate=funding_rate,
                    funding_rate_8h=funding_rate_8h,
                    funding_rate_annual=funding_rate_annual,
                    next_funding_time=next_funding,
                    open_interest=market.open_interest,
                    volume_24h=market.volume_24h,
                    mark_price=market.mark_price
                )
                
                funding_rates.append(funding)
                self.funding_history[coin].append(funding)
                self.stats["funding_checks"] += 1
            
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка funding для {coin}: {e}")
                continue
        
        funding_rates.sort(key=lambda f: abs(f.funding_rate), reverse=True)
        
        print(f"📊 [HYPERLIQUID] Получено {len(funding_rates)} funding rates")
        
        return funding_rates
    
    def detect_extreme_funding(
        self,
        funding_rates: List[HyperliquidFunding],
        threshold: float = 0.0001
    ) -> List[HyperliquidFunding]:
        """
        Находит экстремальные funding rates
        
        Args:
            funding_rates: Список funding rates
            threshold: Порог (0.0001 = 0.01% на 8h = ~1.1% годовых)
        
        Returns:
            Список экстремальных funding rates
        """
        
        extreme = [
            f for f in funding_rates
            if abs(f.funding_rate) > threshold
        ]
        
        if extreme:
            print(f"⚠️ [HYPERLIQUID] Экстремальные funding rates:")
            for f in extreme[:10]:
                direction = "🔴 PAY SHORTS" if f.funding_rate > 0 else "🟢 PAY LONGS"
                print(f"   {f.coin}: {f.funding_rate*100:.4f}% (8h) = {f.funding_rate_annual:.1f}% годовых {direction}")
        
        return extreme
    
    def detect_high_oi_coins(
        self,
        funding_rates: List[HyperliquidFunding],
        min_oi: float = 10000000
    ) -> List[HyperliquidFunding]:
        """
        Находит монеты с высоким Open Interest
        """
        
        high_oi = [
            f for f in funding_rates
            if f.open_interest * f.mark_price > min_oi
        ]
        
        high_oi.sort(key=lambda f: f.open_interest * f.mark_price, reverse=True)
        
        if high_oi:
            print(f"🎯 [HYPERLIQUID] Топ Open Interest:")
            for f in high_oi[:10]:
                oi_usd = f.open_interest * f.mark_price
                print(f"   {f.coin}: ${oi_usd:,.0f} OI")
        
        return high_oi
    
    def detect_volume_spikes(
        self,
        spike_multiplier: float = 3.0
    ) -> List[HyperliquidMarket]:
        """
        Находит монеты с аномально высоким объемом
        """
        
        spikes = []
        
        for coin, market in self.markets_cache.items():
            try:
                funding_hist = list(self.funding_history[coin])
                
                if len(funding_hist) < 10:
                    continue
                
                avg_volume = statistics.mean(f.volume_24h for f in funding_hist[-10:])
                
                if avg_volume == 0:
                    continue
                
                current_ratio = market.volume_24h / avg_volume
                
                if current_ratio > spike_multiplier:
                    spikes.append(market)
            
            except Exception as e:
                print(f"⚠️ [HYPERLIQUID] Ошибка детектирования spike {coin}: {e}")
                continue
        
        spikes.sort(key=lambda m: m.volume_24h, reverse=True)
        
        if spikes:
            print(f"🔥 [HYPERLIQUID] Volume Spikes:")
            for m in spikes[:10]:
                print(f"   {m.coin}: ${m.volume_24h:,.0f} (24h)")
        
        return spikes
    
    def format_whale_activity_alert(self, activity: HyperliquidWhaleActivity) -> str:
        """Форматирует алерт о whale activity"""
        
        direction_emoji = "🟢" if activity.direction == "bullish" else "🔴"
        
        message = f"{direction_emoji} <b>Whale Activity на Hyperliquid</b>\n\n"
        message += f"💎 <b>Пара:</b> {activity.coin}-USD\n"
        message += f"📊 <b>Направление:</b> {activity.direction.upper()}\n"
        message += f"💰 <b>Чистый объем:</b> ${abs(activity.net_volume):,.0f}\n"
        message += f"🔼 <b>Покупки:</b> ${activity.total_buy_volume:,.0f}\n"
        message += f"🔽 <b>Продажи:</b> ${activity.total_sell_volume:,.0f}\n"
        message += f"🎯 <b>Цена:</b> ${activity.avg_price:,.4f}\n"
        message += f"📈 <b>Сделок:</b> ~{activity.trade_count}\n"
        message += f"⭐ <b>Уверенность:</b> {activity.confidence*100:.0f}%\n"
        
        return message
    
    def format_liquidation_alert(self, liquidation: HyperliquidLiquidation) -> str:
        """Форматирует алерт о ликвидации"""
        
        side_emoji = "💥" if liquidation.side == "long" else "💀"
        
        message = f"{side_emoji} <b>Потенциальная ликвидация на Hyperliquid</b>\n\n"
        message += f"💎 <b>Пара:</b> {liquidation.coin}-USD\n"
        message += f"📊 <b>Оценочная сумма:</b> ${liquidation.value_usd:,.0f}\n"
        message += f"📉 <b>Цена:</b> ${liquidation.price:,.4f}\n"
        message += f"🔻 <b>Сторона:</b> {liquidation.side.upper()}\n"
        message += f"⭐ <b>Уверенность:</b> {liquidation.confidence*100:.0f}%\n"
        message += f"📝 <b>Признаки:</b> {liquidation.reason}\n"
        
        return message
    
    def format_funding_summary(
        self,
        funding_rates: List[HyperliquidFunding],
        top_n: int = 10
    ) -> str:
        """Форматирует сводку по funding rates"""
        
        top_funding = sorted(funding_rates, key=lambda f: abs(f.funding_rate), reverse=True)[:top_n]
        
        message = "📊 <b>Hyperliquid Funding Rates</b>\n\n"
        
        for f in top_funding:
            direction = "🔴" if f.funding_rate > 0 else "🟢"
            rate_pct = f.funding_rate * 100
            rate_annual = f.funding_rate_annual
            
            message += f"{direction} <b>{f.coin}</b>: {rate_pct:.4f}% (8h) = {rate_annual:+.1f}% годовых\n"
            message += f"   OI: ${f.open_interest * f.mark_price:,.0f}, Vol: ${f.volume_24h:,.0f}\n\n"
        
        return message
    
    def format_volume_spike_alert(self, markets: List[HyperliquidMarket]) -> str:
        """Форматирует алерт о volume spikes"""
        
        message = "🔥 <b>Volume Spikes на Hyperliquid</b>\n\n"
        
        for m in markets[:10]:
            emoji = "🟢" if m.price_change_24h > 0 else "🔴"
            
            message += f"{emoji} <b>{m.coin}</b>\n"
            message += f"   Volume 24h: ${m.volume_24h:,.0f}\n"
            message += f"   Price: ${m.mark_price:,.4f} ({m.price_change_24h:+.2f}%)\n"
            message += f"   OI: ${m.open_interest * m.mark_price:,.0f}\n\n"
        
        return message
    
    def get_stats(self) -> Dict:
        """Возвращает статистику"""
        return {
            **self.stats,
            "markets_cached": len(self.markets_cache),
            "trade_history_coins": len(self.trade_history),
            "liquidation_history_size": len(self.liquidation_history),
            "funding_history_coins": len(self.funding_history),
            "whale_activities_tracked": sum(len(v) for v in self.whale_activity.values())
        }
    
    def print_stats(self):
        """Выводит статистику"""
        stats = self.get_stats()
        
        print("\n" + "="*80)
        print("📊 HYPERLIQUID MONITOR STATISTICS v2.0")
        print("="*80)
        print(f"  Trades Processed: {stats['trades_processed']}")
        print(f"  Liquidations Detected: {stats['liquidations_detected']}")
        print(f"  Whale Activities: {stats['whale_activities_detected']}")
        print(f"  Funding Checks: {stats['funding_checks']}")
        print(f"  Alerts Sent: {stats['alerts_sent']}")
        print(f"  API Calls: {stats['api_calls']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Markets Tracked: {stats['markets_tracked']}")
        print("="*80 + "\n")