# core/components/trading_loader.py
"""
Trading System Loader
Загрузчик торговой системы
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class TradingLoader:
    """Загрузчик Trading System"""
    
    def __init__(self, utils: Any):
        """
        Инициализация loader
        
        Args:
            utils: Утилиты загрузчика
        """
        self.utils = utils
    
    def load(self) -> Optional[Any]:
        """
        Загрузка Trading System
        
        Returns:
            TradingSystem instance или None
        """
        try:
            # Проверка feature flag
            if not self._is_enabled():
                logger.info("ℹ️  [TRADING] Disabled in configuration")
                return None
            
            logger.info("📈 [TRADING] Loading Trading System...")
            
            # Создание системы
            trading = self._create_system()
            if not trading:
                return None
            
            # Проверка инициализации
            if not self._check_initialization(trading):
                logger.warning("⚠️  [TRADING] System not fully initialized")
                return None
            
            # Валидация
            if not self._validate_system(trading):
                logger.error("❌ [TRADING] System validation failed")
                return None
            
            logger.info("✅ [TRADING] Trading System loaded successfully")
            return trading
        
        except Exception as e:
            logger.error(f"❌ [TRADING] Loading error: {e}", exc_info=True)
            return None
    
    def _is_enabled(self) -> bool:
        """Проверка включен ли trading"""
        try:
            from app.config import config
            return config.is_feature_enabled('trading')
        except Exception as e:
            logger.debug(f"Config check failed: {e}")
            return False  # По умолчанию выключен
    
    def _create_system(self) -> Optional[Any]:
        """
        Создание Trading System
        
        Returns:
            TradingSystem instance или None
        """
        try:
            from app.trading_system import TradingSystem
            
            trading = TradingSystem()
            logger.debug("   ✓ TradingSystem instance created")
            
            return trading
        
        except ImportError as e:
            logger.warning(f"   TradingSystem not available: {e}")
            return None
        
        except Exception as e:
            logger.error(f"   Creation error: {e}", exc_info=True)
            return None
    
    def _check_initialization(self, trading: Any) -> bool:
        """
        Проверка инициализации системы
        
        Args:
            trading: Trading system
            
        Returns:
            True если инициализирована
        """
        try:
            # Проверка метода is_enabled
            if hasattr(trading, 'is_enabled'):
                enabled = trading.is_enabled()
                
                if not enabled:
                    logger.info("   Trading system is disabled (dry_run or config)")
                    return False
                
                logger.debug("   ✓ System is enabled")
                return True
            
            # Fallback: проверка атрибута enabled
            if hasattr(trading, 'enabled'):
                return bool(trading.enabled)
            
            # Если нет методов проверки, считаем что ОК
            return True
        
        except Exception as e:
            logger.error(f"   Initialization check error: {e}")
            return False
    
    def _validate_system(self, trading: Any) -> bool:
        """Валидация trading system"""
        required_methods = ['is_enabled', 'get_status']
        
        for method in required_methods:
            if not hasattr(trading, method):
                logger.debug(f"   Missing optional method: {method}")
        
        # Проверка хотя бы базовых атрибутов
        if not hasattr(trading, 'enabled') and not hasattr(trading, 'is_enabled'):
            logger.error("   Missing enabled attribute/method")
            return False
        
        return True


__all__ = ['TradingLoader']