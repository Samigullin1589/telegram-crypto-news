# bot/news/fetcher.py
"""
News Fetcher v2.0 - Fixed FeedConfig Support
Исправленный фетчер с поддержкой FeedConfig объектов
"""

import logging
from typing import List, Dict, Union, TYPE_CHECKING, Optional

from .http_client import NewsHttpClient
from .parsers import RSSParser, HTMLParser
from .extractors import ArticleExtractor

if TYPE_CHECKING:
    from app.config import FeedConfig

logger = logging.getLogger(__name__)


class NewsFetcher:
    """
    Получение новостей из RSS/Web источников
    
    Улучшения v2.0:
    - Поддержка FeedConfig объектов (не только словарей)
    - Модульная архитектура
    - Улучшенная обработка ошибок
    """
    
    def __init__(self):
        """Инициализация фетчера"""
        self.http_client = NewsHttpClient()
        self.rss_parser = RSSParser()
        self.html_parser = HTMLParser()
        self.extractor = ArticleExtractor()
    
    async def fetch_source(
        self,
        source: Union[Dict, 'FeedConfig'],
        source_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Получает статьи из одного источника
        
        Args:
            source: Словарь или FeedConfig объект с данными источника
        
        Returns:
            List статей
        """
        # Нормализация источника в словарь
        source_data = self._normalize_source(source)
        if source_name:
            source_data['name'] = source_name
        
        url = source_data.get('url')
        name = source_data.get('name', 'Unknown')
        category = source_data.get('category', 'news')
        
        if not url:
            logger.warning(f"Source {name} has no URL")
            return []
        
        try:
            # Получение контента
            content, content_type = await self.http_client.fetch(url, name)
            
            if content is None:
                return []
            
            # Парсинг в зависимости от типа контента
            if self._is_feed_content(content_type):
                articles = self.rss_parser.parse(content, name, category)
            else:
                articles = self.html_parser.parse(content, name, category, url)
            
            # Обогащение статей дополнительными данными
            return self.extractor.enrich_articles(articles, source_data)
        
        except Exception as e:
            logger.error(f"Error fetching {name}: {e}", exc_info=True)
            return []
    
    def _normalize_source(self, source: Union[Dict, 'FeedConfig']) -> Dict:
        """
        Нормализует источник в словарь
        
        Поддерживает:
        - Словари (старый формат)
        - FeedConfig объекты (новый формат)
        
        Args:
            source: Источник данных
            
        Returns:
            Словарь с данными источника
        """
        if isinstance(source, dict):
            # Уже словарь
            return source
        
        # Объект FeedConfig
        try:
            return {
                'name': getattr(source, 'name', 'Unknown'),
                'url': getattr(source, 'url', ''),
                'category': getattr(source, 'category', 'news'),
                'enabled': getattr(source, 'enabled', True),
                'priority': getattr(source, 'priority', 1),
                'language': getattr(source, 'language', 'en'),
                'fetch_interval': getattr(source, 'fetch_interval', 300)
            }
        except Exception as e:
            logger.error(f"Error normalizing source: {e}")
            return {
                'name': 'Unknown',
                'url': '',
                'category': 'news'
            }
    
    def _is_feed_content(self, content_type: str) -> bool:
        """
        Проверка является ли контент RSS/Atom фидом
        
        Args:
            content_type: Content-Type заголовок
            
        Returns:
            True если это фид
        """
        feed_types = ['xml', 'rss', 'atom', 'feed']
        return any(feed_type in content_type.lower() for feed_type in feed_types)


__all__ = ['NewsFetcher']