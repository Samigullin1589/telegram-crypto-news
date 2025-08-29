# bot/config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ==============================================================================
# ВЕРСИЯ 15.0 - THE EDITOR'S CUT
# ФИНАЛЬНАЯ РЕДАКЦИОННАЯ СТРАТЕГИЯ ИСТОЧНИКОВ
# ==============================================================================
RSS_FEEDS = {
    # 1. Технические статьи и аналитика от сообщества РФ/СНГ.
    'Крипто и Блокчейн РФ/СНГ 🇷🇺': 'https://habr.com/ru/rss/hubs/cryptocurrency/',
    
    # 2. Новости мировой индустрии майнинга.
    'Новости Майнинга (Мир) ⚙️': 'https://cointelegraph.com/rss/tag/mining',
    
    # 3. Оперативные "горячие" новости из СНГ.
    'Крипто-новости СНГ 💡': 'https://forklog.com/feed',
    
    # 4. Общие новости мирового крипто-рынка.
    'Мировые Крипто-новости 🌍': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    
    # 5. ИЗМЕНЕНО: Глубокая аналитика и исследования от ведущего издания.
    'Глубокая аналитика (Eng) 🧐': 'https://www.theblock.co/rss.xml'
}

POST_DELAY_SECONDS = 900
IDLE_DELAY_SECONDS = 300
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')
MIN_IMAGE_WIDTH = 400
MIN_IMAGE_HEIGHT = 200

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, GEMINI_API_KEY, OPENAI_API_KEY]):
    raise ValueError("Не все переменные окружения установлены. Проверьте .env файл.")