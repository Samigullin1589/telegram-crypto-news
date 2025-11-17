# core/components/hyperliquid_loader.py
"""
Hyperliquid System Loader
Загрузчик системы мониторинга Hyperliquid DEX
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class HyperliquidLoader:
    """
    Loader для Hyperliquid System

    Отвечает за:
    - Проверку доступности модуля
    - Проверку enabled флага
    - Создание экземпляра HyperliquidSystem
    - Передачу необходимых компонентов
    """

    def __init__(self):
        """Инициализация loader"""
        self.system: Optional[Any] = None

    def load(self) -> Optional[Any]:
        """
        Загрузка Hyperliquid System

        Returns:
            HyperliquidSystem instance или None при ошибке
        """
        logger.info("🌊 [HYPERLIQUID] Loading Hyperliquid System...")

        try:
            # Проверка конфигурации
            from app.config import config

            if not config.is_feature_enabled('hyperliquid'):
                logger.info("   Hyperliquid disabled in features")
                return None

            # Проверка доступности модуля
            try:
                from app.exchanges import HYPERLIQUID_AVAILABLE
                if not HYPERLIQUID_AVAILABLE:
                    logger.warning("   Hyperliquid module not available")
                    return None
            except ImportError:
                logger.warning("   Hyperliquid module not available (import error)")
                return None

            # Создание компонентов для HyperliquidSystem
            components = self._prepare_components()

            # Импорт и создание
            from app.scheduler.hyperliquid import HyperliquidSystem

            self.system = HyperliquidSystem(components)

            if not self.system.enabled:
                logger.warning("   Hyperliquid system initialized but disabled")
                return None

            logger.info("✅ [HYPERLIQUID] Hyperliquid System loaded successfully")
            return self.system

        except Exception as e:
            logger.error(f"   System creation error: {e}", exc_info=True)
            return None

    def _prepare_components(self) -> dict:
        """
        Подготовка компонентов для HyperliquidSystem

        HyperliquidSystem ожидает:
        - publisher: WhalePublisher для отправки уведомлений

        Returns:
            Dict с компонентами
        """
        components = {}

        try:
            # Загружаем publisher для отправки уведомлений
            from app.whales.publish import WhalePublisher
            components['publisher'] = WhalePublisher()
            logger.debug("   Publisher loaded for Hyperliquid")
        except Exception as e:
            logger.warning(f"   Cannot load publisher: {e}")
            components['publisher'] = None

        return components


__all__ = ['HyperliquidLoader']
