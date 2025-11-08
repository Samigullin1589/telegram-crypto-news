# core/components/loaders.py
"""
Component Loaders
Загрузчики бизнес-компонентов приложения
"""

import logging
from typing import Optional, Any

from .errors import ComponentLoadError

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
        
        News Processor отвечает за:
        - Получение новостей из RSS фидов
        - AI обработку контента
        - Публикацию в Telegram канал
        
        Returns:
            NewsProcessor instance или None если отключен/недоступен
        """
        try:
            # Ленивый импорт config чтобы избежать циклических зависимостей
            from app.config import config
            
            if not config.is_feature_enabled('news'):
                logger.info("ℹ️  [LOADER] News Bot отключен в конфигурации")
                return None
            
            logger.info("📰 [LOADER] Загрузка News Processor...")
            
            # Импорт модуля процессора новостей
            from bot.news.processor import NewsProcessor
            
            # Создание экземпляра
            processor = NewsProcessor()
            
            logger.info("✅ [LOADER] News Processor успешно загружен")
            return processor
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] News Processor недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль bot.news.processor")
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
        try:
            from app.config import config
            
            if not config.is_feature_enabled('whale'):
                logger.info("ℹ️  [LOADER] Whale Monitor отключен в конфигурации")
                return None
            
            logger.info("🐋 [LOADER] Загрузка Whale Scheduler...")
            
            # Импорт модуля whale scheduler
            from app.scheduler.whale_monitor import WhaleMonitor
            
            # Создание экземпляра
            scheduler = WhaleMonitor()
            
            logger.info("✅ [LOADER] Whale Scheduler успешно загружен")
            return scheduler
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Whale Scheduler недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль app.scheduler.whale_monitor")
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
            
            # Импорт telegram bot application
            from app.bot import application as bot_application
            
            if bot_application is None:
                logger.warning("⚠️  [LOADER] Bot Application не инициализирован")
                return None
            
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
    
    @staticmethod
    def load_trading_system() -> Optional[Any]:
        """
        Загрузка Trading System
        
        Trading System отвечает за:
        - Генерацию торговых сигналов
        - Управление позициями
        - Риск-менеджмент
        
        Returns:
            TradingSystem instance или None если отключен/недоступен
        """
        try:
            from app.config import config
            
            if not config.is_feature_enabled('trading'):
                logger.info("ℹ️  [LOADER] Trading System отключен в конфигурации")
                return None
            
            logger.info("📈 [LOADER] Загрузка Trading System...")
            
            # Импорт торговой системы
            from app.trading_system import TradingSystem
            
            # Создание экземпляра
            trading = TradingSystem()
            
            logger.info("✅ [LOADER] Trading System успешно загружен")
            return trading
            
        except ImportError as e:
            logger.warning(f"⚠️  [LOADER] Trading System недоступен (ImportError): {e}")
            logger.debug(f"   Возможно отсутствует модуль app.trading_system")
            return None
            
        except Exception as e:
            logger.error(f"❌ [LOADER] Ошибка загрузки Trading System: {e}")
            logger.debug("Traceback:", exc_info=True)
            return None