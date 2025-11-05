# app/news/processor.py - Production-Ready News Processor v4.4

import asyncio
import hashlib
import traceback
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set, Any, Tuple
from collections import defaultdict
from pathlib import Path

import aiohttp
import feedparser
from bs4 import BeautifulSoup

try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

from app.config import (
    config,
    NEWS_SOURCES,
    FETCH_INTERVAL,
    POSTS_PER_HOUR_CAP,
    MIN_CONFIDENCE_SCORE,
    NEWS_ENABLED,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
)

from app.news.ai_handler import AIHandler
from app.news.content_parser import ContentParser
from app.news.database import NewsDatabase
from app.news.telegram_poster import NewsTelegramPoster


class NewsMetrics:
    """Метрики работы новостного процессора"""
    
    def __init__(self):
        self.cycles_completed = 0
        self.articles_fetched = 0
        self.articles_processed = 0
        self.articles_published = 0
        self.articles_filtered = 0
        self.articles_skipped = 0
        self.articles_translated = 0
        self.errors = 0
        
        self.fetch_errors_by_source = defaultdict(int)
        self.fetch_times = []
        self.fetch_counts_by_source = defaultdict(int)
        self.published_by_source = defaultdict(int)
        
        self.total_fetch_time = 0.0
        self.total_process_time = 0.0
        self.total_publish_time = 0.0
        
        self.start_time = datetime.now(timezone.utc)
        self.last_publish_time = None
    
    def record_fetch(self, source: str, count: int, duration: float, success: bool):
        """Записать результат фетча"""
        if success:
            self.articles_fetched += count
            self.fetch_times.append(duration)
            self.fetch_counts_by_source[source] += count
            self.total_fetch_time += duration
        else:
            self.fetch_errors_by_source[source] += 1
            self.errors += 1
    
    def record_published(self, source: str):
        """Записать публикацию"""
        self.published_by_source[source] += 1
        self.last_publish_time = datetime.now(timezone.utc)
    
    def record_translated(self):
        """Записать перевод"""
        self.articles_translated += 1
    
    def get_uptime(self) -> float:
        """Получить время работы в секундах"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def get_success_rate(self) -> float:
        """Получить процент успешных публикаций"""
        if self.articles_processed == 0:
            return 0.0
        return (self.articles_published / self.articles_processed) * 100
    
    def get_average_fetch_time(self) -> float:
        """Получить среднее время фетча"""
        if not self.fetch_times:
            return 0.0
        return sum(self.fetch_times) / len(self.fetch_times)
    
    def get_articles_per_hour(self) -> float:
        """Получить количество статей в час"""
        uptime_hours = self.get_uptime() / 3600
        if uptime_hours == 0:
            return 0.0
        return self.articles_published / uptime_hours
    
    def to_dict(self) -> Dict[str, Any]:
        """Экспорт метрик в словарь"""
        return {
            'cycles_completed': self.cycles_completed,
            'articles_fetched': self.articles_fetched,
            'articles_processed': self.articles_processed,
            'articles_published': self.articles_published,
            'articles_filtered': self.articles_filtered,
            'articles_skipped': self.articles_skipped,
            'articles_translated': self.articles_translated,
            'errors': self.errors,
            'success_rate': self.get_success_rate(),
            'uptime_seconds': self.get_uptime(),
            'average_fetch_time': self.get_average_fetch_time(),
            'articles_per_hour': self.get_articles_per_hour(),
            'fetch_counts_by_source': dict(self.fetch_counts_by_source),
            'published_by_source': dict(self.published_by_source),
            'fetch_errors_by_source': dict(self.fetch_errors_by_source),
        }


class NewsProcessor:
    """Production-ready новостной процессор"""
    
    def __init__(self):
        """Инициализация процессора"""
        
        print("\n" + "="*80)
        print("📰 NEWS PROCESSOR v4.4 - PRODUCTION INITIALIZATION")
        print("="*80 + "\n")
        
        if not NEWS_ENABLED:
            print("⚠️ [NEWS] News processing disabled in config")
            self._initialized = False
            return
        
        if not NEWS_SOURCES:
            print("❌ [NEWS] No news sources configured")
            self._initialized = False
            return
        
        has_ai_key = bool(OPENAI_API_KEY or ANTHROPIC_API_KEY or GEMINI_API_KEY)
        if not has_ai_key:
            print("⚠️ [NEWS] No AI API keys configured")
        
        try:
            self.ai_handler = AIHandler()
            print("✅ AI Handler initialized")
        except Exception as e:
            print(f"❌ AI Handler failed: {e}")
            traceback.print_exc()
            self._initialized = False
            return
        
        try:
            self.content_parser = ContentParser()
            print("✅ Content Parser initialized")
        except Exception as e:
            print(f"⚠️ Content Parser failed: {e}")
            self.content_parser = None
        
        try:
            self.database = NewsDatabase()
            print("✅ Database initialized")
        except Exception as e:
            print(f"❌ Database failed: {e}")
            traceback.print_exc()
            self._initialized = False
            return
        
        try:
            self.telegram = NewsTelegramPoster()
            print("✅ Telegram Poster initialized")
        except Exception as e:
            print(f"❌ Telegram Poster failed: {e}")
            traceback.print_exc()
            self._initialized = False
            return
        
        self.metrics = NewsMetrics()
        
        self.fetch_timeout = config.news.max_retries * 10 if hasattr(config.news, 'max_retries') else 30
        self.max_fetch_retries = config.news.max_retries if hasattr(config.news, 'max_retries') else 3
        self.retry_delay_base = config.news.retry_delay_seconds if hasattr(config.news, 'retry_delay_seconds') else 3
        
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.cache_size_limit = 10000
        
        self.last_fetch_times: Dict[str, datetime] = {}
        self.min_fetch_interval = 5.0
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        self.current_ua_index = 0
        
        self.posts_this_hour = 0
        self.hour_start_time = datetime.now(timezone.utc)
        
        self.shutdown_requested = False
        self._baseline_loaded = False
        self._database_initialized = False
        self._initialized = True
        
        print("✅ News Processor v4.4 initialized")
        print(f"   • Sources: {len(NEWS_SOURCES)}")
        print(f"   • Fetch interval: {FETCH_INTERVAL}s")
        print(f"   • Posts per hour cap: {POSTS_PER_HOUR_CAP}")
        print(f"   • Min confidence: {MIN_CONFIDENCE_SCORE}/100")
        print(f"   • Translation: ✅ Enabled (EN→RU)")
        print(f"   • Brotli support: {'✅' if BROTLI_AVAILABLE else '❌'}")
        print(f"   • AI Provider: {config.get_ai_provider() or 'None'}")
        print(f"   • Database: {config.database.type}")
        print()
    
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
            print(f"⚠️ [NEWS] Database initialization failed: {e}")
            traceback.print_exc()
    
    async def run_cycle(self):
        """Выполнить один цикл обработки новостей"""
        
        if not self.is_initialized:
            print("⚠️ [NEWS] Processor not initialized, skipping cycle")
            return
        
        if not self._database_initialized:
            await self.initialize_database()
        
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
        
        cycle_start = datetime.now(timezone.utc)
        
        print("\n" + "#"*80)
        print(f"📰 NEWS CYCLE #{self.metrics.cycles_completed + 1} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*80 + "\n")
        
        self._reset_hourly_limit_if_needed()
        
        articles = await self._fetch_all_sources()
        
        if not articles:
            print("👍 [NEWS] No new articles in this cycle")
            self.metrics.cycles_completed += 1
            return
        
        print(f"\n📊 [NEWS] Fetched {len(articles)} new articles")
        
        process_start = datetime.now(timezone.utc)
        candidates = await self._process_articles(articles)
        process_duration = (datetime.now(timezone.utc) - process_start).total_seconds()
        self.metrics.total_process_time += process_duration
        
        if not candidates:
            print("⚠️ [NEWS] No candidates for publication (low score)")
            self.metrics.cycles_completed += 1
            return
        
        print(f"✅ [NEWS] {len(candidates)} candidates passed filters")
        
        publish_start = datetime.now(timezone.utc)
        published = await self._publish_best(candidates)
        publish_duration = (datetime.now(timezone.utc) - publish_start).total_seconds()
        self.metrics.total_publish_time += publish_duration
        
        print(f"📤 [NEWS] Published: {published}/{len(candidates)}")
        
        self.metrics.cycles_completed += 1
        
        cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        print(f"\n⏱️ [NEWS] Cycle completed in {cycle_duration:.1f}s")
        print(f"   Fetch: {self.metrics.total_fetch_time:.1f}s | Process: {process_duration:.1f}s | Publish: {publish_duration:.1f}s\n")
    
    async def process_cycle(self):
        """Alias для run_cycle для совместимости"""
        await self.run_cycle()
    
    async def run(self):
        """Запустить главный цикл (standalone mode)"""
        
        if not self.is_initialized:
            print("❌ [NEWS] Processor not initialized, cannot run")
            await asyncio.sleep(300)
            return
        
        print("🚀 [NEWS] Starting main loop (standalone mode)\n")
        
        if not self._database_initialized:
            await self.initialize_database()
        
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
        
        while not self.shutdown_requested:
            try:
                await self.run_cycle()
                
                await asyncio.sleep(FETCH_INTERVAL)
            
            except asyncio.CancelledError:
                print("\n⏹️ [NEWS] Received stop signal")
                break
            
            except Exception as e:
                self.metrics.errors += 1
                print(f"\n❌ [NEWS] Critical error in cycle:")
                print(f"   {e}")
                traceback.print_exc()
                
                await asyncio.sleep(60)
    
    async def _initial_baseline(self):
        """Загрузить начальное состояние (baseline)"""
        
        print("📊 [BASELINE] Loading initial state...\n")
        
        try:
            articles = await self._fetch_all_sources()
            
            for article in articles:
                self._mark_as_seen(article)
            
            print(f"✅ Baseline created: {len(articles)} articles in database")
        except Exception as e:
            print(f"⚠️ [BASELINE] Error: {e}")
            traceback.print_exc()
        
        print("="*80 + "\n")
    
    async def _fetch_all_sources(self) -> List[Dict]:
        """Получить статьи из всех источников"""
        
        sorted_sources = sorted(
            NEWS_SOURCES,
            key=lambda s: s.get('priority', 5),
            reverse=True
        )
        
        for source in sorted_sources[:6]:
            print(f"📡 [FETCH] {source['name']} (priority: {source.get('priority', 5)})")
        
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_with_semaphore(source):
            async with semaphore:
                return await self._fetch_source(
                    url=source['url'],
                    name=source['name'],
                    priority=source.get('priority', 5),
                    language=source.get('language', 'en')
                )
        
        tasks = [fetch_with_semaphore(source) for source in sorted_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            if result:
                all_articles.extend(result)
        
        return all_articles
    
    async def _fetch_source(
        self,
        url: str,
        name: str,
        priority: int,
        language: str = 'en'
    ) -> List[Dict]:
        """Получить статьи из одного источника"""
        
        await self._respect_rate_limit(name)
        
        start_time = datetime.now(timezone.utc)
        
        for attempt in range(self.max_fetch_retries):
            try:
                articles = await self._fetch_with_brotli(url, name, language, attempt)
                
                if articles is not None:
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    self.metrics.record_fetch(name, len(articles), duration, True)
                    
                    if len(articles) > 0:
                        print(f"✅ [FETCH] {name}: {len(articles)} new")
                    
                    return articles
            
            except asyncio.TimeoutError:
                if attempt < self.max_fetch_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    print(f"⏱️ [FETCH] Timeout: {name}")
                    self.metrics.record_fetch(name, 0, 0, False)
                    return []
            
            except aiohttp.ClientError as e:
                error_msg = str(e)
                
                if 'brotli' in error_msg.lower() or 'br' in error_msg.lower():
                    try:
                        articles = await self._fetch_without_compression(url, name, language)
                        if articles:
                            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                            self.metrics.record_fetch(name, len(articles), duration, True)
                            return articles
                    except Exception as fallback_error:
                        pass
                
                if attempt == self.max_fetch_retries - 1:
                    error_type = type(e).__name__
                    print(f"❌ [FETCH] {name}: {error_type}")
                
                if attempt < self.max_fetch_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    self.metrics.record_fetch(name, 0, 0, False)
                    return []
            
            except Exception as e:
                if attempt == self.max_fetch_retries - 1:
                    error_type = type(e).__name__
                    print(f"❌ [FETCH] Unexpected {name}: {error_type}")
                self.metrics.record_fetch(name, 0, 0, False)
                return []
        
        return []
    
    async def _fetch_with_brotli(
        self,
        url: str,
        name: str,
        language: str,
        attempt: int
    ) -> Optional[List[Dict]]:
        """Получить данные с поддержкой Brotli"""
        
        timeout_obj = aiohttp.ClientTimeout(
            total=self.fetch_timeout,
            connect=10,
            sock_read=self.fetch_timeout - 10
        )
        
        headers = {
            'User-Agent': self._get_next_user_agent(),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate' + (', br' if BROTLI_AVAILABLE else ''),
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1'
        }
        
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=2,
            ttl_dns_cache=300,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_obj,
            headers=headers
        ) as session:
            
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                try:
                    content = await response.read()
                    
                    try:
                        text = content.decode('utf-8')
                    except UnicodeDecodeError:
                        for encoding in ['utf-8', 'windows-1251', 'iso-8859-1', 'cp1252']:
                            try:
                                text = content.decode(encoding)
                                break
                            except:
                                continue
                        else:
                            text = content.decode('utf-8', errors='ignore')
                
                except Exception as e:
                    return None
                
                return self._parse_rss(text, name, language)
    
    async def _fetch_without_compression(self, url: str, name: str, language: str) -> List[Dict]:
        """Получить данные без сжатия"""
        
        timeout_obj = aiohttp.ClientTimeout(total=self.fetch_timeout)
        
        headers = {
            'User-Agent': self._get_next_user_agent(),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        connector = aiohttp.TCPConnector(ssl=False, force_close=True)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_obj,
            headers=headers
        ) as session:
            
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                text = await response.text(encoding='utf-8', errors='ignore')
                return self._parse_rss(text, name, language)
    
    def _parse_rss(self, content: str, source_name: str, language: str) -> List[Dict]:
        """Распарсить RSS feed"""
        
        try:
            feed = feedparser.parse(content)
            
            if not feed.entries:
                return []
            
            articles = []
            
            for entry in feed.entries:
                try:
                    article = self._extract_article(entry, source_name, language)
                    
                    if article and self._is_valid_article(article):
                        if not self._is_duplicate(article):
                            articles.append(article)
                
                except Exception as extract_error:
                    continue
            
            return articles
        
        except Exception as e:
            return []
    
    def _extract_article(self, entry, source: str, language: str) -> Optional[Dict]:
        """Извлечь данные статьи из RSS entry"""
        
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            url = entry.get('link', '').strip()
            if not url:
                return None
            
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    from time import mktime
                    published = datetime.fromtimestamp(
                        mktime(entry.published_parsed),
                        tz=timezone.utc
                    )
                except:
                    pass
            
            if not published:
                published = datetime.now(timezone.utc)
            
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            
            if summary:
                if not summary.startswith('<') and not summary.startswith('/'):
                    try:
                        soup = BeautifulSoup(summary, 'html.parser')
                        summary = soup.get_text().strip()
                    except:
                        summary = summary.strip()
                else:
                    summary = re.sub(r'<[^>]+>', '', summary).strip()
            
            image_url = None
            if hasattr(entry, 'media_content') and entry.media_content:
                try:
                    image_url = entry.media_content[0].get('url')
                except:
                    pass
            
            if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
                try:
                    for enclosure in entry.enclosures:
                        if 'image' in enclosure.get('type', ''):
                            image_url = enclosure.get('href')
                            break
                except:
                    pass
            
            return {
                'title': title,
                'url': url,
                'link': url,
                'normalized_link': url,
                'published': published,
                'published_at': published,
                'summary': summary[:500] if summary else '',
                'description': summary[:500] if summary else '',
                'source': source,
                'source_feed': source,
                'image_url': image_url,
                'has_image': bool(image_url),
                'language': language
            }
        
        except Exception as e:
            return None
    
    def _is_valid_article(self, article: Dict) -> bool:
        """Проверить валидность статьи"""
        
        if not article.get('title'):
            return False
        
        if not article.get('url'):
            return False
        
        if len(article['title']) < 10:
            return False
        
        if not article['url'].startswith('http'):
            return False
        
        return True
    
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
        url = article['url']
        self.seen_urls.add(url)
        
        title = article['title'].lower()
        title_normalized = re.sub(r'[^\w\s]', '', title)
        title_hash = hashlib.md5(title_normalized.encode()).hexdigest()
        self.seen_hashes.add(title_hash)
        
        if len(self.seen_urls) > self.cache_size_limit:
            to_remove = int(len(self.seen_urls) * 0.2)
            self.seen_urls = set(list(self.seen_urls)[to_remove:])
            self.seen_hashes = set(list(self.seen_hashes)[to_remove:])
    
    async def _process_articles(self, articles: List[Dict]) -> List[Dict]:
        """Обработать статьи через AI"""
        
        candidates = []
        
        for article in articles:
            try:
                analysis = await self.ai_handler.analyze_article(article)
                
                if not analysis:
                    self.metrics.articles_filtered += 1
                    continue
                
                score = analysis.get('score', 0)
                
                if score < MIN_CONFIDENCE_SCORE:
                    self.metrics.articles_filtered += 1
                    continue
                
                article['ai_analysis'] = analysis
                article['ai_score'] = score
                article['ai_provider'] = analysis.get('provider')
                candidates.append(article)
                
                self.metrics.articles_processed += 1
            
            except Exception as e:
                self.metrics.articles_filtered += 1
                continue
        
        return candidates
    
    async def _translate_if_needed(self, text: str, language: str) -> str:
        """Перевести если нужно"""
        
        if language == 'ru':
            return text
        
        if not hasattr(self.ai_handler, 'translate_text'):
            return text
        
        try:
            translated = await self.ai_handler.translate_text(text, source_lang=language, target_lang='ru')
            if translated:
                self.metrics.record_translated()
                return translated
        except Exception as e:
            pass
        
        return text
    
    async def _publish_best(self, candidates: List[Dict]) -> int:
        """Опубликовать лучшие статьи"""
        
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get('ai_analysis', {}).get('score', 0),
            reverse=True
        )
        
        published = 0
        available_slots = self._get_available_publish_slots()
        
        if available_slots <= 0:
            print(f"⚠️ [NEWS] Hourly limit reached ({self.posts_this_hour}/{POSTS_PER_HOUR_CAP})")
            return 0
        
        publish_count = min(len(sorted_candidates), available_slots)
        
        for candidate in sorted_candidates[:publish_count]:
            try:
                success = await self._publish_article(candidate)
                
                if success:
                    published += 1
                    self.posts_this_hour += 1
                    self.metrics.articles_published += 1
                    self.metrics.record_published(candidate.get('source', 'Unknown'))
                    
                    self._mark_as_seen(candidate)
                    
                    try:
                        await self.database.save_article(
                            link=candidate['url'],
                            normalized_link=candidate['url'],
                            source_feed=candidate.get('source_feed', candidate.get('source', 'Unknown')),
                            title=candidate['title'],
                            has_image=candidate.get('has_image', False),
                            ai_provider=candidate.get('ai_provider'),
                            status='success'
                        )
                    except Exception as db_error:
                        print(f"⚠️ [DB] Failed to save: {db_error}")
                    
                    title_preview = candidate['title'][:60]
                    score = candidate.get('ai_score', 0)
                    print(f"✅ [PUBLISHED] {title_preview}... (score: {score})")
                    
                    await asyncio.sleep(5)
                else:
                    title_preview = candidate['title'][:60]
                    print(f"❌ [FAILED] {title_preview}...")
            
            except Exception as e:
                print(f"⚠️ [PUBLISH] Error: {e}")
                traceback.print_exc()
                continue
        
        return published
    
    async def _publish_article(self, article: Dict) -> bool:
        """Опубликовать одну статью"""
        
        try:
            title = article['title']
            url = article.get('url') or article.get('link')
            summary = article.get('summary') or article.get('description', '')
            source = article.get('source', 'Unknown')
            score = article.get('ai_score', 0)
            language = article.get('language', 'en')
            
            if language != 'ru':
                title = await self._translate_if_needed(title, language)
                if summary:
                    summary = await self._translate_if_needed(summary, language)
            
            analysis = article.get('ai_analysis', {})
            sentiment = analysis.get('sentiment', 'neutral')
            
            sentiment_emoji_map = {
                'positive': '🚀',
                'bullish': '📈',
                'negative': '📉',
                'bearish': '🔻',
                'neutral': '📊'
            }
            sentiment_emoji = sentiment_emoji_map.get(sentiment, '📰')
            
            message_text = f"{sentiment_emoji} {title}\n\n"
            
            if summary:
                clean_summary = summary[:300].strip()
                if clean_summary:
                    message_text += f"{clean_summary}...\n\n"
            
            message_text += f"Источник: {source}\n"
            message_text += f"Оценка AI: {score}/100"
            
            image_url = article.get('image_url')
            
            success = await self.telegram.post(
                text=message_text,
                link=url,
                image_url=image_url if image_url else None
            )
            
            return success
        
        except Exception as e:
            print(f"⚠️ [PUBLISH] Exception: {e}")
            traceback.print_exc()
            return False
    
    def _reset_hourly_limit_if_needed(self):
        """Сбросить почасовой лимит если нужно"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.hour_start_time).total_seconds()
        
        if elapsed >= 3600:
            self.posts_this_hour = 0
            self.hour_start_time = now
    
    def _get_available_publish_slots(self) -> int:
        """Получить доступные слоты для публикации"""
        return max(0, POSTS_PER_HOUR_CAP - self.posts_this_hour)
    
    async def _respect_rate_limit(self, source_name: str):
        """Соблюдать rate limit для источника"""
        
        if source_name in self.last_fetch_times:
            elapsed = (datetime.now(timezone.utc) - self.last_fetch_times[source_name]).total_seconds()
            
            if elapsed < self.min_fetch_interval:
                await asyncio.sleep(self.min_fetch_interval - elapsed)
        
        self.last_fetch_times[source_name] = datetime.now(timezone.utc)
    
    def _get_next_user_agent(self) -> str:
        """Получить следующий User-Agent"""
        ua = self.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return ua
    
    async def cleanup(self):
        """Очистка ресурсов"""
        
        print("\n⏹️ [NEWS] Cleanup processor...")
        self.shutdown_requested = True
        
        try:
            await self.database.close()
        except Exception as e:
            print(f"⚠️ [NEWS] Database cleanup error: {e}")
        
        self._print_stats()
    
    def _print_stats(self):
        """Вывести статистику"""
        
        print("\n" + "="*80)
        print("📊 NEWS PROCESSOR STATISTICS v4.4")
        print("="*80)
        print(f"Uptime: {self.metrics.get_uptime()/3600:.1f}h")
        print(f"Cycles: {self.metrics.cycles_completed}")
        print(f"Articles Fetched: {self.metrics.articles_fetched}")
        print(f"Articles Processed: {self.metrics.articles_processed}")
        print(f"Articles Published: {self.metrics.articles_published}")
        print(f"Articles Filtered: {self.metrics.articles_filtered}")
        print(f"Articles Translated: {self.metrics.articles_translated}")
        print(f"Success Rate: {self.metrics.get_success_rate():.1f}%")
        print(f"Articles/Hour: {self.metrics.get_articles_per_hour():.1f}")
        print(f"Avg Fetch Time: {self.metrics.get_average_fetch_time():.2f}s")
        print(f"Errors: {self.metrics.errors}")
        
        if self.metrics.published_by_source:
            print("\nTop Publishing Sources:")
            sorted_published = sorted(
                self.metrics.published_by_source.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for source, count in sorted_published[:5]:
                print(f"  • {source}: {count} articles")
        
        if self.metrics.fetch_errors_by_source:
            print("\nTop Error Sources:")
            sorted_errors = sorted(
                self.metrics.fetch_errors_by_source.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for source, count in sorted_errors[:5]:
                print(f"  • {source}: {count} errors")
        
        try:
            ai_stats = self.ai_handler.get_stats()
            print("\nAI Handler Stats:")
            print(f"  • Provider: {ai_stats.get('provider', 'unknown')}")
            print(f"  • Requests: {ai_stats.get('total_requests', 0)}")
            print(f"  • Success Rate: {ai_stats.get('success_rate', 0):.1f}%")
        except:
            pass
        
        try:
            tg_stats = self.telegram.get_stats()
            print("\nTelegram Stats:")
            print(f"  • Total Posts: {tg_stats.get('total_posts', 0)}")
            print(f"  • Success Rate: {tg_stats.get('success_rate', 0):.1f}%")
        except:
            pass
        
        print("="*80 + "\n")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получить метрики"""
        return self.metrics.to_dict()


__all__ = ['NewsProcessor', 'NewsMetrics']