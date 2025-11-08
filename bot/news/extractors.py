# bot/news/extractors.py
"""
Article Data Extractors
Извлечение и обогащение данных статей
"""

import logging
from typing import List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """
    Извлечение и обогащение данных статей
    
    Добавляет дополнительные метаданные к статьям
    """
    
    def enrich_articles(self, articles: List[Dict], source_data: Dict) -> List[Dict]:
        """
        Обогащение статей дополнительными данными
        
        Args:
            articles: Список статей
            source_data: Данные источника
            
        Returns:
            Обогащенные статьи
        """
        enriched = []
        
        for article in articles:
            try:
                enriched_article = self._enrich_article(article, source_data)
                enriched.append(enriched_article)
            except Exception as e:
                logger.debug(f"Error enriching article: {e}")
                enriched.append(article)
        
        return enriched
    
    def _enrich_article(self, article: Dict, source_data: Dict) -> Dict:
        """
        Обогащение одной статьи
        
        Добавляет:
        - Метаданные источника
        - Временные метки
        - Нормализованные данные
        """
        # Копия статьи
        enriched = article.copy()
        
        # Добавление метаданных источника
        enriched['source_metadata'] = {
            'priority': source_data.get('priority', 1),
            'language': source_data.get('language', 'en'),
            'enabled': source_data.get('enabled', True)
        }
        
        # Временные метки
        enriched['fetched_at'] = datetime.now(timezone.utc)
        
        # Нормализация published
        if 'published' not in enriched or enriched['published'] is None:
            enriched['published'] = datetime.now(timezone.utc)
        
        # Нормализация description
        if 'description' not in enriched:
            enriched['description'] = ''
        
        # Добавление ID на основе URL
        enriched['id'] = self._generate_article_id(enriched['url'])
        
        return enriched
    
    def _generate_article_id(self, url: str) -> str:
        """
        Генерация ID статьи на основе URL
        
        Args:
            url: URL статьи
            
        Returns:
            Хеш строка
        """
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()


__all__ = ['ArticleExtractor']