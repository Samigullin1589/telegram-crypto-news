# core/components/news_loader.py
"""
News Processor Loader
Загрузчик новостного процессора
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class NewsLoader:
    """Загрузчик News Processor"""
    
    def __init__(self, utils: Any):
        """
        Инициализация loader
        
        Args:
            utils: Утилиты загрузчика
        """
        self.utils = utils
    
    def load(self) -> Optional[Any]:
        """
        Загрузка News Processor
        
        Returns:
            NewsProcessor instance или None
        """
        try:
            # Проверка feature flag
            if not self._is_enabled():
                logger.info("ℹ️  [NEWS] Disabled in configuration")
                return None
            
            logger.info("📰 [NEWS] Loading News Processor...")
            
            # Попытка загрузки из нового модуля
            processor = self._try_new_module()
            if processor:
                return self._validate_and_return(processor)
            
            # Fallback на старый модуль
            processor = self._try_legacy_module()
            if processor:
                return self._validate_and_return(processor)
            
            logger.warning("⚠️  [NEWS] Could not load from any module")
            return None
        
        except Exception as e:
            logger.error(f"❌ [NEWS] Loading error: {e}", exc_info=True)
            return None
    
    def _is_enabled(self) -> bool:
        """Проверка включен ли news"""
        try:
            from app.config import config
            return config.is_feature_enabled('news')
        except Exception as e:
            logger.debug(f"Config check failed: {e}")
            return True  # По умолчанию включен
    
    def _try_new_module(self) -> Optional[Any]:
        """Попытка загрузки из нового модуля"""
        try:
            from bot.news.processor import NewsProcessor
            processor = NewsProcessor()
            logger.debug("   ✓ Loaded from bot.news.processor")
            return processor
        except (ImportError, AttributeError) as e:
            logger.debug(f"   New module not available: {e}")
            return None
    
    def _try_legacy_module(self) -> Optional[Any]:
        """Попытка загрузки из legacy модуля"""
        try:
            from bot.processor import NewsProcessor
            processor = NewsProcessor()
            logger.debug("   ✓ Loaded from bot.processor (legacy)")
            return processor
        except (ImportError, AttributeError) as e:
            logger.debug(f"   Legacy module not available: {e}")
            return None
    
    def _validate_and_return(self, processor: Any) -> Optional[Any]:
        """
        Валидация processor
        
        Args:
            processor: Processor для валидации
            
        Returns:
            Processor если валиден, иначе None
        """
        if not self._validate_processor(processor):
            logger.error("❌ [NEWS] Processor validation failed")
            return None
        
        logger.info("✅ [NEWS] News Processor loaded successfully")
        return processor
    
    def _validate_processor(self, processor: Any) -> bool:
        """Валидация processor"""
        cycle_method = getattr(processor, 'run_cycle', None)
        if not callable(cycle_method):
            logger.error("   Missing callable method: run_cycle")
            return False

        return bool(getattr(processor, 'is_initialized', True))


__all__ = ['NewsLoader']