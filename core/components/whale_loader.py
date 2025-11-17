# core/components/whale_loader.py
"""
Whale Scheduler Loader
Загрузчик whale мониторинга
"""

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class WhaleLoader:
    """Загрузчик Whale Scheduler"""
    
    def __init__(self, utils: Any):
        """
        Инициализация loader
        
        Args:
            utils: Утилиты загрузчика
        """
        self.utils = utils
    
    def load(self) -> Optional[Any]:
        """
        Загрузка Whale Scheduler
        
        Returns:
            WhaleMonitor instance или None
        """
        try:
            # Проверка feature flag
            if not self._is_enabled():
                logger.info("ℹ️  [WHALE] Disabled in configuration")
                return None
            
            logger.info("🐋 [WHALE] Loading Whale Monitor...")
            
            # Создание компонентов для WhaleMonitor
            components = self._create_components()
            if not components:
                logger.error("❌ [WHALE] Failed to create components")
                return None
            
            # Создание WhaleMonitor
            monitor = self._create_monitor(components)
            if not monitor:
                return None
            
            # Валидация
            if not self._validate_monitor(monitor):
                logger.error("❌ [WHALE] Monitor validation failed")
                return None
            
            logger.info("✅ [WHALE] Whale Monitor loaded successfully")
            return monitor
        
        except Exception as e:
            logger.error(f"❌ [WHALE] Loading error: {e}", exc_info=True)
            return None
    
    def _is_enabled(self) -> bool:
        """Проверка включен ли whale"""
        try:
            from app.config import config
            return config.is_feature_enabled('whale')
        except Exception as e:
            logger.debug(f"Config check failed: {e}")
            return True  # По умолчанию включен
    
    def _create_components(self) -> Optional[Dict[str, Any]]:
        """
        Создание компонентов для WhaleMonitor

        Returns:
            Dict с компонентами или None
        """
        try:
            components = {}

            # Seen keys для отслеживания событий
            components['seen_keys'] = set()

            # КРИТИЧЕСКИЕ КОМПОНЕНТЫ (required)

            # 1. WhaleScorer
            try:
                from app.whales.score import WhaleScorer
                components['scorer'] = WhaleScorer()
                logger.debug("   ✓ WhaleScorer created")
            except Exception as e:
                logger.error(f"   ❌ WhaleScorer failed: {e}")

            # 2. PriceProvider
            try:
                from app.whales.price import PriceProvider
                components['price_provider'] = PriceProvider()
                logger.debug("   ✓ PriceProvider created")
            except Exception as e:
                logger.error(f"   ❌ PriceProvider failed: {e}")

            # 3. WhalePublisher
            try:
                from app.whales.publisher.core import WhalePublisher
                components['publisher'] = WhalePublisher()
                logger.debug("   ✓ WhalePublisher created")
            except Exception as e:
                logger.error(f"   ❌ WhalePublisher failed: {e}")

            # 4. HistoryManager
            try:
                from app.whales.history.manager import HistoryManager
                components['history_manager'] = HistoryManager()
                logger.debug("   ✓ HistoryManager created")
            except Exception as e:
                logger.error(f"   ❌ HistoryManager failed: {e}")

            # ОПЦИОНАЛЬНЫЕ КОМПОНЕНТЫ

            # Event filter
            try:
                from app.scheduler.whale_components import EventFilter
                # EventFilter нужны components, передаем пустой dict
                components['event_filter'] = EventFilter({})
                logger.debug("   ✓ EventFilter created")
            except Exception as e:
                logger.debug(f"   EventFilter not available: {e}")

            # Event enricher
            try:
                from app.scheduler.whale_components import EventEnricher
                components['event_enricher'] = EventEnricher({})
                logger.debug("   ✓ EventEnricher created")
            except Exception as e:
                logger.debug(f"   EventEnricher not available: {e}")

            logger.debug(f"   Created {len(components)} components")
            return components

        except Exception as e:
            logger.error(f"Error creating components: {e}")
            return None
    
    def _create_monitor(self, components: Dict[str, Any]) -> Optional[Any]:
        """
        Создание WhaleMonitor
        
        Args:
            components: Компоненты для монитора
            
        Returns:
            WhaleMonitor instance или None
        """
        try:
            from app.scheduler.whale_monitor import WhaleMonitor
            
            # Создание с компонентами
            monitor = WhaleMonitor(components=components)
            logger.debug("   ✓ WhaleMonitor instance created")
            
            return monitor
        
        except TypeError as e:
            # Попытка создать без параметров (legacy)
            logger.debug(f"   TypeError with components: {e}")
            try:
                monitor = WhaleMonitor()
                logger.debug("   ✓ WhaleMonitor created without parameters (legacy)")
                return monitor
            except Exception as e2:
                logger.error(f"   Failed legacy creation: {e2}")
                return None
        
        except Exception as e:
            logger.error(f"   Monitor creation error: {e}")
            return None
    
    def _validate_monitor(self, monitor: Any) -> bool:
        """Валидация monitor"""
        required_methods = ['run_cycle', 'get_health_status']
        
        for method in required_methods:
            if not hasattr(monitor, method):
                logger.error(f"   Missing method: {method}")
                return False
        
        return True


__all__ = ['WhaleLoader']