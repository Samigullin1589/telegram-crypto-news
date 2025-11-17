# app/scheduler/monitor_cycle.py
"""
Whale Monitor Cycle Runner
Выполнение циклов мониторинга
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .event_fetcher import EventFetcher
from .event_publisher import EventPublisher
from .monitor_state import MonitorState

logger = logging.getLogger(__name__)


class MonitorCycleRunner:
    """
    Раннер циклов мониторинга
    
    Координирует:
    - Получение событий
    - Обработку и фильтрацию
    - Публикацию
    """
    
    def __init__(self, components: Dict[str, Any], state: MonitorState):
        """
        Инициализация раннера
        
        Args:
            components: Компоненты системы
            state: Состояние монитора
        """
        self.components = components
        self.state = state
        
        # Инициализация подсистем
        self.event_fetcher = EventFetcher(components)
        self.event_publisher = EventPublisher(components)
        
        # Метрики текущего цикла
        self.cycle_metrics = {
            'events_fetched': 0,
            'events_qualified': 0,
            'events_queued': 0,
            'events_published': 0
        }
    
    async def run_cycle(
        self,
        start_time: datetime,
        chains: List[str]
    ) -> Dict[str, Any]:
        """
        Выполнение одного цикла мониторинга
        
        Args:
            start_time: Время начала мониторинга
            chains: Список блокчейнов
            
        Returns:
            Dict с результатами цикла
        """
        cycle_start = datetime.utcnow()
        self._reset_cycle_metrics()
        
        logger.info(
            f"🔄 [CYCLE] Запуск цикла для {len(chains)} chains: {', '.join(chains)}"
        )
        
        try:
            # Этап 1: Получение событий
            events = await self.event_fetcher.fetch_events(start_time, chains)
            self.cycle_metrics['events_fetched'] = len(events)
            
            if not events:
                logger.info("👍 [WHALE] Новых перемещений не найдено")
                return self._create_cycle_result(cycle_start, success=True)
            
            logger.info(f"📥 [FETCH] Получено {len(events)} событий")
            
            # Этап 2: Обработка событий
            qualified_events = await self._process_events(events)
            self.cycle_metrics['events_qualified'] = len(qualified_events)
            
            if not qualified_events:
                logger.info("🚫 [FILTER] Все события отфильтрованы")
                return self._create_cycle_result(cycle_start, success=True)
            
            logger.info(f"✅ [QUALIFY] {len(qualified_events)} событий прошли фильтрацию")
            
            # Этап 3: Публикация
            published_count = await self.event_publisher.publish_events(
                qualified_events
            )
            self.cycle_metrics['events_published'] = published_count
            
            logger.info(f"📢 [PUBLISHED] Опубликовано {published_count} событий")
            
            # Результат
            duration = (datetime.utcnow() - cycle_start).total_seconds()
            return self._create_cycle_result(
                cycle_start,
                success=True,
                duration=duration
            )
        
        except Exception as e:
            logger.error(f"❌ [CYCLE] Ошибка в цикле: {e}", exc_info=True)
            return self._create_cycle_result(
                cycle_start,
                success=False,
                error=str(e)
            )
    
    async def _process_events(self, events: List[Any]) -> List[Any]:
        """
        Обработка и фильтрация событий

        Args:
            events: Сырые события

        Returns:
            Отфильтрованные события
        """
        try:
            # Импорт процессора если доступен
            from .whale_components import EventProcessor, EventFilter, EventEnricher

            # Создаем filter и enricher с правильными компонентами
            event_filter = EventFilter(self.components)
            event_enricher = EventEnricher(self.components)

            event_processor = EventProcessor(self.components, event_filter, event_enricher)
            qualified = await event_processor.process_events(
                events,
                self.state.seen_keys
            )

            return qualified

        except ImportError as e:
            logger.debug(f"EventProcessor not available: {e}, returning all events")
            return events

        except Exception as e:
            logger.error(f"Error processing events: {e}")
            return []
    
    def _reset_cycle_metrics(self):
        """Сброс метрик цикла"""
        self.cycle_metrics = {
            'events_fetched': 0,
            'events_qualified': 0,
            'events_queued': 0,
            'events_published': 0
        }
    
    def _create_cycle_result(
        self,
        cycle_start: datetime,
        success: bool,
        duration: Optional[float] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Создание результата цикла"""
        if duration is None:
            duration = (datetime.utcnow() - cycle_start).total_seconds()
        
        result = {
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            'duration_seconds': round(duration, 2),
            'metrics': self.cycle_metrics.copy()
        }
        
        if error:
            result['error'] = error
        
        return result
    
    async def cleanup(self):
        """Cleanup раннера"""
        logger.debug("🧹 [CYCLE] Cleanup runner...")
        
        try:
            await self.event_fetcher.cleanup()
            await self.event_publisher.cleanup()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")


__all__ = ['MonitorCycleRunner']