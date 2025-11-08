# core/components/manager.py
"""
Component Manager
Главный менеджер жизненного цикла компонентов
"""

import logging
from typing import Optional, Any, Tuple, Dict
from threading import Lock

from .loaders import ComponentLoader
from .status import ComponentStatusManager
from .shutdown import ComponentShutdownManager

logger = logging.getLogger(__name__)


class ComponentManager:
    """
    Менеджер жизненного цикла компонентов (Thread-safe Singleton)
    """
    
    _instance: Optional['ComponentManager'] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> 'ComponentManager':
        """Thread-safe Singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация менеджера компонентов"""
        if self._initialized:
            return
        
        self.news_processor: Optional[Any] = None
        self.whale_scheduler: Optional[Any] = None
        self.bot_application: Optional[Any] = None
        self.trading_system: Optional[Any] = None
        
        self._loader = ComponentLoader()
        self._status = ComponentStatusManager()
        self._shutdown_manager = ComponentShutdownManager(timeout=10.0)
        
        self._initialized = True
        logger.debug("ComponentManager initialized")
    
    def load_all(self) -> Tuple[bool, bool, bool, bool]:
        """
        Загружает все компоненты приложения
        
        Returns:
            Tuple[news_ok, whale_ok, bot_ok, trading_ok]
        """
        logger.info("\n" + "="*80)
        logger.info("📦 LOADING APPLICATION COMPONENTS")
        logger.info("="*80)
        
        news_ok = self._load_component('news_processor', self._loader.load_news_processor)
        whale_ok = self._load_component('whale_scheduler', self._loader.load_whale_scheduler)
        bot_ok = self._load_component('bot_application', self._loader.load_bot_application)
        trading_ok = self._load_component('trading_system', self._loader.load_trading_system)
        
        self._status.print_status()
        
        return (news_ok, whale_ok, bot_ok, trading_ok)
    
    def _load_component(self, component_name: str, loader_func: callable) -> bool:
        """Универсальный метод загрузки компонента"""
        try:
            instance = loader_func()
            setattr(self, component_name, instance)
            
            self._status.update(
                name=component_name,
                enabled=instance is not None,
                instance=instance,
                error=None
            )
            
            return instance is not None
            
        except Exception as e:
            logger.error(f"Критическая ошибка загрузки {component_name}: {e}")
            setattr(self, component_name, None)
            self._status.update(
                name=component_name,
                enabled=False,
                instance=None,
                error=str(e)
            )
            return False
    
    def has_news(self) -> bool:
        """Проверяет доступность News Bot"""
        return self._status.is_available('news_processor')
    
    def has_whale(self) -> bool:
        """Проверяет доступность Whale Monitor"""
        return self._status.is_available('whale_scheduler')
    
    def has_bot(self) -> bool:
        """Проверяет доступность Bot Commands"""
        return self._status.is_available('bot_application')
    
    def has_trading(self) -> bool:
        """Проверяет доступность Trading System"""
        return self._status.is_available('trading_system')
    
    def get_active_components_count(self) -> int:
        """Возвращает количество активных компонентов"""
        return self._status.active_count()
    
    def is_any_component_active(self) -> bool:
        """Проверяет есть ли хотя бы один активный компонент"""
        return self._status.has_any_active()
    
    def get_status_dict(self) -> dict:
        """Возвращает статус всех компонентов в виде словаря"""
        return {
            **self._status.to_dict(),
            'total_active': self.get_active_components_count()
        }
    
    async def stop_all(self) -> None:
        """Корректно останавливает все активные компоненты"""
        components = {
            'news_processor': self.news_processor,
            'whale_scheduler': self.whale_scheduler,
            'bot_application': self.bot_application,
            'trading_system': self.trading_system
        }
        await self._shutdown_manager.stop_all(components)