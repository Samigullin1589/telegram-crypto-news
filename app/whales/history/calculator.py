# app/whales/history/calculator.py
"""
Price Delta Calculator
"""

from typing import Optional, Dict
from datetime import datetime, timedelta

import aiohttp

from app.whales.history.coingecko import CoinGeckoClient


class DeltaCalculator:
    """Расчёт изменения цен"""
    
    def __init__(self):
        self.coingecko = CoinGeckoClient()
    
    async def calculate_price_deltas(
        self,
        asset: str,
        event_time: datetime,
        price_at_event: float,
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, float]]:
        """
        Рассчитывает реальные Δ% через CoinGecko History API
        
        Args:
            asset: Символ актива
            event_time: Время события
            price_at_event: Цена на момент события
            session: aiohttp сессия
        
        Returns:
            Dict с дельтами {"1h": 2.5, "4h": -1.2, "24h": 5.0}
        """
        if not price_at_event or price_at_event == 0:
            return None
        
        try:
            coin_id = self.coingecko.get_coin_id(asset)
            if not coin_id:
                return None
            
            t1h = event_time + timedelta(hours=1)
            t4h = event_time + timedelta(hours=4)
            t24h = event_time + timedelta(hours=24)
            
            now = datetime.utcnow()
            if t1h > now:
                return None
            
            prices = {}
            
            for label, target_time in [("1h", t1h), ("4h", t4h), ("24h", t24h)]:
                if target_time > now:
                    continue
                
                price = await self.coingecko.get_historical_price(
                    coin_id, target_time, session
                )
                
                if price:
                    delta_pct = ((price - price_at_event) / price_at_event) * 100
                    prices[label] = round(delta_pct, 1)
            
            if not prices:
                return None
            
            return prices
        
        except Exception as e:
            print(f"⚠️  [CALCULATOR] Ошибка расчёта дельт: {e}")
            return None
    
    @staticmethod
    def get_size_bucket(amount_usd: float) -> str:
        """
        Определяет размерную категорию
        
        Args:
            amount_usd: Сумма в USD
        
        Returns:
            Категория: small, medium, large, whale
        """
        if amount_usd < 500_000:
            return "small"
        elif amount_usd < 2_000_000:
            return "medium"
        elif amount_usd < 10_000_000:
            return "large"
        else:
            return "whale"