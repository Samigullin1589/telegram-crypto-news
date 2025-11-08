# core/components/loaders.py
"""
Component Loaders
Загрузчики бизнес-компонентов приложения
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ComponentLoader:
    """
    Загрузчик бизнес-компонентов приложения
    
    Отвечает за безопасную загрузку модулей с обработкой ошибок
    и логированием процесса
    """
    
    @staticmethod
    def load_news_processor() -> Optional[Any]:
        """
        Загрузка News Processor
        
        Returns:
            NewsProcessor instance или None
        """
        try:
            from app.config import config
            
            if not config.is_feature_enabled('news'):
                logger.info("ℹ️  [LOADER] News Bot отключен в конфигурации")
                return None
            
            logger.info("📰 [LOADER] Загрузка News Processor...")
            
            try:
                from bot.news.processor import NewsProcessor
                processor = NewsProcessor()
            except ImportError:
                logger.debug("   Попытка импорта из bot.processor")
                from bot.processor import NewsProcessor
                processor = NewsProcessor()
            
            logger.info("✅ [LOADER] News Processor успешно загружен")
            return processor
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] News Processor недоступен: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки News Processor: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None
    
    @staticmethod
    def load_whale_scheduler() -> Optional[Any]:
        """
        Загрузка Whale Scheduler
        
        Returns:
            Scheduler instance или None
        """
        try:
            from app.config import config
            
            if not config.is_feature_enabled('whale'):
                logger.info("ℹ️  [LOADER] Whale Monitor отключен в конфигурации")
                return None
            
            logger.info("🐋 [LOADER] Загрузка Whale Scheduler...")
            
            try:
                from app.scheduler.whale_monitor import WhaleMonitor
                scheduler = WhaleMonitor()
            except (ImportError, AttributeError):
                logger.debug("   Попытка импорта scheduler из app.scheduler")
                from app.scheduler import scheduler
                return scheduler
            
            logger.info("✅ [LOADER] Whale Scheduler успешно загружен")
            return scheduler
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Whale Scheduler недоступен: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки Whale Scheduler: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None
    
    @staticmethod
    def load_bot_application() -> Optional[Any]:
        """
        Загрузка Bot Application
        
        Returns:
            Application instance или None
        """
        try:
            logger.info("🤖 [LOADER] Загрузка Bot Application...")
            
            from app.bot import application as bot_application
            
            if bot_application is None:
                logger.warning("⚠️  [LOADER] Bot Application не инициализирован")
                return None
            
            logger.info("✅ [LOADER] Bot Application успешно загружен")
            return bot_application
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Bot Application недоступен: {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки Bot Application: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None
    
    @staticmethod
    def load_trading_system() -> Optional[Any]:
        """
        Загрузка Trading System
        
        Returns:
            TradingSystem instance или None
        """
        try:
            from app.config import config
            
            if not config.is_feature_enabled('trading'):
                logger.debug("ℹ️  [LOADER] Trading System отключен")
                return None
            
            logger.info("📈 [LOADER] Загрузка Trading System...")
            
            from app.trading_system import TradingSystem
            trading = TradingSystem()
            
            logger.info("✅ [LOADER] Trading System успешно загружен")
            return trading
            
        except ImportError:
            logger.debug("   Trading System недоступен")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️  [LOADER] Ошибка Trading System: {e}")
            return None