"""
NEWS PROCESSOR v3.2 - Complete Edition with Enhanced Error Handling
AI-powered crypto news aggregation and publishing

ВОЗМОЖНОСТИ:
✅ Multi-source RSS aggregation with Brotli support
✅ AI content analysis
✅ Smart gate filtering
✅ Duplicate detection
✅ Priority-based publishing
✅ Rate limiting
✅ Error recovery with retry
✅ Comprehensive metrics
✅ Graceful degradation if dependencies unavailable
✅ ИСПРАВЛЕНО v3.2: Added run_cycle() and process_cycle() methods for integration
"""

import asyncio
import hashlib
import traceback
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set
from collections import defaultdict
from pathlib import Path

import aiohttp
import feedparser
from bs4 import BeautifulSoup

try:
    import brotli
    BROTLI_AVAILABLE = True
    print("✅ [NEWS] Brotli compression support enabled")
except ImportError:
    BROTLI_AVAILABLE = False
    print("⚠️ [NEWS] Brotli not available - install: pip install brotli brotlipy")

# Импорты зависимостей с graceful fallback
try:
    from bot.config import NEWS_SOURCES, FETCH_INTERVAL, POSTS_PER_HOUR_CAP
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [NEWS] Config import error: {e}")
    CONFIG_AVAILABLE = False
    NEWS_SOURCES = []
    FETCH_INTERVAL = 300
    POSTS_PER_HOUR_CAP = 3

try:
    from bot.ai_handler import AIHandler
    AI_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [NEWS] AIHandler import error: {e}")
    AI_HANDLER_AVAILABLE = False
    AIHandler = None

try:
    from bot.content_parser import ContentParser
    CONTENT_PARSER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [NEWS] ContentParser import error: {e}")
    CONTENT_PARSER_AVAILABLE = False
    ContentParser = None

try:
    from bot.database import NewsDatabase
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [NEWS] NewsDatabase import error: {e}")
    DATABASE_AVAILABLE = False
    NewsDatabase = None

try:
    from bot.telegram_poster import TelegramPoster
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ [NEWS] TelegramPoster import error: {e}")
    TELEGRAM_AVAILABLE = False
    TelegramPoster = None


