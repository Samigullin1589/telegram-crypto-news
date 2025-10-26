# bot/processor.py
import asyncio
import aiohttp
import feedparser
import time
from urllib.parse import urlparse, urlunparse
from typing import List, Tuple, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict
from .config import config
from .database import DatabaseManager
from .ai_handler import AIHandler
from .telegram_poster import TelegramPoster
from .content_parser import ContentParser, URLNormalizer


class ProcessingMetrics:
    """Метрики обработки новостей"""
    
    def __init__(self):
        self.cycles_completed = 0
        self.articles_processed = 0
        self.articles_published = 0
        self.articles_skipped = 0
        self.feed_errors = defaultdict(int)
        self.processing_times = []
        self.start_time = time.time()
    
    def record_cycle(self, articles_found: int, articles_published: int):
        """Запись завершённого цикла"""
        self.cycles_completed += 1
        self.articles_processed += articles_found
        self.articles_published += articles_published
    
    def record_skip(self):
        """Запись пропущенной статьи"""
        self.articles_skipped += 1
    
    def record_feed_error(self, feed_name: str):
        """Запись ошибки фида"""
        self.feed_errors[feed_name] += 1
    
    def record_processing_time(self, elapsed: float):
        """Запись времени обработки"""
        self.processing_times.append(elapsed)
        # Храним только последние 50 замеров
        if len(self.processing_times) > 50:
            self.processing_times.pop(0)
    
    @property
    def uptime_hours(self) -> float:
        """Время работы в часах"""
        return (time.time() - self.start_time) / 3600
    
    @property
    def avg_processing_time(self) -> float:
        """Среднее время обработки"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def print_summary(self):
        """Вывод статистики"""
        print("\n" + "="*80)
        print("📊 СТАТИСТИКА РАБОТЫ БОТА")
        print("="*80)
        print(f"⏱️  Uptime: {self.uptime_hours:.1f}h")
        print(f"🔄 Циклов: {self.cycles_completed}")
        print(f"📰 Обработано статей: {self.articles_processed}")
        print(f"✅ Опубликовано: {self.articles_published}")
        print(f"⏭️  Пропущено: {self.articles_skipped}")
        print(f"⚡ Среднее время обработки: {self.avg_processing_time:.2f}s")
        
        if self.feed_errors:
            print("\n❌ Ошибки фидов:")
            for feed, count in sorted(self.feed_errors.items(), key=lambda x: x[1], reverse=True):
                print(f"   {feed}: {count}")
        
        print("="*80 + "\n")


class FeedFetcher:
    """Умный загрузчик RSS фидов с приоритизацией"""
    
    def __init__(self, metrics: ProcessingMetrics):
        self.metrics = metrics
        self.url_normalizer = URLNormalizer()
    
    async def fetch_all_feeds(
        self,
        session: aiohttp.ClientSession,
        posted_cache: Set[str]
    ) -> List[Tuple[dict, str]]:
        """
        Параллельная загрузка всех фидов с приоритизацией
        
        Returns:
            List[(entry, category)] отсортированный по приоритету
        """
        # Получаем фиды отсортированные по приоритету
        sorted_feeds = config.get_sorted_feeds()
        
        # Параллельно загружаем все фиды
        tasks = [
            self._fetch_single_feed(name, feed_config, session, posted_cache)
            for name, feed_config in sorted_feeds
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты с приоритетами
        prioritized_entries = []
        
        for idx, result in enumerate(results):
            feed_name, feed_config = sorted_feeds[idx]
            
            if isinstance(result, Exception):
                print(f"❌ [FEED] Критическая ошибка {feed_name}: {result}")
                self.metrics.record_feed_error(feed_name)
                continue
            
            entries = result
            
            # Добавляем приоритет к каждой статье
            for entry in entries:
                prioritized_entries.append((entry, feed_name, feed_config.priority))
        
        # Сортируем по приоритету (высший первым), затем по дате
        prioritized_entries.sort(
            key=lambda x: (
                -x[2],  # Приоритет (инверсия для сортировки по убыванию)
                x[0].get('published_parsed', time.gmtime())
            ),
            reverse=False
        )
        
        # Возвращаем без приоритета
        return [(entry, category) for entry, category, _ in prioritized_entries]
    
    async def _fetch_single_feed(
        self,
        category: str,
        feed_config,
        session: aiohttp.ClientSession,
        posted_cache: Set[str]
    ) -> List[Tuple[dict, str]]:
        """Загрузка одного RSS фида"""
        try:
            print(f"📡 [FETCH] {category} (приоритет: {feed_config.priority})")
            
            async with session.get(
                feed_config.url,
                timeout=aiohttp.ClientTimeout(total=feed_config.timeout)
            ) as response:
                
                if response.status != 200:
                    print(f"⚠️  [FETCH] {category} вернул HTTP {response.status}")
                    self.metrics.record_feed_error(category)
                    return []
                
                feed_bytes = await response.read()
            
            # Парсинг в отдельном потоке (блокирующая операция)
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_bytes)
            
            if feed.bozo:
                print(f"⚠️  [FETCH] {category} некорректный RSS: {feed.bozo_exception}")
            
            # Фильтруем новые статьи
            new_entries = []
            for entry in feed.entries:
                link = entry.get('link')
                if not link:
                    continue
                
                normalized_link = self.url_normalizer.normalize(link)
                if normalized_link not in posted_cache:
                    new_entries.append((entry, category))
            
            print(f"✅ [FETCH] {category}: {len(new_entries)} новых из {len(feed.entries)}")
            return new_entries
            
        except asyncio.TimeoutError:
            print(f"⏱️  [FETCH] Timeout: {category}")
            self.metrics.record_feed_error(category)
            return []
        except Exception as e:
            print(f"❌ [FETCH] Ошибка {category}: {type(e).__name__} - {str(e)[:100]}")
            self.metrics.record_feed_error(category)
            return []


class ArticleProcessor:
    """Обработчик отдельных статей"""
    
    def __init__(
        self,
        parser: ContentParser,
        ai: AIHandler,
        poster: TelegramPoster,
        db: DatabaseManager
    ):
        self.parser = parser
        self.ai = ai
        self.poster = poster
        self.db = db
        self.url_normalizer = URLNormalizer()
    
    async def process_article(
        self,
        entry: dict,
        category: str,
        session: aiohttp.ClientSession
    ) -> bool:
        """
        Полная обработка одной статьи
        
        Returns:
            True если успешно опубликовано
        """
        start_time = time.time()
        
        original_link = entry.get('link')
        title = entry.get('title', 'Без заголовка')
        
        if not original_link:
            return False
        
        normalized_link = self.url_normalizer.normalize(original_link)
        
        print(f"\n{'='*80}")
        print(f"🔍 [PROCESS] {title[:70]}")
        print(f"📂 Источник: {category}")
        print(f"🔗 URL: {original_link[:70]}...")
        
        # 1. Парсинг контента
        try:
            content = await self.parser.get_article_content(
                original_link,
                entry,
                session
            )
        except Exception as e:
            print(f"❌ [PROCESS] Ошибка парсинга: {e}")
            return False
        
        final_link = content.get('final_url', original_link)
        article_text = content.get('text', '')
        image_url = content.get('image_url')
        
        print(f"📝 Текст: {len(article_text)} символов")
        print(f"🖼️  Изображение: {'✅' if image_url else '❌'}")
        
        # 2. Генерация саммари
        try:
            result = await self.ai.get_summary(title, article_text, category)
            
            if not result:
                print(f"❌ [PROCESS] AI не смог создать саммари")
                return False
            
            summary, ai_provider = result
            print(f"🤖 AI: {ai_provider.upper()}")
            
        except Exception as e:
            print(f"❌ [PROCESS] Ошибка AI: {e}")
            return False
        
        # 3. Публикация
        try:
            success = await self.poster.post(summary, final_link, image_url)
            
            if success:
                # Сохраняем в БД
                self.db.save_article(
                    link=original_link,
                    normalized_link=normalized_link,
                    source_feed=category,
                    title=title,
                    has_image=bool(image_url),
                    ai_provider=ai_provider,
                    status='success'
                )
                
                elapsed = time.time() - start_time
                print(f"✅ [PROCESS] УСПЕХ за {elapsed:.1f}s")
                print(f"{'='*80}\n")
                return True
            else:
                print(f"❌ [PROCESS] Не удалось опубликовать")
                return False
                
        except Exception as e:
            print(f"❌ [PROCESS] Ошибка публикации: {e}")
            return False


class NewsProcessor:
    """
    Главный процессор новостей с умным управлением потоком
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ai = AIHandler()
        self.poster = TelegramPoster()
        self.parser = ContentParser()
        
        self.metrics = ProcessingMetrics()
        self.fetcher = FeedFetcher(self.metrics)
        self.article_processor = ArticleProcessor(
            self.parser,
            self.ai,
            self.poster,
            self.db
        )
        
        self.posted_cache: Set[str] = set()
        self.shutdown_flag = False
        
        print("🚀 [PROCESSOR] Инициализирован")
    
    async def run(self):
        """Главный цикл работы бота"""
        
        # Загружаем кэш из БД
        self.posted_cache = self.db.get_all_links()
        is_first_run = not self.posted_cache
        
        print(f"\n{'='*80}")
        print(f"🤖 НОВОСТНОЙ БОТ ЗАПУЩЕН")
        print(f"{'='*80}")
        print(f"📊 В базе: {len(self.posted_cache)} статей")
        print(f"📡 Активных фидов: {len([f for f in config.RSS_FEEDS.values() if f.enabled])}")
        print(f"⏱️  Задержка между постами: {config.POST_DELAY_SECONDS // 60} мин")
        print(f"🔄 Проверка фидов: каждые {config.IDLE_DELAY_SECONDS // 60} мин")
        print(f"{'='*80}\n")
        
        # Первый запуск - создаём baseline
        if is_first_run:
            await self._initialize_baseline()
        
        # Главный цикл
        cycle_number = 0
        
        while not self.shutdown_flag:
            cycle_number += 1
            cycle_start = time.time()
            
            print(f"\n{'#'*80}")
            print(f"🔄 ЦИКЛ #{cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'#'*80}\n")
            
            try:
                # Создаём сессию для этого цикла
                timeout = aiohttp.ClientTimeout(
                    total=config.SESSION_TIMEOUT_TOTAL,
                    connect=config.SESSION_TIMEOUT_CONNECT
                )
                
                async with aiohttp.ClientSession(
                    headers=config.COMMON_HEADERS,
                    timeout=timeout
                ) as session:
                    
                    # Загружаем все фиды
                    all_entries = await self.fetcher.fetch_all_feeds(
                        session,
                        self.posted_cache
                    )
                    
                    if not all_entries:
                        print("✅ [CYCLE] Новых статей не найдено")
                        cycle_elapsed = time.time() - cycle_start
                        self.metrics.record_cycle(0, 0)
                        self.metrics.record_processing_time(cycle_elapsed)
                    else:
                        print(f"\n🔥 [CYCLE] Найдено {len(all_entries)} новых статей")
                        print(f"📋 Начинаю последовательную публикацию...\n")
                        
                        published_count = 0
                        
                        # Обрабатываем статьи последовательно
                        for idx, (entry, category) in enumerate(all_entries, 1):
                            if self.shutdown_flag:
                                print("\n⏹️  [SHUTDOWN] Прерывание цикла...")
                                break
                            
                            print(f"[{idx}/{len(all_entries)}] ", end='')
                            
                            success = await self.article_processor.process_article(
                                entry,
                                category,
                                session
                            )
                            
                            if success:
                                published_count += 1
                                
                                # Добавляем в кэш
                                normalized_link = URLNormalizer.normalize(entry['link'])
                                self.posted_cache.add(normalized_link)
                                
                                # Задержка между постами
                                if idx < len(all_entries):  # Не ждём после последнего
                                    print(f"⏳ Пауза {config.POST_DELAY_SECONDS // 60} мин до следующего поста...\n")
                                    await asyncio.sleep(config.POST_DELAY_SECONDS)
                            else:
                                self.metrics.record_skip()
                                print(f"⏭️  Пропускаю и перехожу к следующей...\n")
                                await asyncio.sleep(3)  # Короткая пауза
                        
                        cycle_elapsed = time.time() - cycle_start
                        self.metrics.record_cycle(len(all_entries), published_count)
                        self.metrics.record_processing_time(cycle_elapsed)
                        
                        print(f"\n✅ [CYCLE] Завершён за {cycle_elapsed / 60:.1f} мин")
                        print(f"📊 Опубликовано: {published_count}/{len(all_entries)}")
                
                # Периодический вывод статистики (каждые 10 циклов)
                if cycle_number % 10 == 0:
                    self._print_full_stats()
                
            except Exception as e:
                print(f"\n❌ [CRITICAL] Ошибка в цикле: {e}")
                import traceback
                traceback.print_exc()
            
            # Пауза до следующего цикла
            if not self.shutdown_flag:
                print(f"\n💤 Следующая проверка через {config.IDLE_DELAY_SECONDS // 60} мин...")
                await asyncio.sleep(config.IDLE_DELAY_SECONDS)
        
        print("\n🛑 [PROCESSOR] Остановлен")
    
    async def _initialize_baseline(self):
        """Создание baseline при первом запуске"""
        print("\n" + "="*80)
        print("🔥 ПЕРВЫЙ ЗАПУСК - Создание baseline")
        print("="*80)
        print("Загружаю текущие статьи для заполнения базы данных...")
        print("(Эти статьи НЕ будут опубликованы)\n")
        
        async with aiohttp.ClientSession(headers=config.COMMON_HEADERS) as session:
            baseline_entries = await self.fetcher.fetch_all_feeds(
                session,
                set()  # Пустой кэш
            )
            
            if baseline_entries:
                # Сохраняем только ссылки
                baseline_data = []
                for entry, category in baseline_entries:
                    link = entry.get('link')
                    if link:
                        normalized = URLNormalizer.normalize(link)
                        baseline_data.append((link, normalized, category))
                
                if baseline_data:
                    self.db.save_links_bulk(baseline_data)
                    self.posted_cache = {item[1] for item in baseline_data}
                    
                    print(f"✅ Baseline создан: {len(baseline_data)} статей в базе")
                    print("="*80 + "\n")
    
    def _print_full_stats(self):
        """Вывод полной статистики"""
        self.metrics.print_summary()
        
        # Статистика AI
        print("🤖 AI Handler:")
        ai_stats = self.ai.get_stats_summary()
        print(f"   Gemini: {ai_stats['gemini']['success_rate']} успеха, {ai_stats['gemini']['avg_time']} среднее")
        print(f"   OpenAI: {ai_stats['openai']['success_rate']} успеха, {ai_stats['openai']['avg_time']} среднее")
        print(f"   Preferred: {ai_stats['preferred_provider'].upper()}")
        print(f"   Cache: {ai_stats['cache_size']} записей\n")
        
        # Статистика Telegram
        print("📱 Telegram Poster:")
        tg_stats = self.poster.get_stats()
        print(f"   Успешно: {tg_stats['successful']}/{tg_stats['total_attempts']} ({tg_stats['success_rate']})")
        print(f"   С изображениями: {tg_stats['with_images']}")
        print(f"   Markdown ошибок: {tg_stats['markdown_errors']}")
        print(f"   Retry: {tg_stats['retries']}\n")
        
        # Статистика БД
        db_stats = self.db.get_stats_summary()
        print("💾 Database:")
        print(f"   Всего статей: {db_stats['total_articles']}")
        print(f"   Сегодня: {db_stats['articles_today']}")
        if db_stats['top_feed_7d']:
            print(f"   Топ фид (7д): {db_stats['top_feed_7d']}\n")
    
    async def shutdown(self):
        """Graceful shutdown"""
        print("\n⏹️  [SHUTDOWN] Инициирована остановка...")
        self.shutdown_flag = True
        
        # Финальная статистика
        self._print_full_stats()
        
        print("✅ [SHUTDOWN] Завершено")