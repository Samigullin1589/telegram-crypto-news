# core/components/shutdown.py
"""
Component Shutdown Management
Корректное завершение работы компонентов
"""

import logging
import asyncio
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


class ComponentShutdownManager:
    """Менеджер корректного завершения работы компонентов"""
    
    def __init__(self, timeout: float = 10.0):
        """
        Args:
            timeout: Таймаут остановки каждого компонента в секундах
        """
        self.timeout = timeout
    
    async def stop_all(self, components: Dict[str, Optional[Any]]) -> None:
        """
        Корректно останавливает все активные компоненты
        
        Args:
            components: Словарь с компонентами для остановки
        """
        logger.info("\n" + "="*80)
        logger.info("🛑 STOPPING ALL COMPONENTS")
        logger.info("="*80)
        
        stop_order = [
            ('trading_system', 'Trading System', 'cleanup'),
            ('whale_scheduler', 'Whale Scheduler', 'cleanup'),
            ('news_processor', 'News Processor', 'cleanup'),
            ('bot_application', 'Bot Application', 'stop')
        ]
        
        for key, name, method in stop_order:
            component = components.get(key)
            if component:
                await self._stop_component(component, name, method)
        
        logger.info("✅ Все компоненты остановлены")
        logger.info("="*80 + "\n")
    
    async def _stop_component(
        self,
        component: Any,
        name: str,
        cleanup_method: str
    ) -> None:
        """Останавливает отдельный компонент"""
        try:
            logger.info(f"   Остановка {name}...")
            
            if not hasattr(component, cleanup_method):
                logger.debug(f"   {name} не имеет метода {cleanup_method}")
                return
            
            cleanup_func = getattr(component, cleanup_method)
            await asyncio.wait_for(cleanup_func(), timeout=self.timeout)
            
            logger.info(f"   ✓ {name} успешно остановлен")
            
        except asyncio.TimeoutError:
            logger.warning(f"   ⚠️  Timeout остановки {name} ({self.timeout}s)")
            
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка остановки {name}: {e}")