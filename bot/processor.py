# bot/processor.py
import asyncio
import aiohttp
import feedparser
import time
from urllib.parse import urlparse, urlunparse
from . import config
from .database import DatabaseManager
from .ai_handler import AIHandler
from .telegram_poster import TelegramPoster
from .content_parser import ContentParser

class NewsProcessor:
    def __init__(self):
        self.db = DatabaseManager()
        self.ai = AIHandler()
        self.poster = TelegramPoster()
        self.parser = ContentParser()
        self.posted_urls_cache = set()
    
    def _normalize_url(self, url):
        """Очищает URL от всех query-параметров (UTM и т.д.)."""
        parts = urlparse(url)
        return urlunparse((parts.scheme, parts.netloc, parts.path, '', '', ''))
    
    async def _fetch_and_parse_feed(self, category, url, session):
        """Асинхронно загружает и парсит одну RSS-ленту."""
        try:
            print(f"📡 [FETCH] Запрашиваю: {category}")
            async with session.get(url, timeout=20) as response:
                if response.status != 200:
                    print(f"🕸️ [WARN] Источник '{category}' вернул статус {response.status}")
                    return []
                feed_bytes = await response.read()
            
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_bytes)
            
            if feed.bozo:
                print(f"🕸️ [WARN] RSS-лента для '{category}' может быть некорректной. Причина: {feed.bozo_exception}")
            
            new_entries = []
            for entry in feed.entries:
                original_link = entry.get('link')
                if not original_link: continue
                
                normalized_link = self._normalize_url(original_link)
                if normalized_link not in self.posted_urls_cache:
                    new_entries.append((entry, category))
            
            print(f"📰 [FETCH] Проверено: {category}. Найдено новых статей: {len(new_entries)}")
            return new_entries
        except Exception as e:
            print(f"❌ [CRITICAL] Не удалось обработать RSS-ленту {category}: {e}")
            return []

    async def _fetch_feed_entries(self, session):
        """Параллельно запускает загрузку всех RSS-лент."""
        tasks = [self._fetch_and_parse_feed(cat, url, session) for cat, url in config.RSS_FEEDS.items()]
        results = await asyncio.gather(*tasks)
        return [entry for feed_result in results for entry in feed_result]

    async def run(self):
        """Основной цикл работы бота с короткоживущими сессиями."""
        self.posted_urls_cache = self.db.get_all_links()
        
        # Флаг для однократного выполнения логики первого запуска
        is_first_run = not self.posted_urls_cache
        
        print(f"✅ [START] Бот в рабочем режиме. Загружено {len(self.posted_urls_cache)} ссылок.")

        while True:
            all_new_entries = []
            
            # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Сессия создаётся для каждого цикла ---
            async with aiohttp.ClientSession(headers=config.COMMON_HEADERS) as session:
                if is_first_run:
                    print("🔥 [FIRST RUN] База данных пуста. Заполняю ее текущими статьями...")
                    # Получаем статьи для baseline, но не публикуем их сразу
                    baseline_entries = await self._fetch_feed_entries(session)
                    baseline_links = {self._normalize_url(entry[0].get('link')) for entry in baseline_entries if entry[0].get('link')}
                    if baseline_links:
                        self.db.save_links_bulk(baseline_links)
                        self.posted_urls_cache.update(baseline_links)
                        print(f"✅ [BASELINE] Базовая линия установлена. В базу добавлено {len(baseline_links)} статей.")
                    is_first_run = False # Выключаем флаг
                
                # Основная проверка
                print(f"\n--- [CYCLE] Новая итерация проверки: {time.ctime()} ---")
                all_new_entries = await self._fetch_feed_entries(session)

                if all_new_entries:
                    sorted_entries = sorted(all_new_entries, key=lambda x: x[0].get('published_parsed', time.gmtime()))
                    print(f"🔥 [QUEUE] Найдено {len(sorted_entries)} новых статей. Начинаю публикацию по очереди.")
                    
                    for entry, category in sorted_entries:
                        original_link = entry.get('link')
                        title = entry.get('title', 'Без заголовка')
                        if not original_link: continue

                        normalized_link = self._normalize_url(original_link)
                        if normalized_link in self.posted_urls_cache: continue

                        print(f"\n🔍 [PROCESS] Обрабатываю: {title} ({category})")
                        content = await self.parser.get_article_content(original_link, entry, session)
                        
                        final_link = content.get('final_url', original_link)
                        formatted_post = await self.ai.get_summary(title, content['text'], category)

                        if formatted_post:
                            success = await self.poster.post(formatted_post, final_link, content['image_url'])
                            if success:
                                self.db.save_link(normalized_link)
                                self.posted_urls_cache.add(normalized_link)
                                print(f"🕒 [PAUSE] Публикация успешна. Следующая через {config.POST_DELAY_SECONDS / 60:.0f} минут.")
                                await asyncio.sleep(config.POST_DELAY_SECONDS)
                        else:
                            print("❌ [SKIP] Не удалось сгенерировать саммари. Пропускаю новость.")
                            await asyncio.sleep(5)
                else:
                    print("👍 [INFO] Новых статей не найдено.")

            # Сессия автоматически закрывается здесь после каждого цикла
            
            print(f"--- [PAUSE] Следующая проверка через {config.IDLE_DELAY_SECONDS / 60:.0f} минут. ---")
            await asyncio.sleep(config.IDLE_DELAY_SECONDS)