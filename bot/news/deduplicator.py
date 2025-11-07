# bot/news/deduplicator.py
"""
Article Deduplication System
"""

import re
import hashlib
from typing import Dict, Set


class ArticleDeduplicator:
    """Система дедупликации статей"""
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.max_cache_size = 10000
    
    def is_duplicate(self, article: Dict) -> bool:
        """
        Проверяет является ли статья дубликатом
        
        Args:
            article: Словарь с данными статьи (должен содержать 'url' и 'title')
        
        Returns:
            True если дубликат
        """
        url = article.get('url', '')
        if not url:
            return True
        
        if url in self.seen_urls:
            return True
        
        title = article.get('title', '')
        if not title:
            return True
        
        title_hash = self._compute_title_hash(title)
        
        if title_hash in self.seen_hashes:
            return True
        
        return False
    
    def mark_as_seen(self, article: Dict):
        """Помечает статью как просмотренную"""
        url = article.get('url', '')
        title = article.get('title', '')
        
        if url:
            self.seen_urls.add(url)
        
        if title:
            title_hash = self._compute_title_hash(title)
            self.seen_hashes.add(title_hash)
        
        self._cleanup_cache()
    
    def _compute_title_hash(self, title: str) -> str:
        """Вычисляет хеш заголовка"""
        title_lower = title.lower()
        title_normalized = re.sub(r'[^\w\s]', '', title_lower)
        title_normalized = re.sub(r'\s+', ' ', title_normalized).strip()
        
        return hashlib.md5(title_normalized.encode('utf-8')).hexdigest()
    
    def _cleanup_cache(self):
        """Очищает старые записи если кеш переполнен"""
        if len(self.seen_urls) > self.max_cache_size:
            to_remove = int(len(self.seen_urls) * 0.2)
            self.seen_urls = set(list(self.seen_urls)[to_remove:])
        
        if len(self.seen_hashes) > self.max_cache_size:
            to_remove = int(len(self.seen_hashes) * 0.2)
            self.seen_hashes = set(list(self.seen_hashes)[to_remove:])
    
    def get_stats(self) -> Dict:
        """Возвращает статистику"""
        return {
            'seen_urls': len(self.seen_urls),
            'seen_hashes': len(self.seen_hashes)
        }