# app/whales/history/manager.py
"""
History Manager - Main Orchestrator
"""

from typing import Optional
from datetime import datetime

import aiohttp

from app.config import config
from app.whales.normalize import WhaleEvent, HistoryHint
from app.whales.history.storage import EventStorage
from app.whales.history.calculator import DeltaCalculator


class HistoryManager:
    """Управление историей для функции 'В прошлый раз'"""
    
    def __init__(self):
        history_dir = config.data_dir / 'history'
        
        self.storage = EventStorage(history_dir)
        self.calculator = DeltaCalculator()
    
    def save_event(self, event: WhaleEvent, verdict: str) -> bool:
        """
        Сохраняет событие в историю
        
        Args:
            event: Whale событие
            verdict: Вердикт (bullish/bearish/neutral)
        
        Returns:
            True если успешно сохранено
        """
        try:
            entry = {
                "ts": event.tx_time_utc.isoformat(),
                "phase": event.phase,
                "direction": event.direction,
                "size_bucket": self.calculator.get_size_bucket(event.amount_usd),
                "price_at_tx": event.market.price_usd if hasattr(event.market, 'price_usd') else 0,
                "verdict": verdict,
                "amount_usd": event.amount_usd
            }
            
            return self.storage.save_event(event.asset, entry)
        
        except Exception as e:
            print(f"⚠️  [HISTORY] Ошибка сохранения: {e}")
            return False
    
    async def find_similar_event(
        self,
        event: WhaleEvent,
        session: aiohttp.ClientSession
    ) -> Optional[HistoryHint]:
        """
        Ищет похожее событие и рассчитывает РЕАЛЬНЫЕ Δ%
        
        Args:
            event: Текущее событие
            session: aiohttp сессия для API запросов
        
        Returns:
            HistoryHint с дельтами или None
        """
        try:
            recent_events = self.storage.load_recent_events(event.asset, days=30)
            
            if not recent_events:
                return None
            
            current_bucket = self.calculator.get_size_bucket(event.amount_usd)
            
            candidates = self.storage.find_similar_events(
                recent_events,
                event.direction,
                current_bucket,
                event.phase
            )
            
            if not candidates:
                return None
            
            match = candidates[0]
            
            match_ts = datetime.fromisoformat(match["ts"])
            price_at_event = match.get("price_at_tx", 0)
            
            deltas = await self.calculator.calculate_price_deltas(
                event.asset,
                match_ts,
                price_at_event,
                session
            )
            
            if deltas:
                hint = HistoryHint(
                    d1h=deltas.get("1h"),
                    d4h=deltas.get("4h"),
                    d24h=deltas.get("24h"),
                    comparable_ts=match["ts"]
                )
                return hint
            
            return None
        
        except Exception as e:
            print(f"⚠️  [HISTORY] Ошибка поиска: {e}")
            return None