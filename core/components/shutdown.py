# core/components/shutdown.py
"""
Component Shutdown Management
Корректное завершение работы компонентов
"""

import logging
import asyncio
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ComponentShutdown:
    """
    Менеджер корректного завершения работы компонентов
    
    Отвечает за:
    - Последовательную остановку компонентов
    - Таймауты остановки
    - Обработку ошибок при остановке
    """
    
    def __init__(self, timeout: float = 10.0):
        """
        Инициализация менеджера завершения
        
        Args:
            timeout: Таймаут остановки каждого компонента в секундах
        """
        self.timeout = timeout
    
    async def stop_all(
        self,
        whale_scheduler: Optional[Any] = None,
        news_processor: Optional[Any] = None,
        bot_application: Optional[Any] = None,
        trading_system: Optional[Any] = None
    ) -> None:
        """
        Корректно останавливает все активные компоненты
        
        Порядок остановки:
        1. Trading System (если есть)
        2. Whale Scheduler
        3. News Processor
        4. Bot Application
        
        Args:
            whale_scheduler: Экземпляр whale scheduler
            news_processor: Экземпляр news processor
            bot_application: Экземпляр bot application
            trading_system: Экземпляр trading system
        """
        logger.info("\n" + "="*80)
        logger.info("🛑 STOPPING ALL COMPONENTS")
        logger.info("="*80)
        
        # Список компонентов для остановки в правильном порядке
        components_to_stop = [
            (trading_system, "Trading System", "cleanup"),
            (whale_scheduler, "Whale Scheduler", "cleanup"),
            (news_processor, "News Processor", "cleanup"),
            (bot_application, "Bot Application", "stop")
        ]
        
        # Остановка каждого компонента
        for component, name, method in components_to_stop:
            if component:
                await self._stop_component(
                    component=component,
                    name=name,
                    cleanup_method=method
                )
        
        logger.info("✅ Все компоненты остановлены")
        logger.info("="*80 + "\n")
    
    async def _stop_component(
        self,
        component: Any,
        name: str,
        cleanup_method: str
    ) -> None:
        """
        Останавливает отдельный компонент с таймаутом
        
        Args:
            component: Экземпляр компонента
            name: Название компонента для логов
            cleanup_method: Название метода для вызова (cleanup/stop)
        """
        try:
            logger.info(f"   Остановка {name}...")
            
            # Проверка наличия метода
            if not hasattr(component, cleanup_method):
                logger.warning(
                    f"   ⚠️  {name} не имеет метода {cleanup_method}, пропуск"
                )
                return
            
            # Получение метода
            cleanup_func = getattr(component, cleanup_method)
            
            # Вызов с таймаутом
            await asyncio.wait_for(
                cleanup_func(),
                timeout=self.timeout
            )
            
            logger.info(f"   ✓ {name} успешно остановлен")
            
        except asyncio.TimeoutError:
            logger.warning(
                f"   ⚠️  Timeout остановки {name} ({self.timeout}s)"
            )
            
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка остановки {name}: {e}")
            logger.debug("Traceback:", exc_info=True)
    
    async def stop_component_safe(
        self,
        component: Any,
        name: str,
        cleanup_method: str = "cleanup"
    ) -> bool:
        """
        Безопасная остановка одного компонента
        
        Args:
            component: Экземпляр компонента
            name: Название компонента
            cleanup_method: Метод для вызова
            
        Returns:
            True если остановка успешна
        """
        try:
            await self._stop_component(component, name, cleanup_method)
            return True
        except Exception as e:
            logger.error(f"Критическая ошибка остановки {name}: {e}")
            return False