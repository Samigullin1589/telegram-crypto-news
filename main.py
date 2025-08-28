import os
import telegram
import asyncio
import feedparser
import time
import requests
from bs4 import BeautifulSoup
import re

# --- AI Провайдеры ---
import google.generativeai as genai
from openai import OpenAI

print("✅ [INIT] Запуск улучшенной версии бота v7.1 (Full Queue Processing)...")

# --- 1. Конфигурация ---
try:
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
except KeyError as e:
    print(f"❌ [CRITICAL] Не найдена переменная окружения {e}. Завершение работы.")
    exit()

# Настройка клиентов для обоих AI
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
openai_client = OpenAI(api_key=OPENAI_API_KEY)

RSS_FEEDS = {
    # 1. Финансы и регулирование в РФ от ведущего делового издания
    'Майнинг РФ и Мир 🇷🇺': 'http://static.feed.rbc.ru/rbc/logical/footer/news.rss?categories=crypto',
    
    # 2. Глубокие новости непосредственно о майнинге со всего мира
    'Новости Майнинга ⚙️': 'https://cointelegraph.com/rss/tag/mining',
    
    # 3. Ключевые события в крипто-индустрии СНГ
    'Крипто-новости СНГ 💡': 'https://forklog.com/feed',
    
    # 4. Общий фон мировой бизнес-повестки
    'Мировая Экономика 🌍': 'https://www.reuters.com/news/archive/businessNews.rss',
    
    # 5. НОВЫЙ ИСТОЧНИК: Технологии, оборудование и IT-инфраструктура
    'Технологии и Оборудование 💻': 'https://www.cnews.ru/inc/rss/telecom.xml'
}

# --- КОНСТАНТЫ ДЛЯ УПРАВЛЕНИЯ ПАУЗАМИ ---
# Пауза между публикациями, чтобы не спамить (в секундах)
POST_DELAY_SECONDS = 900 # 15 минут

# Пауза, когда нет новых статей (в секундах)
IDLE_DELAY_SECONDS = 300 # 5 минут

DATA_DIR = os.environ.get('RENDER_DISK_MOUNT_PATH', '.')
POSTED_URLS_FILE = os.path.join(DATA_DIR, 'posted_urls.txt')
print(f"💾 [INFO] Файл памяти будет храниться по пути: {POSTED_URLS_FILE}")


# --- 2. Функции-помощники ---

def load_posted_urls():
    try:
        with open(POSTED_URLS_FILE, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        print("ℹ️ [INFO] Файл с опубликованными URL не найден. Создаю новый.")
        return set()

def save_posted_url(url):
    with open(POSTED_URLS_FILE, 'a') as f:
        f.write(url + '\n')

def get_article_content(url, entry):
    image_url = None
    if 'media_content' in entry and entry.media_content:
        image_url = entry.media_content[0].get('url')
    elif 'enclosures' in entry and entry.enclosures:
        for enc in entry.enclosures:
            if 'image' in enc.type:
                image_url = enc.href
                break

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        if not image_url:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']

        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        text = None
        if article_body:
            for element in (article_body.find_all("script") + article_body.find_all("style")):
                element.decompose()
            text = ' '.join(article_body.get_text().split())
            # Оставляем больше текста для качественного анализа
            text = text[:12000] if len(text) > 200 else entry.summary
        else:
            text = entry.summary
            
        return {'text': text, 'image_url': image_url}
        
    except requests.RequestException as e:
        print(f"🕸️ [WARN] Не удалось получить полный текст/картинку для {url}: {e}")
        # Возвращаем краткое описание из RSS, если парсинг не удался
        return {'text': entry.summary, 'image_url': image_url}

def sanitize_markdown(text):
    # Эта функция пытается исправить незакрытые теги Markdown, которые ломают парсинг в Telegram
    # Проверяем каждый символ отдельно
    for char in ['*', '_', '`']:
        # Проверка тройных символов (```, ***, ___)
        if text.count(char * 3) % 2 != 0:
            text = text.rsplit(char * 3, 1)[0]
        # Проверка двойных символов (**, __)
        if text.count(char * 2) % 2 != 0:
            text = text.rsplit(char * 2, 1)[0]
        # Проверка одинарных символов (*, _)
        if text.count(char) % 2 != 0:
            text = text.rsplit(char, 1)[0]
    return text


# --- 3. Функции для работы с AI ---

async def get_ai_summary(title, text, category):
    category_emoji = category.split()[-1]
    prompt = f"""
    Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.
    Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

    {category_emoji} **{title}**

    *Здесь напиши главную суть новости в 2-3 предложениях. Используй профессиональный, но понятный язык. Объясни, почему это важно.*

    **Детали:**
    - Ключевой факт или цифра из статьи.
    - Контекст или причина произошедшего.
    - Возможные последствия для рынка или индустрии.

    *(Сгенерируй 3 релевантных хэштега на русском, например: #майнинг #россия #закон)*
    """
    try:
        print(f"🤖 [AI] Отправляю в Gemini: {title}")
        response = await gemini_model.generate_content_async(f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text}")
        return sanitize_markdown(response.text)
    except Exception as e:
        print(f"⚠️ [WARN] Ошибка Gemini: {e}. Переключаюсь на GPT...")
        try:
            print(f"🤖 [AI] Отправляю в GPT (резерв): {title}")
            user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_prompt}]))
            summary = response.choices[0].message.content
            return sanitize_markdown(summary)
        except Exception as e_gpt:
            print(f"❌ [ERROR] Ошибка GPT: {e_gpt}. Оба AI провайдера недоступны.")
            return None

