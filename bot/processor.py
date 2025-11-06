# bot/processor.py
"""
News Processor v4.5 - Production Ready
"""

import os
import asyncio
import hashlib
import traceback
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Any
from collections import defaultdict

import aiohttp
import feedparser
from bs4 import BeautifulSoup

try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

from app.config import config

try:
    from bot.ai_handler import AIHandler
    from bot.content_parser import ContentParser
    from bot.database import NewsDatabase
    from bot.telegram_poster import NewsTelegramPoster
    AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  [NEWS] Import error: {e}")
    AI_AVAILABLE = False


class NewsProcessor:
    """Production-ready новостной процессор"""
    
    def __init__(self):
        """Инициализация процессора"""
        
        print("\n" + "="*80)
        print("📰 NEWS PROCESSOR v4.5 - INITIALIZATION")
        print("="*80 + "\n")
        
        if not config.is_feature_enabled('news'):
            print("⚠️  [NEWS] News processing disabled in config")
            self._initialized = False
            return
        
        if not hasattr(config, 'news') or not config.news.sources:
            print("❌ [NEWS] No news sources configured")
            self._initialized = False
            return
        
        if not AI_AVAILABLE:
            print("❌ [NEWS] AI components not available")
            self._initialized = False
            return
        
        try:
            self.ai_handler = AIHandler()
            self.content_parser = ContentParser()
            self.database = NewsDatabase()
            self.telegram = NewsTelegramPoster()
            
            print("✅ All components initialized")
            print(f"   • Sources: {len(config.news.sources)}")
            print(f"   • Fetch interval: {config.news.fetch_interval}s")
            print(f"   • AI Provider: {config.get_ai_provider() or 'None'}")
            print()
            
            self._initialized = True
            self._database_initialized = False
            self._baseline_loaded = False
            self.shutdown_requested = False
            
            self.seen_urls: Set[str] = set()
            self.seen_hashes: Set[str] = set()
            self.posts_this_hour = 0
            self.hour_start_time = datetime.now(timezone.utc)
            
        except Exception as e:
            print(f"❌ [NEWS] Initialization failed: {e}")
            traceback.print_exc()
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Проверить инициализацию"""
        return getattr(self, '_initialized', False)
    
    async def initialize_database(self):
        """Инициализировать базу данных"""
        if self._database_initialized:
            return
        
        try:
            await self.database.initialize()
            print("✅ [NEWS] Database initialized")
            self._database_initialized = True
        except Exception as e:
            print(f"⚠️  [NEWS] Database initialization failed: {e}")
    
    async def run_cycle(self):
        """Выполнить один цикл обработки новостей"""
        
        if not self.is_initialized:
            print("⚠️  [NEWS] Processor not initialized, skipping cycle")
            return
        
        if not self._database_initialized:
            await self.initialize_database()
        
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
        
        print(f"\n📰 [NEWS] Starting cycle at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")
        
        articles = await self._fetch_all_sources()
        
        if not articles:
            print("👍 [NEWS] No new articles")
            return
        
        print(f"📊 [NEWS] Fetched {len(articles)} new articles")
        
        await asyncio.sleep(1)
    
    async def _initial_baseline(self):
        """Загрузить начальное состояние"""
        print("📊 [BASELINE] Loading initial state...")
        
        try:
            articles = await self._fetch_all_sources()
            for article in articles:
                self._mark_as_seen(article)
            print(f"✅ Baseline created: {len(articles)} articles")
        except Exception as e:
            print(f"⚠️  [BASELINE] Error: {e}")
    
    async def _fetch_all_sources(self) -> List[Dict]:
        """Получить статьи из всех источников"""
        
        if not hasattr(config.news, 'sources'):
            return []
        
        all_articles = []
        
        for source in config.news.sources[:3]:
            try:
                articles = await self._fetch_source(source)
                if articles:
                    all_articles.extend(articles)
            except Exception as e:
                print(f"❌ [FETCH] {source.get('name', 'Unknown')}: {e}")
        
        return all_articles
    
    async def _fetch_source(self, source: Dict) -> List[Dict]:
        """Получить статьи из одного источника"""
        
        url = source.get('url')
        name = source.get('name', 'Unknown')
        
        if not url:
            return []
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    
                    text = await response.text()
                    return self._parse_rss(text, name)
        
        except Exception as e:
            return []
    
    def _parse_rss(self, content: str, source_name: str) -> List[Dict]:
        """Распарсить RSS feed"""
        
        try:
            feed = feedparser.parse(content)
            
            if not feed.entries:
                return []
            
            articles = []
            
            for entry in feed.entries[:5]:
                try:
                    article = self._extract_article(entry, source_name)
                    
                    if article and not self._is_duplicate(article):
                        articles.append(article)
                
                except Exception:
                    continue
            
            return articles
        
        except Exception:
            return []
    
    def _extract_article(self, entry, source: str) -> Optional[Dict]:
        """Извлечь данные статьи из RSS entry"""
        
        try:
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            
            if not title or not url:
                return None
            
            return {
                'title': title,
                'url': url,
                'link': url,
                'source': source,
                'published': datetime.now(timezone.utc)
            }
        
        except Exception:
            return None
    
    def _is_duplicate(self, article: Dict) -> bool:
        """Проверить на дубликат"""
        
        url = article['url']
        if url in self.seen_urls:
            return True
        
        title = article['title'].lower()
        title_normalized = re.sub(r'[^\w\s]', '', title)
        title_hash = hashlib.md5(title_normalized.encode()).hexdigest()
        
        if title_hash in self.seen_hashes:
            return True
        
        return False
    
    def _mark_as_seen(self, article: Dict):
        """Пометить как просмотренное"""
        self.seen_urls.add(article['url'])
        
        title = article['title'].lower()
        title_normalized = re.sub(r'[^\w\s]', '', title)
        title_hash = hashlib.md5(title_normalized.encode()).hexdigest()
        self.seen_hashes.add(title_hash)
        
        if len(self.seen_urls) > 10000:
            to_remove = int(len(self.seen_urls) * 0.2)
            self.seen_urls = set(list(self.seen_urls)[to_remove:])
            self.seen_hashes = set(list(self.seen_hashes)[to_remove:])
    
    async def cleanup(self):
        """Очистка ресурсов"""
        print("\n⏹️  [NEWS] Cleanup processor...")
        self.shutdown_requested = True
        
        try:
            if hasattr(self, 'database'):
                await self.database.close()
        except Exception as e:
            print(f"⚠️  [NEWS] Cleanup error: {e}")


__all__ = ['NewsProcessor']