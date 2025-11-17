# core/components/loaders.py
"""
Component Loaders v2.0 - Main Entry Point
Центральная точка загрузки всех компонентов системы

ИСПРАВЛЕНО: Все импорты подлоадеров сделаны ленивыми (lazy)
для избежания циклических зависимостей при инициализации модуля
"""

import logging
from typing import Optional, Any, Dict

from .loader_utils import LoaderUtils

logger = logging.getLogger(__name__)


class ComponentLoader:
    """
    Центральный загрузчик компонентов
    
    Улучшения v2.0:
    - Модульная архитектура
    - Proper dependency injection
    - Comprehensive error handling
    - Validation после загрузки
    - LAZY IMPORTS для избежания циклических зависимостей
    
    Архитектурное решение:
    Все специализированные загрузчики (NewsLoader, WhaleLoader, etc.)
    импортируются лениво через @property для разрыва циклических зависимостей.
    Это позволяет core.monitor импортировать ComponentManager без риска
    циклического импорта через подмодули компонентов.
    """
    
    def __init__(self):
        """
        Инициализация загрузчика
        
        КРИТИЧЕСКИ ВАЖНО: Подлоадеры НЕ импортируются здесь!
        Они будут импортированы ленивым способом при первом обращении.
        """
        self.utils = LoaderUtils()
        
        # ИСПРАВЛЕНО: Подлоадеры не импортируются на уровне модуля
        # Они будут импортированы ленивым способом при первом использовании
        self._news_loader = None
        self._whale_loader = None
        self._trading_loader = None
        self._bot_loader = None
        self._hyperliquid_loader = None
    
    @property
    def news_loader(self):
        """
        Ленивая загрузка NewsLoader
        
        Импортирует NewsLoader только при первом обращении.
        Это предотвращает циклические зависимости при инициализации модуля.
        
        Returns:
            NewsLoader instance
        """
        if self._news_loader is None:
            # ИСПРАВЛЕНО: Импорт только когда нужен
            from .news_loader import NewsLoader
            self._news_loader = NewsLoader(self.utils)
        return self._news_loader
    
    @property
    def whale_loader(self):
        """
        Ленивая загрузка WhaleLoader
        
        Импортирует WhaleLoader только при первом обращении.
        Это предотвращает циклические зависимости при инициализации модуля.
        
        Returns:
            WhaleLoader instance
        """
        if self._whale_loader is None:
            # ИСПРАВЛЕНО: Импорт только когда нужен
            from .whale_loader import WhaleLoader
            self._whale_loader = WhaleLoader(self.utils)
        return self._whale_loader
    
    @property
    def trading_loader(self):
        """
        Ленивая загрузка TradingLoader
        
        Импортирует TradingLoader только при первом обращении.
        Это предотвращает циклические зависимости при инициализации модуля.
        
        Returns:
            TradingLoader instance
        """
        if self._trading_loader is None:
            # ИСПРАВЛЕНО: Импорт только когда нужен
            from .trading_loader import TradingLoader
            self._trading_loader = TradingLoader(self.utils)
        return self._trading_loader
    
    @property
    def bot_loader(self):
        """
        Ленивая загрузка BotLoader

        Импортирует BotLoader только при первом обращении.
        Это предотвращает циклические зависимости при инициализации модуля.

        Returns:
            BotLoader instance
        """
        if self._bot_loader is None:
            # ИСПРАВЛЕНО: Импорт только когда нужен
            from .bot_loader import BotLoader
            self._bot_loader = BotLoader(self.utils)
        return self._bot_loader

    @property
    def hyperliquid_loader(self):
        """
        Ленивая загрузка HyperliquidLoader

        Импортирует HyperliquidLoader только при первом обращении.
        Это предотвращает циклические зависимости при инициализации модуля.

        Returns:
            HyperliquidLoader instance
        """
        if self._hyperliquid_loader is None:
            # Импорт только когда нужен
            from .hyperliquid_loader import HyperliquidLoader
            self._hyperliquid_loader = HyperliquidLoader()
        return self._hyperliquid_loader
    
    def load_news_processor(self) -> Optional[Any]:
        """
        Загрузка News Processor
        
        Использует ленивый импорт NewsLoader для загрузки компонента.
        Включает comprehensive error handling.
        
        Returns:
            NewsProcessor instance или None при ошибке
        """
        try:
            logger.debug("Loading news processor...")
            result = self.news_loader.load()
            
            if result is not None:
                logger.info("✅ News processor loaded successfully")
            else:
                logger.warning("⚠️  News processor not loaded (disabled or error)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to load news processor: {e}", exc_info=True)
            return None
    
    def load_whale_scheduler(self) -> Optional[Any]:
        """
        Загрузка Whale Scheduler
        
        Использует ленивый импорт WhaleLoader для загрузки компонента.
        Включает comprehensive error handling.
        
        Returns:
            WhaleMonitor instance или None при ошибке
        """
        try:
            logger.debug("Loading whale scheduler...")
            result = self.whale_loader.load()
            
            if result is not None:
                logger.info("✅ Whale scheduler loaded successfully")
            else:
                logger.warning("⚠️  Whale scheduler not loaded (disabled or error)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to load whale scheduler: {e}", exc_info=True)
            return None
    
    def load_bot_application(self) -> Optional[Any]:
        """
        Загрузка Bot Application
        
        Использует ленивый импорт BotLoader для загрузки компонента.
        Включает comprehensive error handling.
        
        Returns:
            Application instance или None при ошибке
        """
        try:
            logger.debug("Loading bot application...")
            result = self.bot_loader.load()
            
            if result is not None:
                logger.info("✅ Bot application loaded successfully")
            else:
                logger.warning("⚠️  Bot application not loaded (disabled or error)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to load bot application: {e}", exc_info=True)
            return None
    
    def load_trading_system(self) -> Optional[Any]:
        """
        Загрузка Trading System

        Использует ленивый импорт TradingLoader для загрузки компонента.
        Включает comprehensive error handling.

        Returns:
            TradingSystem instance или None при ошибке
        """
        try:
            logger.debug("Loading trading system...")
            result = self.trading_loader.load()

            if result is not None:
                logger.info("✅ Trading system loaded successfully")
            else:
                logger.warning("⚠️  Trading system not loaded (disabled or error)")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to load trading system: {e}", exc_info=True)
            return None

    def load_hyperliquid_system(self) -> Optional[Any]:
        """
        Загрузка Hyperliquid System

        Использует ленивый импорт HyperliquidLoader для загрузки компонента.
        Включает comprehensive error handling.

        Returns:
            HyperliquidSystem instance или None при ошибке
        """
        try:
            logger.debug("Loading hyperliquid system...")
            result = self.hyperliquid_loader.load()

            if result is not None:
                logger.info("✅ Hyperliquid system loaded successfully")
            else:
                logger.warning("⚠️  Hyperliquid system not loaded (disabled or error)")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to load hyperliquid system: {e}", exc_info=True)
            return None
    
    def load_all_components(self) -> Dict[str, Any]:
        """
        Загрузка всех компонентов системы

        Последовательно загружает все компоненты с полным error handling
        и детальным логированием процесса.

        Returns:
            Dict с загруженными компонентами:
            {
                'news_processor': NewsProcessor или None,
                'whale_scheduler': WhaleMonitor или None,
                'bot_application': Application или None,
                'trading_system': TradingSystem или None,
                'hyperliquid_system': HyperliquidSystem или None
            }
        """
        logger.info("\n" + "="*80)
        logger.info("📦 ЗАГРУЗКА КОМПОНЕНТОВ СИСТЕМЫ")
        logger.info("="*80)

        # Загружаем все компоненты
        components = {
            'news_processor': self.load_news_processor(),
            'whale_scheduler': self.load_whale_scheduler(),
            'bot_application': self.load_bot_application(),
            'trading_system': self.load_trading_system(),
            'hyperliquid_system': self.load_hyperliquid_system()
        }
        
        # Подсчет успешно загруженных
        loaded = sum(1 for c in components.values() if c is not None)
        total = len(components)
        
        # Итоговая статистика
        logger.info("="*80)
        if loaded == total:
            logger.info(f"✅ Все компоненты загружены успешно: {loaded}/{total}")
        elif loaded > 0:
            logger.warning(f"⚠️  Частичная загрузка: {loaded}/{total} компонентов")
        else:
            logger.error(f"❌ Ни один компонент не загружен: {loaded}/{total}")
        
        logger.info("="*80 + "\n")
        
        return components
    
    def get_load_status(self) -> Dict[str, bool]:
        """
        Получение статуса загрузки всех загрузчиков

        Returns:
            Dict с флагами инициализации загрузчиков
        """
        return {
            'news_loader_initialized': self._news_loader is not None,
            'whale_loader_initialized': self._whale_loader is not None,
            'trading_loader_initialized': self._trading_loader is not None,
            'bot_loader_initialized': self._bot_loader is not None,
            'hyperliquid_loader_initialized': self._hyperliquid_loader is not None
        }


__all__ = ['ComponentLoader']