# --- 4. Основная логика ---

async def send_message_to_channel(bot, message, link, image_url):
    full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
    try:
        if image_url:
            await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=image_url, caption=full_message[:1024], parse_mode='Markdown')
        else:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
        print(f"✅ [POST] Новость '{link}' успешно опубликована.")
        return True
    except telegram.error.BadRequest as e:
        print(f"❌ [ERROR] Ошибка форматирования Markdown при отправке в Telegram: {e}")
        print("ℹ️ [INFO] Попытка отправить сообщение без форматирования...")
        try:
            plain_text_message = re.sub(r'[*_`\[\]()~>#+\-=|{}.!]', '', full_message) # Убираем все спецсимволы
            if image_url:
                await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=image_url, caption=plain_text_message[:1024])
            else:
                await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=plain_text_message, disable_web_page_preview=True)
            print("✅ [POST] Сообщение успешно отправлено в текстовом виде.")
            return True
        except Exception as e_plain:
            print(f"❌ [FATAL] Повторная отправка также не удалась: {e_plain}")
            return False
    except Exception as e:
        print(f"❌ [ERROR] Неизвестная ошибка при отправке в Telegram: {e}")
        return False

async def main_loop():
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    posted_urls = load_posted_urls()

    if not posted_urls:
        print("🔥 [FIRST RUN] Первый запуск. Устанавливаю базовую линию новостей, чтобы не спамить.")
        for category, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if entry.link not in posted_urls:
                        posted_urls.add(entry.link)
                        save_posted_url(entry.link)
            except Exception as e:
                print(f"🕸️ [WARN] Не удалось обработать RSS-ленту {url} при первом запуске: {e}")
        print(f"✅ [BASELINE] Базовая линия установлена. Проигнорировано {len(posted_urls)} старых статей.")

    print(f"✅ [START] Бот в рабочем режиме. Загружено {len(posted_urls)} ранее опубликованных ссылок.")
    
    while True:
        print(f"\n--- [CYCLE] Новая итерация проверки: {time.ctime()} ---")
        all_new_entries = []
        for category, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                if feed.bozo:
                    # `bozo` - признак того, что RSS-лента может быть некорректной
                    print(f"🕸️ [WARN] RSS-лента для '{category}' может быть некорректной или временно недоступна.")
                
                new_count = 0
                for entry in feed.entries:
                    if entry.link not in posted_urls:
                        all_new_entries.append((entry, category))
                        new_count += 1
                print(f"📰 [FETCH] Проверено: {category}. Найдено новых статей: {new_count}")
            except Exception as e:
                print(f"🕸️ [CRITICAL] Не удалось проверить RSS-ленту {url}: {e}")

        if all_new_entries:
            # Сортируем все найденные новости от старых к новым, чтобы публиковать в хронологическом порядке
            sorted_entries = sorted(all_new_entries, key=lambda x: x[0].get('published_parsed', time.gmtime()))
            
            print(f"🔥 [QUEUE] Найдено {len(sorted_entries)} новых статей. Начинаю публикацию по очереди.")
            
            # --- ГЛАВНОЕ ИЗМЕНЕНИЕ: ОБРАБАТЫВАЕМ КАЖДУЮ НОВОСТЬ В ОЧЕРЕДИ ---
            for entry, category in sorted_entries:
                # Проверяем еще раз, вдруг за время обработки предыдущих новостей эта ссылка уже была добавлена
                if entry.link in posted_urls:
                    continue

                print(f"\n🔍 [PROCESS] Обрабатываю: {entry.title} ({category})")
                
                content = get_article_content(entry.link, entry)
                
                formatted_post = await get_ai_summary(entry.title, content['text'], category)

                if formatted_post:
                    success = await send_message_to_channel(bot, formatted_post, entry.link, content['image_url'])
                    if success:
                        # Отмечаем новость как опубликованную ТОЛЬКО после успешной отправки
                        posted_urls.add(entry.link)
                        save_posted_url(entry.link)
                        
                        # Пауза МЕЖДУ публикациями, чтобы не затопить канал сообщениями
                        print(f"🕒 [PAUSE] Публикация успешна. Следующая через {POST_DELAY_SECONDS / 60:.0f} минут.")
                        await asyncio.sleep(POST_DELAY_SECONDS)
                else:
                    print("❌ [SKIP] Не удалось сгенерировать саммари. Пропускаю новость.")
                    await asyncio.sleep(5) # Короткая пауза на всякий случай

            print("✅ [QUEUE] Все новости из текущей пачки обработаны.")
        else:
            print("👍 [INFO] Новых статей не найдено.")

        # Если новостей не было, проверяем чаще. Если были - цикл начнется сразу после последней публикации.
        print(f"--- [PAUSE] Следующая проверка через {IDLE_DELAY_SECONDS / 60:.0f} минут. ---")
        await asyncio.sleep(IDLE_DELAY_SECONDS)

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Бот остановлен вручную.")