class NewsMetrics:
    """Метрики обработки новостей"""
    
    def __init__(self):
        self.cycles_completed = 0
        self.articles_fetched = 0
        self.articles_processed = 0
        self.articles_published = 0
        self.articles_filtered = 0
        self.errors = 0
        
        self.fetch_errors_by_source = defaultdict(int)
        self.fetch_times = []
        
        self.start_time = datetime.now(timezone.utc)
    
    def record_fetch(self, source: str, count: int, duration: float, success: bool):
        """Регистрация fetch операции"""
        if success:
            self.articles_fetched += count
            self.fetch_times.append(duration)
        else:
            self.fetch_errors_by_source[source] += 1
            self.errors += 1
    
    def get_uptime(self) -> float:
        """Время работы в секундах"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def get_success_rate(self) -> float:
        """Процент успешно опубликованных статей"""
        if self.articles_processed == 0:
            return 0.0
        return (self.articles_published / self.articles_processed) * 100


class DummyAIHandler:
    """Заглушка для AI Handler если он недоступен"""
    
    async def analyze_article(self, article: Dict) -> Optional[Dict]:
        """Возвращает базовый анализ"""
        return {
            'score': 75,
            'sentiment': 'neutral',
            'relevance': 'medium'
        }


class DummyDatabase:
    """Заглушка для Database если она недоступна"""
    
    async def save_article(self, article: Dict):
        """Ничего не делает"""
        pass


class DummyTelegram:
    """Заглушка для Telegram если он недоступен"""
    
    async def post_article(self, article: Dict) -> bool:
        """Симулирует успешную публикацию"""
        print(f"📤 [TELEGRAM DUMMY] Would post: {article.get('title', 'No title')[:50]}")
        return True


class NewsProcessor:
    """
    Главный процессор новостей
    
    Интегрирует:
    - RSS fetching с Brotli поддержкой
    - AI анализ контента
    - Smart gate фильтрацию
    - Telegram публикацию
    
    НОВОЕ v3.2: Методы для интеграции с main.py:
    - run_cycle() - выполняет один цикл обработки
    - process_cycle() - алиас для run_cycle()
    - run() - бесконечный цикл (для standalone использования)
    """
    
    def __init__(self):
        """Инициализация процессора"""
        
        print("\n" + "="*80)
        print("📰 NEWS PROCESSOR - INITIALIZATION v3.2")
        print("="*80 + "\n")
        
        # Проверяем доступность конфига
        if not CONFIG_AVAILABLE or not NEWS_SOURCES:
            print("❌ [NEWS] Config not available or empty NEWS_SOURCES")
            print("   News Processor will be disabled")
            self._initialized = False
            return
        
        # Компоненты с fallback
        if AI_HANDLER_AVAILABLE and AIHandler:
            try:
                self.ai_handler = AIHandler()
                print("✅ AI Handler loaded")
            except Exception as e:
                print(f"⚠️ AI Handler failed, using dummy: {e}")
                self.ai_handler = DummyAIHandler()
        else:
            print("⚠️ AI Handler unavailable, using dummy")
            self.ai_handler = DummyAIHandler()
        
        if CONTENT_PARSER_AVAILABLE and ContentParser:
            try:
                self.content_parser = ContentParser()
                print("✅ Content Parser loaded")
            except Exception as e:
                print(f"⚠️ Content Parser failed: {e}")
                self.content_parser = None
        else:
            self.content_parser = None
        
        if DATABASE_AVAILABLE and NewsDatabase:
            try:
                self.database = NewsDatabase()
                print("✅ Database loaded")
            except Exception as e:
                print(f"⚠️ Database failed, using dummy: {e}")
                self.database = DummyDatabase()
        else:
            print("⚠️ Database unavailable, using dummy")
            self.database = DummyDatabase()
        
        if TELEGRAM_AVAILABLE and TelegramPoster:
            try:
                self.telegram = TelegramPoster()
                print("✅ Telegram Poster loaded")
            except Exception as e:
                print(f"⚠️ Telegram failed, using dummy: {e}")
                self.telegram = DummyTelegram()
        else:
            print("⚠️ Telegram unavailable, using dummy")
            self.telegram = DummyTelegram()
        
        # Metrics
        self.metrics = NewsMetrics()
        
        # Fetch settings
        self.fetch_timeout = 30
        self.max_fetch_retries = 3
        
        # Cache для дедупликации
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        
        # Rate limiting
        self.last_fetch_times: Dict[str, datetime] = {}
        self.min_fetch_interval = 5.0
        
        # User agents для ротации
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        self.current_ua_index = 0
        
        # Shutdown flag
        self.shutdown_requested = False
        
        # Baseline loaded flag
        self._baseline_loaded = False
        
        # Initialization complete
        self._initialized = True
        
        print("✅ News Processor v3.2 инициализирован")
        print(f"   • Sources: {len(NEWS_SOURCES)}")
        print(f"   • Fetch interval: {FETCH_INTERVAL}s")
        print(f"   • Posts per hour cap: {POSTS_PER_HOUR_CAP}")
        print(f"   • Brotli support: {'✅' if BROTLI_AVAILABLE else '❌'}")
        print(f"   • AI Handler: {'✅' if AI_HANDLER_AVAILABLE else '⚠️ dummy'}")
        print(f"   • Database: {'✅' if DATABASE_AVAILABLE else '⚠️ dummy'}")
        print(f"   • Telegram: {'✅' if TELEGRAM_AVAILABLE else '⚠️ dummy'}")
        print(f"   • Available methods: run(), run_cycle(), process_cycle()")
        print()
    
    @property
    def is_initialized(self) -> bool:
        """Проверка инициализации"""
        return getattr(self, '_initialized', False)
    
    async def run_cycle(self):
        """
        НОВОЕ v3.2: Выполняет ОДИН цикл обработки новостей
        
        Этот метод предназначен для интеграции с main.py
        main.py вызывает его в своем цикле с контролируемыми интервалами
        
        Steps:
        1. Загружает baseline при первом запуске
        2. Fetch новостей из всех источников
        3. Обработка через AI
        4. Фильтрация через Smart Gate
        5. Публикация лучших
        
        Raises:
            Exception: При критических ошибках
        """
        
        if not self.is_initialized:
            print("⚠️ [NEWS] Processor not initialized, skipping cycle")
            return
        
        # Загружаем baseline при первом запуске
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
        
        cycle_start = datetime.now(timezone.utc)
        
        print("\n" + "#"*80)
        print(f"🔄 NEWS CYCLE #{self.metrics.cycles_completed + 1} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*80 + "\n")
        
        # 1. Fetch новостей
        articles = await self._fetch_all_sources()
        
        if not articles:
            print("⚠️ [NEWS] Нет новых статей в этом цикле")
            self.metrics.cycles_completed += 1
            return
        
        print(f"\n📊 [NEWS] Собрано {len(articles)} новых статей")
        
        # 2. Обработка и фильтрация
        candidates = await self._process_articles(articles)
        
        if not candidates:
            print("⚠️ [NEWS] Нет кандидатов для публикации")
            self.metrics.cycles_completed += 1
            return
        
        print(f"✅ [NEWS] {len(candidates)} кандидатов прошли фильтры")
        
        # 3. Публикация
        published = await self._publish_best(candidates)
        
        print(f"📤 [NEWS] Опубликовано: {published}/{len(candidates)}")
        
        # 4. Обновляем метрики
        self.metrics.cycles_completed += 1
        
        cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        print(f"\n⏱️ [NEWS] Цикл завершен за {cycle_duration:.1f}s\n")
    
    async def process_cycle(self):
        """
        НОВОЕ v3.2: Алиас для run_cycle()
        
        Этот метод существует для совместимости с main.py
        который может вызывать либо run_cycle(), либо process_cycle()
        """
        await self.run_cycle()
    
    async def run(self):
        """
        Главный цикл обработки новостей (бесконечный)
        
        ВНИМАНИЕ: Этот метод НЕ используется в интеграции с main.py
        Он предназначен для standalone запуска NewsProcessor
        
        Бесконечный цикл:
        1. Fetch новостей из всех источников
        2. Обработка через AI
        3. Фильтрация через Smart Gate
        4. Публикация лучших
        5. Пауза до следующего цикла
        """
        
        if not self.is_initialized:
            print("❌ [NEWS] Processor not initialized, cannot run")
            await asyncio.sleep(300)
            return
        
        print("🚀 [NEWS] Запуск главного цикла (standalone mode)\n")
        
        # Загружаем baseline при первом запуске
        if not self._baseline_loaded:
            await self._initial_baseline()
            self._baseline_loaded = True
        
        while not self.shutdown_requested:
            try:
                cycle_start = datetime.now(timezone.utc)
                
                print("\n" + "#"*80)
                print(f"🔄 ЦИКЛ #{self.metrics.cycles_completed + 1} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
                print("#"*80 + "\n")
                
                # 1. Fetch новостей
                articles = await self._fetch_all_sources()
                
                if not articles:
                    print("⚠️ [NEWS] Нет новых статей в этом цикле")
                    self.metrics.cycles_completed += 1
                    await asyncio.sleep(FETCH_INTERVAL)
                    continue
                
                print(f"\n📊 [NEWS] Собрано {len(articles)} новых статей")
                
                # 2. Обработка и фильтрация
                candidates = await self._process_articles(articles)
                
                if not candidates:
                    print("⚠️ [NEWS] Нет кандидатов для публикации")
                    self.metrics.cycles_completed += 1
                    await asyncio.sleep(FETCH_INTERVAL)
                    continue
                
                print(f"✅ [NEWS] {len(candidates)} кандидатов прошли фильтры")
                
                # 3. Публикация
                published = await self._publish_best(candidates)
                
                print(f"📤 [NEWS] Опубликовано: {published}/{len(candidates)}")
                
                # 4. Обновляем метрики
                self.metrics.cycles_completed += 1
                
                # 5. Пауза до следующего цикла
                cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
                
                if cycle_duration < FETCH_INTERVAL:
                    wait_time = FETCH_INTERVAL - cycle_duration
                    print(f"\n⏳ [NEWS] Пауза {wait_time:.0f}s до следующего цикла\n")
                    await asyncio.sleep(wait_time)
            
            except asyncio.CancelledError:
                print("\n⏹️ [NEWS] Получен сигнал остановки")
                break
            
            except Exception as e:
                self.metrics.errors += 1
                print(f"\n❌ [NEWS] Критическая ошибка в цикле:")
                print(f"   {e}")
                traceback.print_exc()
                
                # Пауза перед retry
                await asyncio.sleep(60)
    
    async def _initial_baseline(self):
        """Загрузка baseline при первом запуске"""
        
        print("📊 [BASELINE] Загрузка начального состояния...\n")
        
        try:
            articles = await self._fetch_all_sources()
            
            print(f"✅ Baseline создан: {len(articles)} статей в базе")
        except Exception as e:
            print(f"⚠️ [BASELINE] Ошибка: {e}")
        
        print("="*80 + "\n")
    
    async def _fetch_all_sources(self) -> List[Dict]:
        """
        Fetch всех RSS источников параллельно
        
        Returns:
            List[Dict]: Список новых статей
        """
        
        # Сортируем источники по приоритету
        sorted_sources = sorted(
            NEWS_SOURCES,
            key=lambda s: s.get('priority', 5),
            reverse=True
        )
        
        # Показываем что будем fetch-ить
        for source in sorted_sources[:6]:
            print(f"📡 [FETCH] {source['name']} (приоритет: {source.get('priority', 5)})")
        
        # Fetch параллельно (max 5 одновременно)
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_with_semaphore(source):
            async with semaphore:
                return await self._fetch_source(
                    url=source['url'],
                    name=source['name'],
                    priority=source.get('priority', 5)
                )
        
        tasks = [fetch_with_semaphore(source) for source in sorted_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем все статьи
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
        priority: int
    ) -> List[Dict]:
        """
        Fetch одного RSS источника с Brotli поддержкой
        
        Args:
            url: URL RSS фида
            name: Название источника
            priority: Приоритет
        
        Returns:
            List[Dict]: Список статей
        """
        
        # Rate limiting
        await self._respect_rate_limit(name)
        
        start_time = datetime.now(timezone.utc)
        
        # Retry loop
        for attempt in range(self.max_fetch_retries):
            try:
                articles = await self._fetch_with_brotli(url, name, attempt)
                
                if articles is not None:
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    self.metrics.record_fetch(name, len(articles), duration, True)
                    
                    if len(articles) > 0:
                        print(f"✅ [FETCH] {name}: {len(articles)} новых")
                    
                    return articles
            
            except asyncio.TimeoutError:
                if attempt < self.max_fetch_retries - 1:
                    delay = 5 * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    print(f"⏱️ [FETCH] Timeout: {name}")
                    self.metrics.record_fetch(name, 0, 0, False)
                    return []
            
            except aiohttp.ClientError as e:
                error_msg = str(e)
                
                # Специальная обработка Brotli
                if 'brotli' in error_msg.lower() or 'br' in error_msg.lower():
                    try:
                        articles = await self._fetch_without_compression(url, name)
                        if articles:
                            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                            self.metrics.record_fetch(name, len(articles), duration, True)
                            return articles
                    except:
                        pass
                
                # Короткий лог ошибки
                error_short = error_msg[:100] if len(error_msg) > 100 else error_msg
                
                if attempt == self.max_fetch_retries - 1:
                    print(f"❌ [FETCH] {name}: {type(e).__name__}")
                
                if attempt < self.max_fetch_retries - 1:
                    await asyncio.sleep(3 * (2 ** attempt))
                else:
                    self.metrics.record_fetch(name, 0, 0, False)
                    return []
            
            except Exception as e:
                if attempt == self.max_fetch_retries - 1:
                    print(f"❌ [FETCH] Unexpected {name}: {type(e).__name__}")
                self.metrics.record_fetch(name, 0, 0, False)
                return []
        
        return []
    
    async def _fetch_with_brotli(
        self,
        url: str,
        name: str,
        attempt: int
    ) -> Optional[List[Dict]]:
        """
        Fetch с полной поддержкой Brotli compression
        """
        
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
            'Connection': 'keep-alive'
        }
        
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=2,
            ttl_dns_cache=300,
            ssl=False
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
                        for encoding in ['utf-8', 'windows-1251', 'iso-8859-1']:
                            try:
                                text = content.decode(encoding)
                                break
                            except:
                                continue
                        else:
                            text = content.decode('utf-8', errors='ignore')
                
                except Exception as e:
                    return None
                
                return self._parse_rss(text, name)
    
    async def _fetch_without_compression(self, url: str, name: str) -> List[Dict]:
        """Fallback без compression"""
        
        timeout_obj = aiohttp.ClientTimeout(total=self.fetch_timeout)
        
        headers = {
            'User-Agent': self._get_next_user_agent(),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout_obj,
            headers=headers
        ) as session:
            
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                text = await response.text(encoding='utf-8', errors='ignore')
                return self._parse_rss(text, name)
    
    def _parse_rss(self, content: str, source_name: str) -> List[Dict]:
        """Парсинг RSS контента"""
        
        try:
            feed = feedparser.parse(content)
            
            if not feed.entries:
                return []
            
            articles = []
            
            for entry in feed.entries:
                try:
                    article = self._extract_article(entry, source_name)
                    
                    if article and self._is_valid_article(article):
                        if not self._is_duplicate(article):
                            articles.append(article)
                
                except:
                    continue
            
            return articles
        
        except Exception as e:
            return []
    
    def _extract_article(self, entry, source: str) -> Optional[Dict]:
        """Извлечение данных статьи"""
        
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            url = entry.get('link', '').strip()
            if not url:
                return None
            
            # Published date
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
            
            # Summary
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description
            
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                summary = soup.get_text().strip()
            
            return {
                'title': title,
                'url': url,
                'published': published,
                'summary': summary[:500],
                'source': source
            }
        
        except:
            return None
    
    def _is_valid_article(self, article: Dict) -> bool:
        """Валидация статьи"""
        
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
        """Проверка дубликата"""
        
        url = article['url']
        
        if url in self.seen_urls:
            return True
        
        title_hash = hashlib.md5(article['title'].lower().encode()).hexdigest()
        if title_hash in self.seen_hashes:
            return True
        
        self.seen_urls.add(url)
        self.seen_hashes.add(title_hash)
        
        # Ограничиваем cache
        if len(self.seen_urls) > 10000:
            to_remove = int(len(self.seen_urls) * 0.2)
            self.seen_urls = set(list(self.seen_urls)[to_remove:])
            self.seen_hashes = set(list(self.seen_hashes)[to_remove:])
        
        return False
    
    async def _process_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Обработка статей через AI и фильтры
        
        Returns:
            List[Dict]: Кандидаты для публикации
        """
        
        candidates = []
        
        for article in articles:
            try:
                # AI анализ
                analysis = await self.ai_handler.analyze_article(article)
                
                if not analysis:
                    continue
                
                # Smart Gate фильтр
                if analysis['score'] < 70:
                    self.metrics.articles_filtered += 1
                    continue
                
                # Добавляем к кандидатам
                article['ai_analysis'] = analysis
                candidates.append(article)
                
                self.metrics.articles_processed += 1
            
            except Exception as e:
                continue
        
        return candidates
    
    async def _publish_best(self, candidates: List[Dict]) -> int:
        """
        Публикация лучших кандидатов
        
        Returns:
            int: Количество опубликованных
        """
        
        # Сортируем по score
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get('ai_analysis', {}).get('score', 0),
            reverse=True
        )
        
        published = 0
        
        # Публикуем топ-N
        for candidate in sorted_candidates[:POSTS_PER_HOUR_CAP]:
            try:
                success = await self.telegram.post_article(candidate)
                
                if success:
                    published += 1
                    self.metrics.articles_published += 1
                    
                    # Сохраняем в БД
                    await self.database.save_article(candidate)
                    
                    # Пауза между публикациями
                    await asyncio.sleep(5)
            
            except Exception as e:
                print(f"⚠️ [PUBLISH] Ошибка: {e}")
                continue
        
        return published
    
    async def _respect_rate_limit(self, source_name: str):
        """Rate limiting для источника"""
        
        if source_name in self.last_fetch_times:
            elapsed = (datetime.now(timezone.utc) - self.last_fetch_times[source_name]).total_seconds()
            
            if elapsed < self.min_fetch_interval:
                await asyncio.sleep(self.min_fetch_interval - elapsed)
        
        self.last_fetch_times[source_name] = datetime.now(timezone.utc)
    
    def _get_next_user_agent(self) -> str:
        """Ротация User-Agent"""
        ua = self.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return ua
    
    async def cleanup(self):
        """
        Graceful cleanup (вызывается из main.py)
        
        ВАЖНО: Этот метод нужен для main.py
        """
        print("\n⏹️ [NEWS] Cleanup processor...")
        self.shutdown_requested = True
        
        self._print_stats()
    
    def _print_stats(self):
        """Вывод статистики"""
        
        print("\n" + "="*80)
        print("📊 NEWS PROCESSOR STATISTICS v3.2")
        print("="*80)
        print(f"Uptime: {self.metrics.get_uptime()/3600:.1f}h")
        print(f"Cycles: {self.metrics.cycles_completed}")
        print(f"Articles Fetched: {self.metrics.articles_fetched}")
        print(f"Articles Processed: {self.metrics.articles_processed}")
        print(f"Articles Published: {self.metrics.articles_published}")
        print(f"Articles Filtered: {self.metrics.articles_filtered}")
        print(f"Success Rate: {self.metrics.get_success_rate():.1f}%")
        print(f"Errors: {self.metrics.errors}")
        
        if self.metrics.fetch_errors_by_source:
            print("\nTop Error Sources:")
            sorted_errors = sorted(
                self.metrics.fetch_errors_by_source.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for source, count in sorted_errors[:5]:
                print(f"  • {source}: {count}")
        
        print("="*80 + "\n")