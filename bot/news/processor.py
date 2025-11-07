# bot/news/processor.py
"""
News Processor v5.0 - Production Ready
"""

import asyncio
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.config import config
from bot.news.fetcher import NewsFetcher
from bot.news.deduplicator import ArticleDeduplicator


class NewsProcessor:
    """Production-ready новостной процессор"""
    
    def __init__(self):
        """Инициализация процессора"""
        
        print("\n" + "="*80)
        print("📰 NEWS PROCESSOR v5.0 - INITIALIZATION")
        print("="*80 + "\n")
        
        self._initialized = False
        self._database_initialized = False
        self._baseline_loaded = False
        self.shutdown_requested = False
        
        if not self._check_prerequisites():
            return
        
        try:
            self.fetcher = NewsFetcher()
            self.deduplicator = ArticleDeduplicator()
            
            self._load_optional_components()
            
            self.posts_this_hour = 0
            self.hour_start_time = datetime.now(timezone.utc)
            
            print("✅ Core components initialized")
            print(f"   • Sources: {len(config.news.sources)}")
            print(f"   • Fetch interval: {config.news.fetch_interval}s")
            print(f"   • Posts per hour cap: {config.news.posts_per_hour_cap}")
            print()
            
            self._initialized = True
        
        except Exception as e:
            print(f"❌ [NEWS] Initialization failed: {e}")
            traceback.print_exc()
            self._initialized = False
    
    def _check_prerequisites(self) -> bool:
        """Проверка предварительных условий"""
        if not config.is_feature_enabled('news'):
            print("⚠️  [NEWS] News processing disabled in config")
            return False
        
        if not hasattr(config, 'news'):
            print("❌ [NEWS] config.news not found")
            return False
        
        if not hasattr(config.news, 'sources') or not config.news.sources:
            print("❌ [NEWS] No news sources configured")
            return False
        
        return True
    
    def _load_optional_components(self):
        """Загрузка опциональных компонентов"""
        try:
            from bot.ai_handler import AIHandler
            self.ai_handler = AIHandler()
            print("   ✅ AI Handler loaded")
        except ImportError:
            print("   ⚠️  AI Handler not available (disabled)")
            self.ai_handler = None
        except Exception as e:
            print(f"   ⚠️  AI Handler error: {e}")
            self.ai_handler = None
        
        try:
            from bot.content_parser import ContentParser
            self.content_parser = ContentParser()
            print("   ✅ Content Parser loaded")
        except ImportError:
            print("   ⚠️  Content Parser not available")
            self.content_parser = None
        except Exception as e:
            print(f"   ⚠️  Content Parser error: {e}")
            self.content_parser = None
        
        try:
            from bot.database import NewsDatabase
            self.database = NewsDatabase()
            print("   ✅ Database loaded")
        except ImportError:
            print("   ⚠️  Database not available")
            self.database = None
        except Exception as e:
            print(f"   ⚠️  Database error: {e}")
            self.database = None
        
        try:
            from bot.telegram_poster import NewsTelegramPoster
            self.telegram = NewsTelegramPoster()
            print("   ✅ Telegram Poster loaded")
        except ImportError:
            print("   ⚠️  Telegram Poster not available")
            self.telegram = None
        except Exception as e:
            print(f"   ⚠️  Telegram Poster error: {e}")
            self.telegram = None
    
    @property
    def is_initialized(self) -> bool:
        """Проверить инициализацию"""
        return getattr(self, '_initialized', False)
    
    async def initialize_database(self):
        """Инициализировать базу данных"""
        if self._database_initialized or not self.database:
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
        
        if not self._database_initialized and self.database:
            await self.initialize_database()
        
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
            return
        
        print(f"\n📰 [NEWS] Cycle at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")
        
        articles = await self._fetch_all_sources()
        
        if not articles:
            print("✅ [NEWS] No new articles")
            return
        
        print(f"📊 [NEWS] Fetched {len(articles)} new articles")
        
        new_articles = self._filter_duplicates(articles)
        
        if not new_articles:
            print("✅ [NEWS] All articles are duplicates")
            return
        
        print(f"🆕 [NEWS] {len(new_articles)} new unique articles")
        
        for article in new_articles[:3]:
            self.deduplicator.mark_as_seen(article)
        
        await asyncio.sleep(1)
    
    async def _initial_baseline(self):
        """Загрузить начальное состояние"""
        print("📊 [BASELINE] Loading initial state...")
        
        try:
            articles = await self._fetch_all_sources()
            
            for article in articles:
                self.deduplicator.mark_as_seen(article)
            
            stats = self.deduplicator.get_stats()
            print(f"✅ [BASELINE] Created: {stats['seen_urls']} URLs, {stats['seen_hashes']} hashes")
        
        except Exception as e:
            print(f"⚠️  [BASELINE] Error: {e}")
            traceback.print_exc()
    
    async def _fetch_all_sources(self) -> List[Dict]:
        """Получить статьи из всех источников"""
        all_articles = []
        
        sources = config.news.sources[:5]
        
        tasks = [self.fetcher.fetch_source(source) for source in sources]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = sources[i].get('name', 'Unknown')
                print(f"❌ [FETCH] {source_name}: {result}")
            elif result:
                all_articles.extend(result)
        
        return all_articles
    
    def _filter_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Фильтрует дубликаты"""
        return [
            article for article in articles
            if not self.deduplicator.is_duplicate(article)
        ]
    
    async def cleanup(self):
        """Очистка ресурсов"""
        print("\n⏹️  [NEWS] Cleanup processor...")
        self.shutdown_requested = True
        
        try:
            if self.database and hasattr(self.database, 'close'):
                await self.database.close()
                print("   ✓ Database closed")
        except Exception as e:
            print(f"⚠️  [NEWS] Cleanup error: {e}")


__all__ = ['NewsProcessor']