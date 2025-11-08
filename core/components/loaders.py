# core/components/loaders.py
"""
Component Loaders v2.0 - Main Entry Point
Центральная точка загрузки всех компонентов системы
"""

import logging
from typing import Optional, Any, Dict

from .news_loader import NewsLoader
from .whale_loader import WhaleLoader
from .trading_loader import TradingLoader
from .bot_loader import BotLoader
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
    """
    
    def __init__(self):
        """Инициализация загрузчика"""
        self.utils = LoaderUtils()
        self.news_loader = NewsLoader(self.utils)
        self.whale_loader = WhaleLoader(self.utils)
        self.trading_loader = TradingLoader(self.utils)
        self.bot_loader = BotLoader(self.utils)
    
    def load_news_processor(self) -> Optional[Any]:
        """
        Загрузка News Processor
        
        Returns:
            NewsProcessor instance или None
        """
        return self.news_loader.load()
    
    def load_whale_scheduler(self) -> Optional[Any]:
        """
        Загрузка Whale Scheduler
        
        Returns:
            WhaleMonitor instance или None
        """
        return self.whale_loader.load()
    
    def load_bot_application(self) -> Optional[Any]:
        """
        Загрузка Bot Application
        
        Returns:
            Application instance или None
        """
        return self.bot_loader.load()
    
    def load_trading_system(self) -> Optional[Any]:
        """
        Загрузка Trading System
        
        Returns:
            TradingSystem instance или None
        """
        return self.trading_loader.load()
    
    def load_all_components(self) -> Dict[str, Any]:
        """
        Загрузка всех компонентов
        
        Returns:
            Dict с загруженными компонентами
        """
        logger.info("\n" + "="*80)
        logger.info("📦 ЗАГРУЗКА КОМПОНЕНТОВ СИСТЕМЫ")
        logger.info("="*80)
        
        components = {
            'news_processor': self.load_news_processor(),
            'whale_scheduler': self.load_whale_scheduler(),
            'bot_application': self.load_bot_application(),
            'trading_system': self.load_trading_system()
        }
        
        # Подсчет успешно загруженных
        loaded = sum(1 for c in components.values() if c is not None)
        total = len(components)
        
        logger.info("="*80)
        logger.info(f"✅ Загружено {loaded}/{total} компонентов")
        logger.info("="*80 + "\n")
        
        return components


__all__ = ['ComponentLoader']