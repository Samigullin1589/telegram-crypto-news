# app/scheduler/event_fetcher.py
"""
Event Fetcher for Whale Monitor
Получение событий из блокчейнов
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EventFetcher:
    """
    Получение событий из блокчейнов
    
    Координирует работу с BlockchainMonitor
    """
    
    def __init__(self, components: Dict[str, Any]):
        """
        Инициализация fetcher
        
        Args:
            components: Компоненты системы
        """
        self.components = components
        self.rate_limiter = components.get('rate_limiter')
    
    async def fetch_events(
        self,
        start_time: datetime,
        chains: List[str]
    ) -> List[Any]:
        """
        Получение событий из блокчейнов
        
        Args:
            start_time: Время начала периода
            chains: Список блокчейнов
            
        Returns:
            Список событий
        """
        try:
            from app.whales.monitor import BlockchainMonitor
            
            events = []
            
            async with BlockchainMonitor() as monitor:
                # Подключение rate limiter
                if self.rate_limiter:
                    monitor.rate_limiter = self.rate_limiter
                    logger.debug("🔧 [FETCH] Rate limiter подключен")
                
                # Получение событий
                events = await monitor.fetch_events(start_time, chains=chains)
                
                # Логирование статистики
                self._log_chain_stats(monitor, chains)
            
            return events
        
        except ImportError:
            logger.warning("⚠️  [FETCH] BlockchainMonitor not available")
            return []
        
        except Exception as e:
            logger.error(f"❌ [FETCH] Error fetching events: {e}", exc_info=True)
            return []
    
    def _log_chain_stats(self, monitor: Any, chains: List[str]):
        """Логирование статистики по блокчейнам"""
        try:
            if not hasattr(monitor, 'get_chain_stats'):
                return
            
            stats = monitor.get_chain_stats()
            
            for chain in chains:
                if chain in stats:
                    stat = stats[chain]
                    logger.info(
                        f"🔗 [CHAIN] {chain}: "
                        f"{stat.get('events', 0)} событий, "
                        f"{stat.get('blocks', 0)} блоков"
                    )
        
        except Exception as e:
            logger.debug(f"Error logging chain stats: {e}")
    
    async def cleanup(self):
        """Cleanup fetcher"""
        pass


__all__ = ['EventFetcher']