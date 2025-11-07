# bot/news/fetcher.py
"""
News Fetcher - RSS/Web scraping
"""

import re
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional

import aiohttp
import feedparser
from bs4 import BeautifulSoup


class NewsFetcher:
    """Получение новостей из RSS источников"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
    
    async def fetch_source(self, source: Dict) -> List[Dict]:
        """
        Получает статьи из одного источника
        
        Args:
            source: Словарь с данными источника (name, url, category)
        
        Returns:
            List статей
        """
        url = source.get('url')
        name = source.get('name', 'Unknown')
        category = source.get('category', 'news')
        
        if not url:
            return []
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"⚠️  [{name}] HTTP {response.status}")
                        return []
                    
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'xml' in content_type or 'rss' in content_type or 'atom' in content_type:
                        text = await response.text()
                        return self._parse_rss(text, name, category)
                    else:
                        text = await response.text()
                        return self._parse_html(text, name, category, url)
        
        except asyncio.TimeoutError:
            print(f"⏱️  [{name}] Timeout")
            return []
        
        except aiohttp.ClientError as e:
            print(f"❌ [{name}] Network error: {e}")
            return []
        
        except Exception as e:
            print(f"❌ [{name}] Error: {e}")
            return []
    
    def _parse_rss(self, content: str, source_name: str, category: str) -> List[Dict]:
        """Парсит RSS feed"""
        try:
            feed = feedparser.parse(content)
            
            if not feed.entries:
                return []
            
            articles = []
            
            for entry in feed.entries[:10]:
                try:
                    article = self._extract_article_from_entry(entry, source_name, category)
                    if article:
                        articles.append(article)
                except Exception:
                    continue
            
            return articles
        
        except Exception as e:
            print(f"❌ [RSS] Parse error: {e}")
            return []
    
    def _parse_html(self, content: str, source_name: str, category: str, base_url: str) -> List[Dict]:
        """Парсит HTML страницу"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            articles = []
            
            for article_tag in soup.find_all('article', limit=10):
                try:
                    title_tag = article_tag.find(['h1', 'h2', 'h3', 'h4'])
                    link_tag = article_tag.find('a', href=True)
                    
                    if title_tag and link_tag:
                        title = title_tag.get_text(strip=True)
                        url = link_tag['href']
                        
                        if not url.startswith('http'):
                            url = base_url + url
                        
                        article = {
                            'title': title,
                            'url': url,
                            'link': url,
                            'source': source_name,
                            'category': category,
                            'published': datetime.now(timezone.utc)
                        }
                        
                        articles.append(article)
                
                except Exception:
                    continue
            
            return articles
        
        except Exception as e:
            print(f"❌ [HTML] Parse error: {e}")
            return []
    
    def _extract_article_from_entry(self, entry, source: str, category: str) -> Optional[Dict]:
        """Извлекает данные статьи из RSS entry"""
        try:
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            
            if not title or not url:
                return None
            
            description = entry.get('summary', '') or entry.get('description', '')
            
            if description:
                description = BeautifulSoup(description, 'html.parser').get_text()
                description = re.sub(r'\s+', ' ', description).strip()[:500]
            
            published = self._parse_date(entry.get('published', ''))
            
            return {
                'title': title,
                'url': url,
                'link': url,
                'source': source,
                'category': category,
                'description': description,
                'published': published or datetime.now(timezone.utc)
            }
        
        except Exception:
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Парсит дату из RSS"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return None