# core/components.py
"""
Component Loading and Management System

Модуль отвечает за загрузку и управление жизненным циклом
всех компонентов приложения:
- News Processor (обработка новостей)
- Whale Scheduler (мониторинг whale транзакций)
- Bot Application (Telegram команды)
- Trading System (торговая система)
"""

import logging
import asyncio
import traceback
from typing import Optional, Any, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Component Loader - Загрузка компонентов
# ============================================================================

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
        
        News Processor отвечает за:
        - Получение новостей из RSS фидов
        - AI обработку контента
        - Публикацию в Telegram канал
        
        Returns:
            NewsProcessor instance или None если отключен/недоступен
        """
        # Ленивый импорт config чтобы избежать циклических зависимостей
        from app.config import config
        
        if not config.is_feature_enabled('news'):
            logger.info("ℹ️  [LOADER] News Bot отключен в конфигурации")
            return None
        
        try:
            logger.info("📰 [LOADER] Загрузка News Processor...")
            from bot.processor import NewsProcessor
            
            processor = NewsProcessor()
            logger.info("✅ [LOADER] News Processor успешно загружен")
            return processor
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] News Processor недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль bot.processor")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки News Processor: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None
    
    @staticmethod
    def load_whale_scheduler() -> Optional[Any]:
        """
        Загрузка Whale Scheduler
        
        Whale Scheduler отвечает за:
        - Мониторинг whale транзакций на блокчейнах
        - Анализ и фильтрацию событий
        - Публикацию alerts в Telegram
        
        Returns:
            Scheduler instance или None если отключен/недоступен
        """
        from app.config import config
        
        if not config.is_feature_enabled('whale'):
            logger.info("ℹ️  [LOADER] Whale Monitor отключен в конфигурации")
            return None
        
        try:
            logger.info("🐋 [LOADER] Загрузка Whale Scheduler...")
            from app.scheduler import scheduler as whale_scheduler
            
            logger.info("✅ [LOADER] Whale Scheduler успешно загружен")
            return whale_scheduler
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Whale Scheduler недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль app.scheduler")
            return None
            
        except AttributeError as e:
            logger.error(f"❌ [LOADER] Ошибка конфигурации Whale Scheduler: {e}")
            logger.error("   Проверьте что все необходимые атрибуты присутствуют в config")
            logger.debug("Traceback:", exc_info=True)
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки Whale Scheduler: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None
    
    @staticmethod
    def load_bot_application() -> Optional[Any]:
        """
        Загрузка Bot Application
        
        Bot Application отвечает за:
        - Обработку Telegram команд пользователей
        - Интерактивные меню и кнопки
        - Административные функции
        
        Returns:
            Application instance или None если недоступен
        """
        try:
            logger.info("🤖 [LOADER] Загрузка Bot Application...")
            from app.bot import application as bot_application
            
            logger.info("✅ [LOADER] Bot Application успешно загружен")
            return bot_application
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Bot Application недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль app.bot")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки Bot Application: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None


# ============================================================================
# Component Manager - Управление компонентами
# ============================================================================

class ComponentManager:
    """
    Менеджер жизненного цикла компонентов
    
    Управляет:
    - Загрузкой компонентов при старте
    - Проверкой статуса компонентов
    - Корректным завершением работы компонентов
    
    Singleton паттерн для единого экземпляра
    """
    
    _instance: Optional['ComponentManager'] = None
    
    def __new__(cls) -> 'ComponentManager':
        """Singleton implementation"""
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
        
        # Флаги состояния компонентов
        self._news_enabled: bool = False
        self._whale_enabled: bool = False
        self._bot_enabled: bool = False
        self._trading_enabled: bool = False
        
        self._initialized = True
    
    # ========================================================================
    # Загрузка компонентов
    # ========================================================================
    
    def load_all(self) -> Tuple[bool, bool, bool]:
        """
        Загружает все компоненты приложения
        
        Процесс загрузки:
        1. News Processor (если включен в конфигурации)
        2. Whale Scheduler (если включен в конфигурации)
        3. Bot Application (всегда пытается загрузить)
        4. Проверка Trading System (если есть)
        
        Returns:
            Tuple[news_available, whale_available, bot_available]
        """
        self._print_loading_header()
        
        loader = ComponentLoader()
        
        # Загрузка News Processor
        self.news_processor = loader.load_news_processor()
        self._news_enabled = self.news_processor is not None
        
        # Загрузка Whale Scheduler
        self.whale_scheduler = loader.load_whale_scheduler()
        self._whale_enabled = self.whale_scheduler is not None
        
        # Загрузка Bot Application
        self.bot_application = loader.load_bot_application()
        self._bot_enabled = self.bot_application is not None
        
        # Проверка Trading System
        self._check_trading_enabled()
        
        # Вывод итоговой информации
        self._print_component_status()
        
        return (
            self._news_enabled,
            self._whale_enabled,
            self._bot_enabled
        )
    
    def _check_trading_enabled(self) -> None:
        """
        Проверяет статус торговой системы
        
        Trading может быть включен через:
        1. Флаг в конфигурации
        2. Whale Scheduler с активной торговлей
        """
        try:
            from app.config import config
            
            if config.is_feature_enabled('trading'):
                self._trading_enabled = True
                logger.debug("   Trading включен через config")
            elif self.whale_scheduler and hasattr(self.whale_scheduler, 'trading_enabled'):
                self._trading_enabled = self.whale_scheduler.trading_enabled
                logger.debug(f"   Trading статус из whale_scheduler: {self._trading_enabled}")
            else:
                self._trading_enabled = False
                logger.debug("   Trading отключен")
                
        except Exception as e:
            logger.warning(f"⚠️  [MANAGER] Ошибка проверки trading статуса: {e}")
            self._trading_enabled = False
    
    # ========================================================================
    # Проверка статуса компонентов
    # ========================================================================
    
    def has_news(self) -> bool:
        """Проверяет доступность News Bot"""
        return self._news_enabled
    
    def has_whale(self) -> bool:
        """Проверяет доступность Whale Monitor"""
        return self._whale_enabled
    
    def has_bot(self) -> bool:
        """Проверяет доступность Bot Commands"""
        return self._bot_enabled
    
    def has_trading(self) -> bool:
        """Проверяет доступность Trading System"""
        return self._trading_enabled
    
    def get_active_components_count(self) -> int:
        """Возвращает количество активных компонентов"""
        return sum([
            self._news_enabled,
            self._whale_enabled,
            self._bot_enabled,
            self._trading_enabled
        ])
    
    def is_any_component_active(self) -> bool:
        """Проверяет есть ли хотя бы один активный компонент"""
        return self.get_active_components_count() > 0
    
    # ========================================================================
    # Завершение работы компонентов
    # ========================================================================
    
    async def stop_all(self) -> None:
        """
        Корректно останавливает все активные компоненты
        
        Процесс остановки:
        1. Whale Scheduler (cleanup)
        2. News Processor (cleanup)
        3. Bot Application (stop)
        
        Каждый компонент имеет timeout на остановку
        """
        logger.info("\n" + "="*80)
        logger.info("🛑 STOPPING ALL COMPONENTS")
        logger.info("="*80)
        
        stop_timeout = 10.0
        
        # Остановка Whale Scheduler
        if self.whale_scheduler and hasattr(self.whale_scheduler, 'cleanup'):
            await self._stop_component(
                component=self.whale_scheduler,
                name="Whale Scheduler",
                cleanup_method="cleanup",
                timeout=stop_timeout
            )
        
        # Остановка News Processor
        if self.news_processor and hasattr(self.news_processor, 'cleanup'):
            await self._stop_component(
                component=self.news_processor,
                name="News Processor",
                cleanup_method="cleanup",
                timeout=stop_timeout
            )
        
        # Остановка Bot Application
        if self.bot_application and hasattr(self.bot_application, 'stop'):
            await self._stop_component(
                component=self.bot_application,
                name="Bot Application",
                cleanup_method="stop",
                timeout=stop_timeout
            )
        
        logger.info("✅ Все компоненты остановлены")
        logger.info("="*80 + "\n")
    
    async def _stop_component(
        self, 
        component: Any, 
        name: str, 
        cleanup_method: str,
        timeout: float
    ) -> None:
        """
        Останавливает отдельный компонент с таймаутом
        
        Args:
            component: Экземпляр компонента
            name: Название компонента для логов
            cleanup_method: Название метода для вызова (cleanup/stop)
            timeout: Максимальное время ожидания в секундах
        """
        try:
            logger.info(f"   Остановка {name}...")
            
            cleanup_func = getattr(component, cleanup_method)
            await asyncio.wait_for(
                cleanup_func(),
                timeout=timeout
            )
            
            logger.info(f"   ✓ {name} успешно остановлен")
            
        except asyncio.TimeoutError:
            logger.warning(f"   ⚠️  Timeout остановки {name} ({timeout}s)")
            
        except Exception as e:
            logger.warning(f"   ⚠️  Ошибка остановки {name}: {e}")
            logger.debug("Traceback:", exc_info=True)
    
    # ========================================================================
    # Вспомогательные методы для вывода информации
    # ========================================================================
    
    def _print_loading_header(self) -> None:
        """Вывод заголовка процесса загрузки"""
        logger.info("\n" + "="*80)
        logger.info("📦 LOADING APPLICATION COMPONENTS")
        logger.info("="*80)
    
    def _print_component_status(self) -> None:
        """Вывод итогового статуса всех компонентов"""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPONENT STATUS SUMMARY")
        logger.info("="*80)
        
        # Статус каждого компонента
        components_status = [
            ("News Bot", self._news_enabled),
            ("Whale Monitor", self._whale_enabled),
            ("Trading System", self._trading_enabled),
            ("Bot Commands", self._bot_enabled),
        ]
        
        for name, enabled in components_status:
            status = "✅ Активен" if enabled else "❌ Недоступен"
            logger.info(f"   {name:20} {status}")
        
        # Общая статистика
        active_count = self.get_active_components_count()
        total_count = len(components_status)
        
        logger.info(f"\n   Активно компонентов: {active_count}/{total_count}")
        
        if not self.is_any_component_active():
            logger.warning("   ⚠️  Нет активных компонентов!")
        
        logger.info("="*80 + "\n")
    
    # ========================================================================
    # Информация о компонентах
    # ========================================================================
    
    def get_status_dict(self) -> dict:
        """
        Возвращает статус всех компонентов в виде словаря
        
        Returns:
            Dict с информацией о компонентах
        """
        return {
            'news_processor': {
                'enabled': self._news_enabled,
                'instance': self.news_processor is not None
            },
            'whale_scheduler': {
                'enabled': self._whale_enabled,
                'instance': self.whale_scheduler is not None
            },
            'bot_application': {
                'enabled': self._bot_enabled,
                'instance': self.bot_application is not None
            },
            'trading_system': {
                'enabled': self._trading_enabled,
                'instance': False  # Trading интегрирован в whale_scheduler
            },
            'total_active': self.get_active_components_count()
        }


# ============================================================================
# Публичный API модуля
# ============================================================================

__all__ = [
    'ComponentLoader',
    'ComponentManager',
]