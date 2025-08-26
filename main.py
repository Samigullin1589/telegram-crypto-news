import os
import telegram
import asyncio
import feedparser
import time
import requests
from bs4 import BeautifulSoup

# --- AI Провайдеры ---
import google.generativeai as genai
from openai import OpenAI

print("✅ [INIT] Запуск финальной версии бота v3.0 (Image Edition)...")

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

# Список RSS-лент для мониторинга с эмодзи для категорий
RSS_FEEDS = {
    'Майнинг РФ и Мир 🇷🇺': 'https://bits.media/rss/',
    'Новости Майнинга ⚙️': 'https://cointelegraph.com/rss/tag/mining',
    'Крипто-новости СНГ 💡': 'https://forklog.com/feed',
    'Мировая Экономика 🌍': 'https://feeds.reuters.com/reuters/businessNews'
}

POSTED_URLS_FILE = 'posted_urls.txt'

# --- 2. Функции-помощники ---

def load_posted_urls():
    """Загружает опубликованные URL из файла в память при старте."""
    try:
        with open(POSTED_URLS_FILE, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        print("ℹ️ [INFO] Файл с опубликованными URL не найден. Создаю новый.")
        return set()

def save_posted_url(url):
    """Добавляет новый URL в файл, обеспечивая постоянство памяти."""
    with open(POSTED_URLS_FILE, 'a') as f:
        f.write(url + '\n')

def get_article_content(url, entry):
    """
    Извлекает полный текст И главное изображение статьи.
    Возвращает словарь: {'text': str, 'image_url': str}
    """
    image_url = None
    # --- НОВАЯ ЛОГИКА: Поиск изображения ---
    # 1. Сначала ищем в RSS-тегах (самый надежный способ)
    if 'media_content' in entry and entry.media_content:
        image_url = entry.media_content[0].get('url')
    elif 'enclosures' in entry and entry.enclosures:
        for enc in entry.enclosures:
            if 'image' in enc.type:
                image_url = enc.href
                break

    # 2. Если в RSS нет, парсим HTML-страницу
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 2a. Ищем мета-тег 'og:image' - стандарт для превью
        if not image_url:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
                print(f"🖼️ [IMG] Изображение найдено через og:image: {image_url}")

        # 2b. Извлекаем текст (логика осталась прежней)
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        text = None
        if article_body:
            for element in (article_body.find_all("script") + article_body.find_all("style")):
                element.decompose()
            text = ' '.join(article_body.get_text().split())
            text = text[:8000] if len(text) > 200 else None
        
        return {'text': text, 'image_url': image_url}
        
    except requests.RequestException as e:
        print(f"🕸️ [WARN] Не удалось получить полный текст/картинку: {e}")
        # Возвращаем то, что смогли найти (например, картинку из RSS, даже если текст не спарсился)
        return {'text': None, 'image_url': image_url}

# --- 3. Функции для работы с AI (без изменений) ---

async def summarize_with_gemini(title, text, category_emoji):
    print(f"🤖 [AI] Отправляю в Gemini: {title}")
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
    response = await gemini_model.generate_content_async(f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text}")
    return response.text

async def summarize_with_gpt(title, text, category_emoji):
    print(f"🤖 [AI] Отправляю в GPT (резерв): {title}")
    system_prompt = f"""Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'. Ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

    {category_emoji} **Заголовок новости**

    *Главная суть новости в 2-3 предложениях. Объясни, почему это важно.*

    **Детали:**
    - Ключевой факт или цифра.
    - Контекст или причина.
    - Возможные последствия.

    #хэштег1 #хэштег2 #хэштег3
    """
    user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text}"
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]))
    return response.choices[0].message.content

async def get_ai_summary(title, text, category):
    category_emoji = category.split()[-1]
    try:
        return await summarize_with_gemini(title, text, category_emoji)
    except Exception as e:
        print(f"⚠️ [WARN] Ошибка Gemini: {e}. Переключаюсь на GPT...")
        try:
            return await summarize_with_gpt(title, text, category_emoji)
        except Exception as e_gpt:
            print(f"❌ [ERROR] Ошибка GPT: {e_gpt}. Оба AI провайдера недоступны.")
            return None

# --- 4. Основная логика ---

async def send_message_to_channel(bot, message, link, image_url):
    """
    Отправляет пост в канал. Если есть image_url - отправляет фото с подписью.
    Если нет - отправляет текстовое сообщение.
    """
    full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
    try:
        if image_url:
            # Отправляем фото с подписью. Подпись может быть до 1024 символов.
            await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=image_url, caption=full_message[:1024], parse_mode='Markdown')
            print(f"✅ [POST] Новость с картинкой успешно опубликована.")
        else:
            # Отправляем обычное текстовое сообщение
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
            print(f"✅ [POST] Новость (только текст) успешно опубликована.")
    except Exception as e:
        print(f"❌ [ERROR] Ошибка при отправке в Telegram: {e}")

async def main_loop():
    """Главный бесконечный цикл работы бота."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    posted_urls = load_posted_urls()
    print(f"✅ [START] Бот в рабочем режиме. Загружено {len(posted_urls)} ранее опубликованных ссылок.")
    
    while True:
        print(f"\n--- [CYCLE] Новая итерация проверки: {time.ctime()} ---")
        all_new_entries = []
        for category, url in RSS_FEEDS.items():
            print(f"📰 [FETCH] Проверяю RSS-ленту: {category}")
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link not in posted_urls:
                    all_new_entries.append((entry, category))
        
        sorted_entries = sorted(all_new_entries, key=lambda x: x[0].get('published_parsed', time.gmtime()))

        for entry, category in sorted_entries:
            print(f"🔍 [PROCESS] Обрабатываю новую статью: {entry.title}")
            
            content = get_article_content(entry.link, entry)
            full_text = content['text']
            image_url = content['image_url']
            
            if not full_text:
                print("📝 [INFO] Не удалось получить полный текст, использую краткое описание из RSS.")
                full_text = entry.summary

            formatted_post = await get_ai_summary(entry.title, full_text, category)

            if formatted_post:
                await send_message_to_channel(bot, formatted_post, entry.link, image_url)
                posted_urls.add(entry.link)
                save_posted_url(entry.link)
                
                print(f"🕒 [PAUSE] Публикация успешна. Следующая возможна через 15 минут.")
                await asyncio.sleep(900)
            else:
                print("❌ [SKIP] Не удалось обработать новость, оба AI не сработали.")
                await asyncio.sleep(5)

        print(f"--- [PAUSE] Проверка всех лент завершена. Следующая через 10 минут. ---")
        await asyncio.sleep(600)

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Бот остановлен вручную.")