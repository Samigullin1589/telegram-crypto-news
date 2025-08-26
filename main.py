import os
import telegram
import asyncio
import feedparser
import google.generativeai as genai
import time

print("✅ Бот запускается...")

# --- 1. Безопасная конфигурация ---
# Читаем "секреты" из переменных окружения. На Render мы их укажем в настройках.
try:
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
except KeyError as e:
    print(f"❌ Критическая ошибка: Не найдена переменная окружения {e}.")
    print("При локальном запуске убедитесь, что у вас есть файл .env или переменные заданы системно.")
    exit() # Выходим, если ключей нет

# Настройка доступа к Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Список RSS-лент для мониторинга
RSS_FEEDS = {
    'Криптовалюты': 'https://cointelegraph.com/rss',
    'Экономика': 'https://feeds.reuters.com/reuters/businessNews',
    'ForkLog': 'https://forklog.com/feed'
}

# Множество для хранения URL уже опубликованных новостей, чтобы избежать дублей.
# При каждом перезапуске скрипта оно будет обнуляться.
# Для постоянного хранения лучше использовать файл или базу данных SQLite.
posted_urls = set()

# --- 2. Основные асинхронные функции ---

async def summarize_with_ai(title, summary):
    """Отправляет новость в Gemini для анализа и форматирования."""
    print(f"🤖 Отправляю на анализ: {title}")
    prompt = f"""
    Ты — профессиональный редактор Telegram-канала о криптовалютах и экономике.
    Проанализируй новость и верни краткую, структурированную выжимку на русском языке.
    Твой ответ должен быть ТОЛЬКО в следующем формате:

    **{title}**

    *(Здесь краткая суть новости в 2-3 предложениях)*

    **Ключевые моменты:**
    - Первый важный тезис.
    - Второй важный тезис.
    - Третий важный тезис.

    #хэштег1 #хэштег2 #хэштег3
    """
    try:
        # Используем асинхронный вызов к модели
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Ошибка при обращении к Gemini API: {e}")
        return None

async def send_message_to_channel(bot, message, link):
    """Форматирует и отправляет финальное сообщение в Telegram-канал."""
    # Добавляем к сообщению от AI ссылку на источник
    full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=full_message,
            parse_mode='Markdown',
            disable_web_page_preview=True # Отключаем превью ссылки, чтобы пост выглядел чище
        )
        print(f"✅ Новость успешно опубликована в канале.")
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения в Telegram: {e}")

# --- 3. Главный цикл программы ---

async def main_loop():
    """Бесконечный цикл, который проверяет новости и публикует их."""
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    print("Бот в рабочем режиме. Начинаю проверку новостей...")
    while True:
        print(f"\n--- Новая итерация проверки: {time.ctime()} ---")
        for category, url in RSS_FEEDS.items():
            print(f"Проверяю RSS-ленту: {category}")
            feed = feedparser.parse(url)

            for entry in reversed(feed.entries):
                if entry.link not in posted_urls:
                    print(f"🔍 Найдена новая статья: {entry.title}")

                    formatted_post = await summarize_with_ai(entry.title, entry.summary)

                    if formatted_post:
                        await send_message_to_channel(bot, formatted_post, entry.link)
                        posted_urls.add(entry.link)
                    else:
                        print("Не удалось обработать новость, пропускаю.")

                    # !!! ВОТ ВАЖНОЕ ИЗМЕНЕНИЕ !!!
                    # Добавляем небольшую паузу в 5 секунд ПОСЛЕ КАЖДОЙ новой статьи,
                    # чтобы никогда не превышать лимит запросов в минуту.
                    await asyncio.sleep(5)

        print("--- Проверка всех лент завершена. Следующая через 30 минут. ---")
        await asyncio.sleep(1800) # 30 минут

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")