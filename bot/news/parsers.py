# bot/news/parsers.py
"""
Content Parsers for News Fetching
Парсеры контента для получения новостей
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RSSParser:
    """
    Парсер RSS/Atom фидов
    
    Поддерживает:
    - RSS 2.0
    - Atom
    - RDF
    """
    
    def __init__(self, max_entries: int = 10):
        """
        Инициализация парсера
        
        Args:
            max_entries: Максимальное количество статей для извлечения
        """
        self.max_entries = max_entries
    
    def parse(self, content: str, source_name: str, category: str) -> List[Dict]:
        """
        Парсинг RSS контента
        
        Args:
            content: XML контент фида
            source_name: Название источника
            category: Категория новостей
            
        Returns:
            Список статей
        """
        try:
            feed = feedparser.parse(content)
            
            if not feed.entries:
                logger.debug(f"[{source_name}] No entries in feed")
                return []
            
            articles = []
            
            for entry in feed.entries[:self.max_entries]:
                try:
                    article = self._extract_from_entry(entry, source_name, category)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.debug(f"[{source_name}] Error parsing entry: {e}")
                    continue
            
            logger.debug(f"[{source_name}] Parsed {len(articles)} articles from RSS")
            return articles
        
        except Exception as e:
            logger.error(f"[{source_name}] RSS parse error: {e}")
            return []
    
    def _extract_from_entry(
        self,
        entry,
        source_name: str,
        category: str
    ) -> Optional[Dict]:
        """
        Извлечение данных из RSS entry
        
        Args:
            entry: feedparser entry объект
            source_name: Название источника
            category: Категория
            
        Returns:
            Словарь с данными статьи или None
        """
        try:
            # Обязательные поля
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            
            if not title or not url:
                return None
            
            # Описание
            description = self._extract_description(entry)
            
            # Дата публикации
            published = self._extract_date(entry)
            
            # Автор
            author = self._extract_author(entry)
            
            return {
                'title': title,
                'url': url,
                'link': url,
                'source': source_name,
                'category': category,
                'description': description,
                'published': published,
                'author': author
            }
        
        except Exception as e:
            logger.debug(f"Error extracting entry: {e}")
            return None
    
    def _extract_description(self, entry) -> str:
        """Извлечение описания из entry"""
        description = entry.get('summary', '') or entry.get('description', '')
        
        if description:
            # Удаление HTML тегов
            description = BeautifulSoup(description, 'html.parser').get_text()
            # Нормализация пробелов
            description = re.sub(r'\s+', ' ', description).strip()
            # Ограничение длины
            description = description[:500]
        
        return description
    
    def _extract_date(self, entry) -> datetime:
        """Извлечение даты публикации"""
        date_str = entry.get('published', '') or entry.get('updated', '')
        
        if date_str:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_str)
            except:
                pass
        
        return datetime.now(timezone.utc)
    
    def _extract_author(self, entry) -> str:
        """Извлечение автора"""
        # Попытка получить автора разными способами
        author = entry.get('author', '')
        
        if not author and 'author_detail' in entry:
            author = entry.author_detail.get('name', '')
        
        if not author and 'authors' in entry and entry.authors:
            author = entry.authors[0].get('name', '')
        
        return author.strip()


class HTMLParser:
    """
    Парсер HTML страниц
    
    Пытается извлечь статьи из обычных HTML страниц
    """
    
    def __init__(self, max_articles: int = 10):
        """
        Инициализация парсера
        
        Args:
            max_articles: Максимальное количество статей
        """
        self.max_articles = max_articles
    
    def parse(
        self,
        content: str,
        source_name: str,
        category: str,
        base_url: str
    ) -> List[Dict]:
        """
        Парсинг HTML контента
        
        Args:
            content: HTML контент
            source_name: Название источника
            category: Категория
            base_url: Базовый URL для относительных ссылок
            
        Returns:
            Список статей
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')
            articles = []
            
            # Попытка найти article теги
            article_tags = soup.find_all('article', limit=self.max_articles)
            
            for article_tag in article_tags:
                try:
                    article = self._extract_from_tag(
                        article_tag,
                        source_name,
                        category,
                        base_url
                    )
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.debug(f"Error parsing article tag: {e}")
                    continue
            
            logger.debug(f"[{source_name}] Parsed {len(articles)} articles from HTML")
            return articles
        
        except Exception as e:
            logger.error(f"[{source_name}] HTML parse error: {e}")
            return []
    
    def _extract_from_tag(
        self,
        article_tag,
        source_name: str,
        category: str,
        base_url: str
    ) -> Optional[Dict]:
        """Извлечение статьи из article тега"""
        try:
            # Поиск заголовка
            title_tag = article_tag.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            if not title_tag:
                return None
            
            title = title_tag.get_text(strip=True)
            
            # Поиск ссылки
            link_tag = article_tag.find('a', href=True)
            if not link_tag:
                return None
            
            url = link_tag['href']
            
            # Нормализация URL
            if not url.startswith('http'):
                url = self._normalize_url(base_url, url)
            
            # Поиск описания
            description = self._extract_html_description(article_tag)
            
            return {
                'title': title,
                'url': url,
                'link': url,
                'source': source_name,
                'category': category,
                'description': description,
                'published': datetime.now(timezone.utc)
            }
        
        except Exception as e:
            logger.debug(f"Error extracting from tag: {e}")
            return None
    
    def _normalize_url(self, base_url: str, relative_url: str) -> str:
        """Нормализация относительного URL"""
        if relative_url.startswith('/'):
            # Абсолютный путь
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{relative_url}"
        else:
            # Относительный путь
            return base_url.rstrip('/') + '/' + relative_url.lstrip('/')
    
    def _extract_html_description(self, article_tag) -> str:
        """Извлечение описания из HTML"""
        # Поиск параграфов
        paragraphs = article_tag.find_all('p', limit=2)
        
        if paragraphs:
            text = ' '.join(p.get_text(strip=True) for p in paragraphs)
            return text[:500]
        
        return ''


__all__ = ['RSSParser', 'HTMLParser']