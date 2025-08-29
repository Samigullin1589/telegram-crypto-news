# bot/config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

RSS_FEEDS = {
    'Крипто и Блокчейн РФ/СНГ 🇷🇺': 'https://habr.com/ru/rss/hubs/cryptocurrency/',
    'Новости Майнинга (Мир) ⚙️': 'https://cointelegraph.com/rss/tag/mining',
    'Крипто-новости СНГ 💡': 'https://forklog.com/feed',
    'Мировые Крипто-новости 🌍': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'Майнинг и Железо (СНГ) 💻': 'https://forklog.com/hub/mining/feed'
}

POST_DELAY_SECONDS = 900
IDLE_DELAY_SECONDS = 300
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')
MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 200

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, GEMINI_API_KEY, OPENAI_API_KEY]):
    raise ValueError("Не все переменные окружения установлены. Проверьте .env файл.")