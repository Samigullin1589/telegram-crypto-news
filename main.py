# main.py v9.1
import os
import telegram
import asyncio
import feedparser
import time
from bs4 import BeautifulSoup
import re
import sqlite3
import aiohttp
from urllib.parse import urljoin
import io
from PIL import Image

# --- AI Провайдеры ---
import google.generativeai as genai
from openai import OpenAI

# ==============================================================================
# --- ВЕРСИЯ 9.1 - GOLD STANDARD (FINAL OPTIMIZATIONS) ---
#
# ФИНАЛЬНЫЕ ИЗМЕНЕНИЯ:
# 1. ОПТИМИЗАЦИЯ ПЕРВОГО ЗАПУСКА: Устранена двойная загрузка RSS-лент
#    при создании "базовой линии". Бот теперь работает быстрее при старте.
# 2. ОПТИМИЗАЦИЯ СЕТИ: Улучшена проверка изображений — теперь используется
#    единое сетевое подключение, что ускоряет обработку страниц.
# 3. ПОВЫШЕНИЕ НАДЁЖНОСТИ: Добавлены дополнительные проверки на наличие
#    атрибутов у RSS-записей для максимальной стабильности.
# ==============================================================================

print("✅ [INIT] Запуск улучшенной версии бота v9.1 (Gold Standard)...")

# --- 1. Конфигурация ---
try:
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
except KeyError as e:
    print(f"❌ [CRITICAL] Не найдена переменная окружения {e}. Завершение работы.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)

RSS_FEEDS = {
    'Крипто и Блокчейн РФ/СНГ 🇷🇺': 'https://habr.com/ru/rss/hubs/cryptocurrency/',
    'Новости Майнинга (Мир) ⚙️': 'https://cointelegraph.com/rss/tag/mining',
    'Крипто-новости СНГ 💡': 'https://forklog.com/feed',
    'Мировые Крипто-новости 🌍': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'Майнинг и Железо (СНГ) 💻': 'https://forklog.com/hub/mining/feed'
}

# --- КОНСТАНТЫ ---
POST_DELAY_SECONDS = 900
IDLE_DELAY_SECONDS = 300
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')
MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 200

# --- 2. Управляющий класс для Базы Данных ---
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.setup()

    def setup(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posted_articles (
                    link TEXT PRIMARY KEY,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        print(f"💾 [DB] База данных готова по пути: {self.db_path}")

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_link(self, link):
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO posted_articles (link) VALUES (?)", (link,))
            conn.commit()

    def save_links_bulk(self, links):
        with self._get_connection() as conn:
            conn.executemany("INSERT OR IGNORE INTO posted_articles (link) VALUES (?)", [(link,) for link in links])
            conn.commit()

    def get_all_links(self):
        with self._get_connection() as conn:
            return {row[0] for row in conn.execute("SELECT link FROM posted_articles")}

# --- 3. Класс для работы с AI ---
class AIHandler:
    def __init__(self, gemini_key, openai_key):
        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
        self.openai_client = OpenAI(api_key=openai_key)
        self.prompt_template = """
        Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.
        Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

        {emoji} **{title}**

        *Здесь напиши главную суть новости в 2-3 предложениях. Используй профессиональный, но понятный язык. Объясни, почему это важно.*

        **Детали:**
        - Ключевой факт или цифра из статьи.
        - Контекст или причина произошедшего.
        - Возможные последствия для рынка или индустрии.

        *(Сгенерируй 3 релевантных хэштега на русском, например: #майнинг #россия #закон)*
        """

    async def get_summary(self, title, text, category):
        max_retries = 3
        backoff_factor = 10
        category_emoji = category.split()[-1]
        
        if not text:
            print("⚠️ [AI] Текст для анализа пуст. Пропускаю саммари.")
            return None
        
        prompt = self.prompt_template.format(emoji=category_emoji, title=title)

        for attempt in range(max_retries):
            try:
                print(f"🤖 [AI] Попытка {attempt + 1}/{max_retries}. Отправляю в Gemini: {title}")
                response = await self.gemini_model.generate_content_async(f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text}")
                return self._sanitize_markdown(response.text)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print(f"🚨 [AI] Квота Gemini исчерпана. Немедленное переключение на GPT.")
                    break
                
                print(f"⚠️ [WARN] Ошибка Gemini: {e}. Попытка {attempt + 1} не удалась.")
                if attempt + 1 < max_retries:
                    delay = backoff_factor * (2 ** attempt)
                    print(f"⏳ [AI] Пауза на {delay} секунд перед следующей попыткой.")
                    await asyncio.sleep(delay)
        
        print("🤖 [AI] Переключаюсь на GPT (резерв).")
        try:
            user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_prompt}]))
            summary = response.choices[0].message.content
            return self._sanitize_markdown(summary)
        except Exception as e_gpt:
            print(f"❌ [ERROR] Ошибка GPT: {e_gpt}. Оба AI провайдера недоступны.")
            return None

    def _sanitize_markdown(self, text):
        for char in ['*', '_', '`']:
            if text.count(char * 3) % 2 != 0: text = text.rsplit(char * 3, 1)[0]
            if text.count(char * 2) % 2 != 0: text = text.rsplit(char * 2, 1)[0]
            if text.count(char) % 2 != 0: text = text.rsplit(char, 1)[0]
        return text

