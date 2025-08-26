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

print("✅ [INIT] Запуск финальной версии бота...")

# --- 1. Конфигурация ---
# Читаем "секреты" из переменных окружения.
try:
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
except KeyError as e:
    print(f"❌ [CRITICAL] Не найдена переменная окружения {e}. Завершение работы.")
    exit()

# Настройка клиентов для обоих AI
# Gemini (основной)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
# OpenAI (резервный)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Список RSS-лент для мониторинга
RSS_FEEDS = {
    'Майнинг РФ и Мир': 'https://bits.media/rss/',
    'Новости Майнинга': 'https://cointelegraph.com/rss/tag/mining',
    'Крипто-новости СНГ': 'https://forklog.com/feed',
    'Мировая Экономика': 'https://feeds.reuters.com/reuters/businessNews'
}

# Имя файла для хранения опубликованных ссылок
POSTED_URLS_FILE = 'posted_urls.txt'

# --- 2. Функции-помощники ---

def load_posted_urls():
    """Загружает опубликованные URL из файла в память при старте."""
    try:
        with open(POSTED_URLS_FILE, 'r') as f:
            # Используем set для быстрой проверки наличия элемента
            return set(line.strip() for line in f)
    except FileNotFoundError:
        print("ℹ️ [INFO] Файл с опубликованными URL не найден. Создаю новый.")
        return set()

def save_posted_url(url):
    """Добавляет новый URL в файл, обеспечивая постоянство памяти."""
    with open(POSTED_URLS_FILE, 'a') as f:
        f.write(url + '\n')

def get_full_article_text(url):
    """
    Заходит на страницу статьи и извлекает её полный текст.
    Это дает AI гораздо больше контекста, чем краткое описание из RSS.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Проверка на ошибки HTTP
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Поиск основного контента статьи (эти селекторы могут потребовать подстройки под конкретный сайт)
        article_body = soup.find('article') or soup.find('div', class_='post-content') or soup.find('body')
        
        if article_body:
            # Очистка от скриптов, стилей и лишних пробелов
            for element in (article_body.find_all("script") + article_body.find_all("style")):
                element.decompose()
            text = ' '.join(article_body.get_text().split())
            # Ограничиваем текст, чтобы не превышать лимиты токенов API
            return text[:8000] 
        return None
    except requests.RequestException as e:
        print(f"🕸️ [WARN] Не удалось получить полный текст статьи: {e}")
        return None

# --- 3. Функции для работы с AI ---

async def summarize_with_gemini(title, text, category):
    """Обрабатывает новость с помощью Gemini."""
    print(f"🤖 [AI] Отправляю в Gemini: {title}")
    prompt = f"""
    Ты — главный редактор ведущего Telegram-канала 'Crypto Compass'.
    Твоя задача — проанализировать полный текст новости из категории '{category}' и создать профессиональный, ёмкий пост.
    Ответ должен быть строго на русском языке и ТОЛЬКО в формате Markdown ниже. Никаких лишних фраз.

    **{title}**

    *(Здесь самая суть новости в 2-3 предложениях. Максимально информативно и без воды.)*

    **Ключевые тезисы:**
    - Главный вывод или событие.
    - Вторая по важности деталь или последствие.
    - Третий интересный факт или цифра.

    *(Сгенерируй 3-4 релевантных хэштега на русском, например: #майнинг #россия #закон)*
    """
    response = await gemini_model.generate_content_async(f"{prompt}\n\nТЕКСТ СТАТЬИ ДЛЯ АНАЛИЗА:\n{text}")
    return response.text

async def summarize_with_gpt(title, text, category):
    """Обрабатывает новость с помощью GPT (резервный вариант)."""
    print(f"🤖 [AI] Отправляю в GPT (резерв): {title}")
    system_prompt = f"""Ты — главный редактор ведущего Telegram-канала 'Crypto Compass'. Твоя задача — проанализировать полный текст новости из категории '{category}' и создать профессиональный, ёмкий пост. Ответ должен быть строго на русском языке и ТОЛЬКО в формате Markdown ниже. Никаких лишних фраз.

    **Заголовок новости**

    *Суть новости в 2-3 предложениях.*

    **Ключевые тезисы:**
    - Главный вывод.
    - Вторая деталь.
    - Третий факт.

    #хэштег1 #хэштег2 #хэштег3
    """
    user_prompt = f"Заголовок: {title}\n\nПолный текст статьи:\n{text}"
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
    )
    return response.choices[0].message.content

async def get_ai_summary(title, text, category):
    """Универсальная отказоустойчивая функция. Пробует Gemini, при любой ошибке — GPT."""
    try:
        return await summarize_with_gemini(title, text, category)
    except Exception as e:
        print(f"⚠️ [WARN] Ошибка Gemini: {e}. Переключаюсь на GPT...")
        try:
            return await summarize_with_gpt(title, text, category)
        except Exception as e_gpt:
            print(f"❌ [ERROR] Ошибка GPT: {e_gpt}. Оба AI провайдера недоступны.")
            return None

# --- 4. Основная логика ---

async def send_message_to_channel(bot, message, link):
    """Отправляет финальное сообщение в Telegram-канал."""
    full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
    try:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
        print(f"✅ [POST] Новость успешно опубликована в канале.")
    except Exception as e:
        print(f"❌ [ERROR] Ошибка при отправке в Telegram: {e}")

async def main_loop():
    """Главный бесконечный цикл работы бота."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    posted_urls = load_posted_urls()
    print(f"✅ [START] Бот в рабочем режиме. Загружено {len(posted_urls)} ранее опубликованных ссылок.")
    
    while True:
        print(f"\n--- [CYCLE] Новая итерация проверки: {time.ctime()} ---")
        for category, url in RSS_FEEDS.items():
            print(f"📰 [FETCH] Проверяю RSS-ленту: {category}")
            feed = feedparser.parse(url)
            
            for entry in reversed(feed.entries):
                if entry.link not in posted_urls:
                    print(f"🔍 [NEW] Найдена новая статья: {entry.title}")
                    
                    full_text = get_full_article_text(entry.link)
                    if not full_text:
                        print("📝 [SKIP] Не удалось получить полный текст, используем краткое описание из RSS.")
                        full_text = entry.summary

                    formatted_post = await get_ai_summary(entry.title, full_text, category)

                    if formatted_post:
                        await send_message_to_channel(bot, formatted_post, entry.link)
                        posted_urls.add(entry.link)
                        save_posted_url(entry.link)
                    else:
                        print("❌ [SKIP] Не удалось обработать новость, оба AI не сработали.")
                    
                    # Пауза для соблюдения лимитов API и избежания спама
                    await asyncio.sleep(10)

        print(f"--- [PAUSE] Проверка завершена. Следующая через 30 минут. ---")
        await asyncio.sleep(1800)

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\n[STOP] Бот остановлен вручную.")