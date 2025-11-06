# core/components.py
"""
Component loading and initialization
"""

import logging
import traceback
from typing import Optional, Any

from app.config import config

logger = logging.getLogger(__name__)


class ComponentLoader:
    """Загрузка бизнес-логики компонентов"""
    
    @staticmethod
    def load_news_processor() -> Optional[Any]:
        """Загрузка News Processor"""
        if not config.is_feature_enabled('news'):
            logger.info("ℹ️  News Bot disabled in config")
            return None
        
        try:
            logger.info("📰 [NEWS] Загрузка News Processor...")
            from bot.processor import NewsProcessor
            processor = NewsProcessor()
            logger.info("✅ News Processor loaded")
            return processor
        except ImportError as e:
            logger.warning(f"⚠️  News Processor not available (import): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load News Processor: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def load_whale_scheduler() -> Optional[Any]:
        """Загрузка Whale Scheduler"""
        if not config.is_feature_enabled('whale'):
            logger.info("ℹ️  Whale Monitor disabled in config")
            return None
        
        try:
            logger.info("🐋 [WHALE] Загрузка Whale Scheduler...")
            from app.scheduler import scheduler as whale_scheduler
            logger.info("✅ Whale Scheduler loaded")
            return whale_scheduler
        except ImportError as e:
            logger.warning(f"⚠️  Whale Scheduler not available (import): {e}")
            return None
        except AttributeError as e:
            logger.error(f"❌ Config error in Whale Scheduler: {e}")
            logger.error("   Проверьте что все необходимые атрибуты есть в config")
            traceback.print_exc()
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load Whale Scheduler: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def load_bot_application() -> Optional[Any]:
        """Загрузка Bot Application"""
        try:
            logger.info("🤖 [BOT] Загрузка Bot Application...")
            from app.bot import application as bot_application
            logger.info("✅ Bot Commands Handler loaded")
            return bot_application
        except ImportError as e:
            logger.warning(f"⚠️  Bot Commands Handler not available (import): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Bot Commands Handler not loaded: {e}")
            traceback.print_exc()
            return None


class ComponentManager:
    """Управление жизненным циклом компонентов"""
    
    def __init__(self):
        self.news_processor: Optional[Any] = None
        self.whale_scheduler: Optional[Any] = None
        self.bot_application: Optional[Any] = None
        
        self._news_enabled = False
        self._whale_enabled = False
        self._bot_enabled = False
        self._trading_enabled = False
    
    def load_all(self) -> tuple[bool, bool, bool]:
        """
        Загружает все компоненты
        
        Returns:
            (has_news, has_whale, has_bot)
        """
        logger.info("\n" + "="*80)
        logger.info("📦 LOADING COMPONENTS")
        logger.info("="*80)
        
        loader = ComponentLoader()
        
        self.news_processor = loader.load_news_processor()
        self._news_enabled = self.news_processor is not None
        
        self.whale_scheduler = loader.load_whale_scheduler()
        self._whale_enabled = self.whale_scheduler is not None
        
        self.bot_application = loader.load_bot_application()
        self._bot_enabled = self.bot_application is not None
        
        self._check_trading_enabled()
        
        logger.info("\n" + "="*80)
        logger.info("📊 COMPONENT STATUS")
        logger.info("="*80)
        logger.info(f"   News Bot:        {'✅ Loaded' if self._news_enabled else '❌ Not Available'}")
        logger.info(f"   Whale Monitor:   {'✅ Loaded' if self._whale_enabled else '❌ Not Available'}")
        logger.info(f"   Trading System:  {'✅ Enabled' if self._trading_enabled else '❌ Disabled'}")
        logger.info(f"   Bot Commands:    {'✅ Loaded' if self._bot_enabled else '❌ Not Available'}")
        logger.info("="*80 + "\n")
        
        return (
            self._news_enabled,
            self._whale_enabled,
            self._bot_enabled
        )
    
    def _check_trading_enabled(self):
        """Проверяет состояние trading системы"""
        try:
            if config.is_feature_enabled('trading'):
                self._trading_enabled = True
            elif self.whale_scheduler and hasattr(self.whale_scheduler, 'trading_enabled'):
                self._trading_enabled = self.whale_scheduler.trading_enabled
            else:
                self._trading_enabled = False
        except Exception as e:
            logger.warning(f"⚠️  Error checking trading status: {e}")
            self._trading_enabled = False
    
    def has_news(self) -> bool:
        """Проверяет наличие News Bot"""
        return self._news_enabled
    
    def has_whale(self) -> bool:
        """Проверяет наличие Whale Monitor"""
        return self._whale_enabled
    
    def has_bot(self) -> bool:
        """Проверяет наличие Bot Commands"""
        return self._bot_enabled
    
    def has_trading(self) -> bool:
        """Проверяет наличие trading системы"""
        return self._trading_enabled
    
    async def stop_all(self):
        """Останавливает все компоненты"""
        import asyncio
        
        logger.info("🛑 Stopping all components...")
        
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.whale_scheduler.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ Whale Scheduler остановлен")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️  Timeout остановки Whale Scheduler")
            except Exception as e:
                logger.warning(f"   ⚠️  Ошибка остановки Whale Scheduler: {e}")
        
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            try:
                await asyncio.wait_for(
                    self.news_processor.cleanup(),
                    timeout=10.0
                )
                logger.info("   ✓ News Processor остановлен")
            except asyncio.TimeoutError:
                logger.warning("   ⚠️  Timeout остановки News Processor")
            except Exception as e:
                logger.warning(f"   ⚠️  Ошибка остановки News Processor: {e}")
        
        logger.info("✅ All components stopped")