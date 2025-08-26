import os
import telegram
import asyncio
import feedparser
import time
# --- Новые импорты ---
import google.generativeai as genai
from openai import OpenAI

print("✅ Универсальный бот запускается...")

# --- 1. Безопасная конфигурация для ДВУХ провайдеров ---
try:
    TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY'] # <-- Новый ключ
except KeyError as e:
    print(f"❌ Критическая ошибка: Не найдена переменная окружения {e}.")
    exit()

# Настройка клиентов для обоих API
# Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
# OpenAI (GPT)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --- (Остальная конфигурация без изменений) ---
RSS_FEEDS = {
    'Криптовалюты': 'https://cointelegraph.com/rss',
    'Экономика': 'https://feeds.reuters.com/reuters/businessNews',
    'ForkLog': 'https://forklog.com/feed'
}
posted_urls = set()

# --- 2. Функции для каждого AI и универсальный обработчик ---

async def summarize_with_gemini(title, summary):
    """Пытается обработать новость с помощью Gemini."""
    print(f"🤖 Отправляю на анализ в Gemini: {title}")
    prompt = f"""Ты — профессиональный редактор Telegram-канала. Проанализируй новость и верни краткую, структурированную выжимку на русском языке. Формат: **Заголовок**\n\n*Суть новости*.\n\n**Тезисы:**\n- Тезис 1\n- Тезис 2\n\n#хэштег1 #хэштег2"""
    response = await gemini_model.generate_content_async(f"{prompt}\n\nНовость: {title} - {summary}")
    return response.text

async def summarize_with_gpt(title, summary):
    """Пытается обработать новость с помощью GPT (запасной вариант)."""
    print(f"🤖 Отправляю на анализ в GPT: {title}")
    system_prompt = "Ты — профессиональный редактор Telegram-канала. Проанализируй новость и верни краткую, структурированную выжимку на русском языке. Формат: **Заголовок**\n\n*Суть новости*.\n\n**Тезисы:**\n- Тезис 1\n- Тезис 2\n\n#хэштег1 #хэштег2"
    user_prompt = f"Новость: {title} - {summary}"
    
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

async def summarize_universal(title, summary):
    """Универсальная функция: сначала пробует Gemini, при ошибке — GPT."""
    try:
        # Первая попытка - Gemini
        return await summarize_with_gemini(title, summary)
    except Exception as e:
        print(f"⚠️ Ошибка Gemini: {e}. Переключаюсь на GPT...")
        try:
            # Вторая попытка (резервная) - GPT
            return await summarize_with_gpt(title, summary)
        except Exception as e_gpt:
            print(f"❌ Ошибка GPT (резервный AI тоже не сработал): {e_gpt}")
            return None

async def send_message_to_channel(bot, message, link):
    """Отправляет финальное сообщение в Telegram-канал (без изменений)."""
    full_message = f"{message}\n\n🔗 [Читать первоисточник]({link})"
    try:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=full_message, parse_mode='Markdown', disable_web_page_preview=True)
        print(f"✅ Новость успешно опубликована в канале.")
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения в Telegram: {e}")

# --- 3. Главный цикл программы (теперь вызывает универсальную функцию) ---

async def main_loop():
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
                    
                    # ↓ ↓ ↓ ГЛАВНОЕ ИЗМЕНЕНИЕ ЗДЕСЬ ↓ ↓ ↓
                    formatted_post = await summarize_universal(entry.title, entry.summary)

                    if formatted_post:
                        await send_message_to_channel(bot, formatted_post, entry.link)
                        posted_urls.add(entry.link)
                    else:
                        print("Не удалось обработать новость, оба AI не сработали.")
                    
                    await asyncio.sleep(5) # Оставляем паузу для защиты от блокировок

        print("--- Проверка всех лент завершена. Следующая через 30 минут. ---")
        await asyncio.sleep(1800)

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")