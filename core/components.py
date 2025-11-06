# core/components.py
"""
Component loading and initialization
"""

import logging
import traceback
from typing import Optional, Any

logger = logging.getLogger(__name__)


class ComponentLoader:
    """Загрузка бизнес-логики компонентов"""
    
    @staticmethod
    def load_news_processor() -> Optional[Any]:
        """Загрузка News Processor"""
        try:
            from bot.processor import NewsProcessor
            processor = NewsProcessor()
            logger.info("✅ News Processor loaded")
            return processor
        except ImportError as e:
            logger.warning(f"⚠️  News Processor not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️  Failed to load News Processor: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def load_whale_scheduler() -> Optional[Any]:
        """Загрузка Whale Scheduler"""
        try:
            from app.scheduler import scheduler as whale_scheduler
            logger.info("✅ Whale Scheduler loaded")
            return whale_scheduler
        except ImportError as e:
            logger.warning(f"⚠️  Whale Scheduler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️  Failed to load Whale Scheduler: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def load_bot_application() -> Optional[Any]:
        """Загрузка Bot Application"""
        try:
            from app.bot import application as bot_application
            logger.info("✅ Bot Commands Handler loaded")
            return bot_application
        except ImportError as e:
            logger.warning(f"⚠️  Bot Commands Handler not available: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️  Bot Commands Handler not loaded: {e}")
            traceback.print_exc()
            return None


class ComponentManager:
    """Управление жизненным циклом компонентов"""
    
    def __init__(self):
        self.news_processor: Optional[Any] = None
        self.whale_scheduler: Optional[Any] = None
        self.bot_application: Optional[Any] = None
    
    def load_all(self) -> tuple[bool, bool, bool]:
        """
        Загружает все компоненты
        
        Returns:
            (has_news, has_whale, has_bot)
        """
        loader = ComponentLoader()
        
        self.news_processor = loader.load_news_processor()
        self.whale_scheduler = loader.load_whale_scheduler()
        self.bot_application = loader.load_bot_application()
        
        return (
            self.news_processor is not None,
            self.whale_scheduler is not None,
            self.bot_application is not None
        )
    
    def has_trading(self) -> bool:
        """Проверяет наличие trading системы"""
        return (
            self.whale_scheduler is not None and
            hasattr(self.whale_scheduler, 'trading_enabled') and
            self.whale_scheduler.trading_enabled
        )
    
    async def stop_all(self):
        """Останавливает все компоненты"""
        import asyncio
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.whale_scheduler.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ Whale Scheduler остановлен")
            except Exception as e:
                logger.warning(f"   ⚠️  Ошибка остановки Whale Scheduler: {e}")
        
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.news_processor.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ News Processor остановлен")
            except Exception as e:
                logger.warning(f"   ⚠️  Ошибка остановки News Processor: {e}")