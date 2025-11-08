# app/scheduler/whale_monitor.py
"""
Whale Monitoring System - Main Orchestrator
Координирует процесс мониторинга крупных криптовалютных транзакций
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

from app.config import config
from app.whales.monitor import BlockchainMonitor
from app.whales.normalize import WhaleEvent
from .whale_components import (
    EventProcessor,
    EventFilter,
    EventEnricher,
    PublicationManager,
    MetricsCollector,
    ComponentValidator
)

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """
    Главный класс мониторинга крупных криптовалютных перемещений
    Управляет полным циклом: обнаружение → обработка → фильтрация → публикация
    """
    
    def __init__(self, components: Dict):
        """
        Инициализация системы мониторинга
        
        Args:
            components: Словарь с необходимыми компонентами системы
        """
        self.components = components
        
        # Валидация компонентов при старте
        validator = ComponentValidator(components)
        validator.validate_required_components()
        
        # Инициализация подсистем
        self.event_filter = EventFilter(components)
        self.event_enricher = EventEnricher(components)
        self.event_processor = EventProcessor(components, self.event_filter, self.event_enricher)
        self.publication_manager = PublicationManager(components)
        self.metrics = MetricsCollector()
        
        # Состояние системы
        self.seen_keys = components.get('seen_keys', set())
        self.is_healthy = True
        self.last_cycle_time = None
        
        logger.info("🐋 [WHALE] Monitor инициализирован успешно")
        logger.info(f"🐋 [WHALE] Порог: ${config.whale.min_usd_threshold:,.0f}")
        logger.info(f"🐋 [WHALE] Лимит публикаций: {config.whale.posts_per_hour_cap}/час")
    
    async def run_cycle(self, start_time: datetime, chains: List[str]) -> Dict:
        """
        Выполнить один полный цикл мониторинга
        
        Args:
            start_time: Время начала мониторинга
            chains: Список блокчейнов для мониторинга
            
        Returns:
            Dict с результатами цикла
        """
        cycle_start = datetime.utcnow()
        self.metrics.reset_cycle()
        
        logger.info(f"🔄 [CYCLE] Запуск цикла для {len(chains)} chains: {', '.join(chains)}")
        
        try:
            # Этап 1: Получение событий из блокчейнов
            events = await self._fetch_blockchain_events(start_time, chains)
            self.metrics.events_fetched = len(events)
            
            if not events:
                logger.info("👍 [WHALE] Новых перемещений не найдено в блокчейнах")
                return self._create_cycle_result(cycle_start, success=True)
            
            logger.info(f"📥 [FETCH] Получено {len(events)} сырых событий из блокчейнов")
            
            # Этап 2: Обработка и фильтрация событий
            qualified_events = await self.event_processor.process_events(events, self.seen_keys)
            self.metrics.events_qualified = len(qualified_events)
            
            if not qualified_events:
                logger.info("🚫 [FILTER] Все события отфильтрованы")
                self._log_filtering_stats()
                return self._create_cycle_result(cycle_start, success=True)
            
            logger.info(f"✅ [QUALIFY] {len(qualified_events)} событий прошли фильтрацию")
            
            # Этап 3: Подготовка к публикации
            publication_items = await self._prepare_publications(qualified_events)
            self.metrics.events_queued = len(publication_items)
            
            if not publication_items:
                logger.info("📭 [QUEUE] Нет событий для публикации")
                return self._create_cycle_result(cycle_start, success=True)
            
            # Этап 4: Публикация событий
            published_count = await self.publication_manager.publish_batch(publication_items)
            self.metrics.events_published = published_count
            
            logger.info(f"📢 [PUBLISHED] Опубликовано {published_count}/{len(publication_items)} событий")
            
            # Обновление состояния
            self.last_cycle_time = datetime.utcnow()
            cycle_duration = (self.last_cycle_time - cycle_start).total_seconds()
            
            return self._create_cycle_result(
                cycle_start, 
                success=True,
                duration=cycle_duration
            )
        
        except Exception as e:
            logger.error(f"❌ [CYCLE] Критическая ошибка в цикле: {e}", exc_info=True)
            self.is_healthy = False
            return self._create_cycle_result(cycle_start, success=False, error=str(e))
    
    async def _fetch_blockchain_events(
        self, 
        start_time: datetime, 
        chains: List[str]
    ) -> List[WhaleEvent]:
        """
        Получение событий из блокчейнов
        
        Args:
            start_time: Время начала периода мониторинга
            chains: Список блокчейнов
            
        Returns:
            Список обнаруженных событий
        """
        events = []
        
        try:
            async with BlockchainMonitor() as monitor:
                # Передача rate limiter если доступен
                rate_limiter = self.components.get('rate_limiter')
                if rate_limiter:
                    monitor.rate_limiter = rate_limiter
                    logger.debug("🔧 [SETUP] Rate limiter подключен к монитору")
                
                # Получение событий
                events = await monitor.fetch_events(start_time, chains=chains)
                
                # Детальное логирование результатов по каждому chain
                if hasattr(monitor, 'get_chain_stats'):
                    stats = monitor.get_chain_stats()
                    for chain, stat in stats.items():
                        logger.info(
                            f"🔗 [CHAIN] {chain}: {stat.get('events', 0)} событий, "
                            f"{stat.get('blocks', 0)} блоков проверено"
                        )
        
        except Exception as e:
            logger.error(f"❌ [FETCH] Ошибка получения событий: {e}", exc_info=True)
            raise
        
        return events
    
    async def _prepare_publications(self, events: List[WhaleEvent]) -> List[Dict]:
        """
        Подготовка событий к публикации
        
        Args:
            events: Отфильтрованные события
            
        Returns:
            Список элементов для публикации с приоритетами
        """
        publication_items = []
        
        scorer = self.components.get('scorer')
        if not scorer:
            logger.error("❌ [PREPARE] Scorer не доступен")
            return []
        
        for event in events:
            try:
                # Расчет вердикта и уверенности
                verdict, confidence = scorer.calculate_verdict_and_confidence(event)
                
                # Проверка необходимости публикации
                if not scorer.should_publish(event, verdict, confidence):
                    logger.debug(
                        f"⏭️ [SKIP] {event.asset}: verdict={verdict}, "
                        f"confidence={confidence:.2f}"
                    )
                    continue
                
                # Расчет приоритета
                priority = scorer.calculate_priority(event, confidence)
                
                publication_items.append({
                    "event": event,
                    "verdict": verdict,
                    "confidence": confidence,
                    "priority": priority,
                    "queued_at": datetime.utcnow()
                })
                
                logger.debug(
                    f"📋 [QUEUE] {event.asset} ${event.amount_usd:,.0f} - "
                    f"verdict={verdict}, confidence={confidence:.2f}, priority={priority:.2f}"
                )
            
            except Exception as e:
                logger.error(f"⚠️ [PREPARE] Ошибка подготовки {event.asset}: {e}")
                continue
        
        # Сортировка по приоритету
        publication_items.sort(key=lambda x: x["priority"], reverse=True)
        
        return publication_items
    
    def _create_cycle_result(
        self, 
        cycle_start: datetime, 
        success: bool,
        duration: Optional[float] = None,
        error: Optional[str] = None
    ) -> Dict:
        """
        Создание результата цикла
        
        Args:
            cycle_start: Время начала цикла
            success: Успешность выполнения
            duration: Длительность в секундах
            error: Описание ошибки если была
            
        Returns:
            Dict с детальной статистикой цикла
        """
        if duration is None:
            duration = (datetime.utcnow() - cycle_start).total_seconds()
        
        result = {
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            'duration_seconds': round(duration, 2),
            'metrics': {
                'events_fetched': self.metrics.events_fetched,
                'events_qualified': self.metrics.events_qualified,
                'events_queued': self.metrics.events_queued,
                'events_published': self.metrics.events_published,
                'filtering_stats': self.metrics.get_filtering_stats()
            }
        }
        
        if error:
            result['error'] = error
        
        return result
    
    def _log_filtering_stats(self):
        """Вывод детальной статистики фильтрации"""
        stats = self.metrics.get_filtering_stats()
        
        if not stats:
            return
        
        logger.info("📊 [STATS] Причины фильтрации:")
        for reason, count in stats.items():
            logger.info(f"  • {reason}: {count}")
    
    def get_health_status(self) -> Dict:
        """
        Получение статуса здоровья системы
        
        Returns:
            Dict со статусом и метриками
        """
        return {
            'is_healthy': self.is_healthy,
            'last_cycle': self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            'seen_events_count': len(self.seen_keys),
            'publication_queue_size': len(self.publication_manager.get_queue()),
            'recent_publications_count': len(self.publication_manager.get_recent_publications()),
            'metrics': self.metrics.get_summary()
        }