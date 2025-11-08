# core/components/manager.py
"""
Component Manager
Главный менеджер жизненного цикла компонентов
"""

import logging
from typing import Optional, Any, Tuple
from threading import Lock

from .loaders import ComponentLoader
from .status import ComponentStatus
from .shutdown import ComponentShutdown

logger = logging.getLogger(__name__)


class ComponentManager:
    """
    Менеджер жизненного цикла компонентов (Singleton)
    
    Управляет:
    - Загрузкой компонентов при старте
    - Проверкой статуса компонентов
    - Корректным завершением работы компонентов
    
    Thread-safe singleton implementation
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
        
        # Компоненты приложения
        self.news_processor: Optional[Any] = None
        self.whale_scheduler: Optional[Any] = None
        self.bot_application: Optional[Any] = None
        self.trading_system: Optional[Any] = None
        
        # Менеджеры
        self._status = ComponentStatus()
        self._shutdown = ComponentShutdown(timeout=10.0)
        self._loader = ComponentLoader()
        
        self._initialized = True
        
        logger.debug("ComponentManager initialized")
    
    # ========================================================================
    # Загрузка компонентов
    # ========================================================================
    
    def load_all(self) -> Tuple[bool, bool, bool, bool]:
        """
        Загружает все компоненты приложения
        
        Процесс загрузки:
        1. News Processor (если включен в конфигурации)
        2. Whale Scheduler (если включен в конфигурации)
        3. Bot Application (всегда пытается загрузить)
        4. Trading System (если включен в конфигурации)
        
        Returns:
            Tuple[news_ok, whale_ok, bot_ok, trading_ok]
        """
        self._print_loading_header()
        
        # Загрузка News Processor
        news_ok = self._load_news_processor()
        
        # Загрузка Whale Scheduler
        whale_ok = self._load_whale_scheduler()
        
        # Загрузка Bot Application
        bot_ok = self._load_bot_application()
        
        # Загрузка Trading System
        trading_ok = self._load_trading_system()
        
        # Вывод итогового статуса
        self._status.print_status()
        
        return (news_ok, whale_ok, bot_ok, trading_ok)
    
    def _load_news_processor(self) -> bool:
        """
        Загрузка News Processor
        
        Returns:
            True если загрузка успешна
        """
        try:
            self.news_processor = self._loader.load_news_processor()
            
            self._status.update_component(
                name='news_processor',
                enabled=self.news_processor is not None,
                instance=self.news_processor,
                error=None
            )
            
            return self.news_processor is not None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки news_processor: {e}")
            self._status.update_component(
                name='news_processor',
                enabled=False,
                instance=None,
                error=str(e)
            )
            return False
    
    def _load_whale_scheduler(self) -> bool:
        """
        Загрузка Whale Scheduler
        
        Returns:
            True если загрузка успешна
        """
        try:
            self.whale_scheduler = self._loader.load_whale_scheduler()
            
            self._status.update_component(
                name='whale_scheduler',
                enabled=self.whale_scheduler is not None,
                instance=self.whale_scheduler,
                error=None
            )
            
            return self.whale_scheduler is not None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки whale_scheduler: {e}")
            self._status.update_component(
                name='whale_scheduler',
                enabled=False,
                instance=None,
                error=str(e)
            )
            return False
    
    def _load_bot_application(self) -> bool:
        """
        Загрузка Bot Application
        
        Returns:
            True если загрузка успешна
        """
        try:
            self.bot_application = self._loader.load_bot_application()
            
            self._status.update_component(
                name='bot_application',
                enabled=self.bot_application is not None,
                instance=self.bot_application,
                error=None
            )
            
            return self.bot_application is not None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки bot_application: {e}")
            self._status.update_component(
                name='bot_application',
                enabled=False,
                instance=None,
                error=str(e)
            )
            return False
    
    def _load_trading_system(self) -> bool:
        """
        Загрузка Trading System
        
        Returns:
            True если загрузка успешна
        """
        try:
            self.trading_system = self._loader.load_trading_system()
            
            self._status.update_component(
                name='trading_system',
                enabled=self.trading_system is not None,
                instance=self.trading_system,
                error=None
            )
            
            return self.trading_system is not None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки trading_system: {e}")
            self._status.update_component(
                name='trading_system',
                enabled=False,
                instance=None,
                error=str(e)
            )
            return False
    
    # ========================================================================
    # Проверка статуса компонентов
    # ========================================================================
    
    def has_news(self) -> bool:
        """Проверяет доступность News Bot"""
        return self._status.is_component_available('news_processor')
    
    def has_whale(self) -> bool:
        """Проверяет доступность Whale Monitor"""
        return self._status.is_component_available('whale_scheduler')
    
    def has_bot(self) -> bool:
        """Проверяет доступность Bot Commands"""
        return self._status.is_component_available('bot_application')
    
    def has_trading(self) -> bool:
        """Проверяет доступность Trading System"""
        return self._status.is_component_available('trading_system')
    
    def get_active_components_count(self) -> int:
        """Возвращает количество активных компонентов"""
        return self._status.get_active_components_count()
    
    def is_any_component_active(self) -> bool:
        """Проверяет есть ли хотя бы один активный компонент"""
        return self._status.is_any_component_active()
    
    def get_status_dict(self) -> dict:
        """
        Возвращает статус всех компонентов в виде словаря
        
        Returns:
            Dict с информацией о компонентах
        """
        return {
            **self._status.get_status_dict(),
            'total_active': self.get_active_components_count()
        }
    
    # ========================================================================
    # Завершение работы компонентов
    # ========================================================================
    
    async def stop_all(self) -> None:
        """
        Корректно останавливает все активные компоненты
        """
        await self._shutdown.stop_all(
            whale_scheduler=self.whale_scheduler,
            news_processor=self.news_processor,
            bot_application=self.bot_application,
            trading_system=self.trading_system
        )
    
    # ========================================================================
    # Вспомогательные методы
    # ========================================================================
    
    def _print_loading_header(self) -> None:
        """Вывод заголовка процесса загрузки"""
        logger.info("\n" + "="*80)
        logger.info("📦 LOADING APPLICATION COMPONENTS")
        logger.info("="*80)
    
    def reset(self) -> None:
        """
        Сброс состояния менеджера (для тестов)
        
        ВНИМАНИЕ: Использовать только в тестах!
        """
        self.news_processor = None
        self.whale_scheduler = None
        self.bot_application = None
        self.trading_system = None
        self._status = ComponentStatus()
        
        logger.warning("⚠️  ComponentManager reset (should only be used in tests)")