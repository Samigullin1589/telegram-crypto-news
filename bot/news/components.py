# bot/news/components.py
"""
News Processor Components Loader
Загрузка опциональных компонентов процессора
"""

import logging
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessorComponents:
    """Компоненты процессора новостей"""
    ai_handler: Optional[Any] = None
    content_parser: Optional[Any] = None
    database: Optional[Any] = None
    telegram: Optional[Any] = None
    
    def has_ai(self) -> bool:
        """Проверка наличия AI обработчика"""
        return self.ai_handler is not None
    
    def has_parser(self) -> bool:
        """Проверка наличия парсера контента"""
        return self.content_parser is not None
    
    def has_database(self) -> bool:
        """Проверка наличия БД"""
        return self.database is not None
    
    def has_telegram(self) -> bool:
        """Проверка наличия Telegram постера"""
        return self.telegram is not None


class ComponentsLoader:
    """Загрузчик компонентов процессора"""
    
    @staticmethod
    def load_all() -> ProcessorComponents:
        """
        Загрузка всех компонентов
        
        Returns:
            ProcessorComponents с загруженными компонентами
        """
        components = ProcessorComponents()
        
        # Загрузка AI Handler
        components.ai_handler = ComponentsLoader._load_ai_handler()
        
        # Загрузка Content Parser
        components.content_parser = ComponentsLoader._load_content_parser()
        
        # Загрузка Database
        components.database = ComponentsLoader._load_database()
        
        # Загрузка Telegram Poster
        components.telegram = ComponentsLoader._load_telegram_poster()
        
        ComponentsLoader._log_components_status(components)
        
        return components
    
    @staticmethod
    def _load_ai_handler() -> Optional[Any]:
        """Загрузка AI Handler"""
        try:
            from bot.ai_handler import AIHandler
            handler = AIHandler()
            print("   ✅ AI Handler loaded")
            return handler
        except ImportError:
            print("   ⚠️  AI Handler not available (optional)")
            return None
        except Exception as e:
            print(f"   ⚠️  AI Handler error: {e}")
            logger.debug(f"AI Handler load error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _load_content_parser() -> Optional[Any]:
        """Загрузка Content Parser"""
        try:
            from bot.content_parser import ContentParser
            parser = ContentParser()
            print("   ✅ Content Parser loaded")
            return parser
        except ImportError:
            print("   ⚠️  Content Parser not available (optional)")
            return None
        except Exception as e:
            print(f"   ⚠️  Content Parser error: {e}")
            logger.debug(f"Content Parser load error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _load_database() -> Optional[Any]:
        """Загрузка Database"""
        try:
            from bot.database import NewsDatabase
            db = NewsDatabase()
            print("   ✅ Database loaded")
            return db
        except ImportError:
            print("   ⚠️  Database not available (optional)")
            return None
        except Exception as e:
            print(f"   ⚠️  Database error: {e}")
            logger.debug(f"Database load error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _load_telegram_poster() -> Optional[Any]:
        """Загрузка Telegram Poster"""
        try:
            from bot.telegram_poster import NewsTelegramPoster
            poster = NewsTelegramPoster()
            print("   ✅ Telegram Poster loaded")
            return poster
        except ImportError:
            print("   ⚠️  Telegram Poster not available (optional)")
            return None
        except Exception as e:
            print(f"   ⚠️  Telegram Poster error: {e}")
            logger.debug(f"Telegram Poster load error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _log_components_status(components: ProcessorComponents):
        """Логирование статуса компонентов"""
        loaded = []
        if components.has_ai():
            loaded.append("AI")
        if components.has_parser():
            loaded.append("Parser")
        if components.has_database():
            loaded.append("DB")
        if components.has_telegram():
            loaded.append("Telegram")
        
        if loaded:
            print(f"\n   Optional components: {', '.join(loaded)}")