# --- 4. Класс для отправки сообщений в Telegram ---
class TelegramPoster:
    def __init__(self, token, channel_id):
        self.bot = telegram.Bot(token=token)
        self.channel_id = channel_id

    async def post(self, message, link, image_url):
        full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
        try:
            if image_url:
                await self.bot.send_photo(chat_id=self.channel_id, photo=image_url, caption=full_message[:1024], parse_mode='Markdown')
            else:
                await self.bot.send_message(chat_id=self.channel_id, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
            print(f"✅ [POST] Новость '{link}' успешно опубликована.")
            return True
        except telegram.error.BadRequest as e:
            print(f"❌ [ERROR] Ошибка форматирования Markdown: {e}. Пробую отправить без него.")
            plain_text_message = re.sub(r'[*_`\[\]()~>#+\-=|{}.!]', '', full_message)
            try:
                if image_url:
                    await self.bot.send_photo(chat_id=self.channel_id, photo=image_url, caption=plain_text_message[:1024])
                else:
                    await self.bot.send_message(chat_id=self.channel_id, text=plain_text_message, disable_web_page_preview=True)
                print("✅ [POST] Сообщение успешно отправлено в текстовом виде.")
                return True
            except Exception as e_plain:
                print(f"❌ [FATAL] Повторная отправка также не удалась: {e_plain}")
                return False
        except Exception as e:
            print(f"❌ [ERROR] Неизвестная ошибка при отправке в Telegram: {e}")
            return False

# --- 5. Главный orchestrator ---
class NewsProcessor:
    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.ai = AIHandler(GEMINI_API_KEY, OPENAI_API_KEY)
        self.poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
        self.posted_urls_cache = set()

    def _is_likely_logo(self, image_url):
        if not image_url: return True
        return any(keyword in image_url.lower() for keyword in ['logo', 'brand', 'icon', 'sprite', 'avatar'])

    async def _get_valid_image_url(self, image_candidates, session):
        for url in image_candidates:
            if not url or self._is_likely_logo(url):
                continue
            
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200: continue
                    image_data = await response.content.read(4096)
                    if not image_data: continue

                    img = Image.open(io.BytesIO(image_data))
                    if img.width >= MIN_IMAGE_WIDTH and img.height >= MIN_IMAGE_HEIGHT:
                        print(f"🖼️ [IMG] Найдено подходящее изображение: {url} ({img.width}x{img.height})")
                        return url
                    else:
                        print(f"🖼️ [IMG] Изображение отклонено (слишком маленькое): {url} ({img.width}x{img.height})")
            except Exception as e:
                print(f"🖼️ [IMG] Не удалось проверить изображение {url}: {e}")
                continue
        return None

    async def _get_article_content(self, url, entry, session):
        article_text = entry.get('summary', '')
        final_url = url
        image_candidates = []
        main_image_url = None
        try:
            async with session.get(url, timeout=15) as response:
                response.raise_for_status()
                final_url = str(response.url)
                html_text = await response.text()
            
            soup = BeautifulSoup(html_text, 'lxml')
            article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
            if article_body:
                for element in (article_body.find_all("script") + article_body.find_all("style")):
                    element.decompose()
                
                parsed_text = ' '.join(article_body.get_text().split())
                if parsed_text:
                    article_text = parsed_text[:12000]

                for img_tag in article_body.find_all('img', src=True):
                    if src := img_tag.get('src'):
                        image_candidates.append(urljoin(final_url, src))
            
            if 'media_content' in entry and entry.media_content:
                if media_url := entry.media_content[0].get('url'):
                    image_candidates.append(urljoin(final_url, media_url))
            elif 'enclosures' in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if 'image' in enc.type and enc.href:
                        image_candidates.append(urljoin(final_url, enc.href))
            
            if og_image := soup.find('meta', property='og:image'):
                if content := og_image.get('content'):
                    image_candidates.append(urljoin(final_url, content))
            
            main_image_url = await self._get_valid_image_url(image_candidates, session)
            
            return {'text': article_text, 'image_url': main_image_url, 'final_url': final_url}
        except Exception as e:
            print(f"🕸️ [WARN] Не удалось получить полный текст/картинку для {url}: {e}")
            return {'text': article_text, 'image_url': None, 'final_url': url}

    async def _fetch_feed_entries(self, session):
        tasks = [self._fetch_and_parse_feed(cat, url, session) for cat, url in RSS_FEEDS.items()]
        results = await asyncio.gather(*tasks)
        return [entry for feed_result in results for entry in feed_result]

    async def _fetch_and_parse_feed(self, category, url, session):
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
            
            new_entries = [(entry, category) for entry in feed.entries if entry.get('link') and entry.get('link') not in self.posted_urls_cache]
            print(f"📰 [FETCH] Проверено: {category}. Найдено новых статей: {len(new_entries)}")
            return new_entries
        except Exception as e:
            print(f"❌ [CRITICAL] Не удалось обработать RSS-ленту {category}: {e}")
            return []

    async def run(self):
        self.posted_urls_cache = self.db.get_all_links()
        all_new_entries = []
        
        if not self.posted_urls_cache:
            print("🔥 [FIRST RUN] База данных пуста. Заполняю ее текущими статьями...")
            async with aiohttp.ClientSession() as session:
                all_new_entries = await self._fetch_feed_entries(session)
            
            baseline_links = {entry[0].get('link') for entry in all_new_entries if entry[0].get('link')}
            if baseline_links:
                self.db.save_links_bulk(baseline_links)
                self.posted_urls_cache.update(baseline_links)
                print(f"✅ [BASELINE] Базовая линия установлена. В базу добавлено {len(baseline_links)} статей.")
        
        print(f"✅ [START] Бот в рабочем режиме. Загружено {len(self.posted_urls_cache)} ссылок.")

        while True:
            if not all_new_entries:
                print(f"\n--- [CYCLE] Новая итерация проверки: {time.ctime()} ---")
                async with aiohttp.ClientSession() as session:
                    all_new_entries = await self._fetch_feed_entries(session)

            if all_new_entries:
                sorted_entries = sorted(all_new_entries, key=lambda x: x[0].get('published_parsed', time.gmtime()))
                print(f"🔥 [QUEUE] Найдено {len(sorted_entries)} новых статей. Начинаю публикацию по очереди.")
                
                async with aiohttp.ClientSession() as session:
                    for entry, category in sorted_entries:
                        link = entry.get('link')
                        title = entry.get('title', 'Без заголовка')

                        if not link or link in self.posted_urls_cache:
                            continue

                        print(f"\n🔍 [PROCESS] Обрабатываю: {title} ({category})")
                        content = await self._get_article_content(link, entry, session)
                        
                        final_link = content.get('final_url', link)
                        formatted_post = await self.ai.get_summary(title, content['text'], category)

                        if formatted_post:
                            success = await self.poster.post(formatted_post, final_link, content['image_url'])
                            if success:
                                self.db.save_link(link)
                                self.posted_urls_cache.add(link)
                                print(f"🕒 [PAUSE] Публикация успешна. Следующая через {POST_DELAY_SECONDS / 60:.0f} минут.")
                                await asyncio.sleep(POST_DELAY_SECONDS)
                        else:
                            print("❌ [SKIP] Не удалось сгенерировать саммари. Пропускаю новость.")
                            await asyncio.sleep(5)
            else:
                print("👍 [INFO] Новых статей не найдено.")

            all_new_entries = []
            print(f"--- [PAUSE] Следующая проверка через {IDLE_DELAY_SECONDS / 60:.0f} минут. ---")
            await asyncio.sleep(IDLE_DELAY_SECONDS)

# --- 6. Точка входа ---
if __name__ == '__main__':
    processor = NewsProcessor()
    try:
        asyncio.run(processor.run())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Бот остановлен вручную.")