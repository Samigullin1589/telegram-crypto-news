# core/initialization/monitor.py
"""
Monitor Initializer - Инициализация системы мониторинга
"""

from typing import Optional
from core.logging_config import get_logger
from core.monitor import IntegratedCryptoMonitor

logger = get_logger(__name__)


class MonitorInitializer:
    """
    Инициализация системы мониторинга
    
    Создает и настраивает IntegratedCryptoMonitor
    """
    
    def __init__(self):
        """Инициализация"""
        self.monitor: Optional[IntegratedCryptoMonitor] = None
    
    def initialize(self) -> bool:
        """
        Инициализация мониторинга
        
        Returns:
            bool: True если успешно
        """
        try:
            self.monitor = IntegratedCryptoMonitor()
            logger.info("✅ Monitor initialized")
            return True
        
        except Exception as e:
            logger.error(f"❌ Monitor initialization error: {e}", exc_info=True)
            return False
    
    def get_monitor(self) -> Optional[IntegratedCryptoMonitor]:
        """
        Получение инициализированного монитора
        
        Returns:
            Optional[IntegratedCryptoMonitor]: Monitor или None
        """
        return self.monitor