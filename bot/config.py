# bot/config.py
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FeedConfig:
    """Конфигурация RSS фида с приоритетом и метаданными"""
    url: str
    priority: int  # 1-10, где 10 = максимальный приоритет
    timeout: int = 20
    enabled: bool = True
    
    def __post_init__(self):
        if not 1 <= self.priority <= 10:
            raise ValueError(f"Priority must be between 1-10, got {self.priority}")


class Config:
    """
    Централизованная конфигурация с валидацией и умными дефолтами
    Singleton pattern для единой точки доступа
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # === Telegram Configuration ===
        self.TELEGRAM_BOT_TOKEN = self._get_required_env('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHANNEL_ID = self._get_required_env('TELEGRAM_CHANNEL_ID')
        
        # === AI Configuration ===
        self.GEMINI_API_KEY = self._get_required_env('GEMINI_API_KEY')
        self.OPENAI_API_KEY = self._get_required_env('OPENAI_API_KEY')
        
        # AI Models
        self.GEMINI_MODEL = 'gemini-1.5-pro'
        self.OPENAI_MODEL = 'gpt-4o'
        
        # AI Retry Strategy
        self.AI_MAX_RETRIES = 3
        self.AI_BACKOFF_FACTOR = 10
        self.AI_TIMEOUT = 60
        
        # === Optional API Keys (новые) ===
        # CoinGecko - для цен криптовалют (РЕКОМЕНДУЕТСЯ)
        self.COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
        
        # Alchemy - альтернатива Etherscan (опционально)
        self.ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
        
        # CoinMarketCap - альтернатива CoinGecko (опционально)
        self.COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
        
        # CryptoPanic - агрегатор новостей (опционально)
        self.CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY')
        
        # NewsAPI - новости (опционально)
        self.NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
        
        # === RSS Feeds Configuration ===
        self.RSS_FEEDS: Dict[str, FeedConfig] = {
            'Крипто и Блокчейн РФ/СНГ 🇷🇺': FeedConfig(
                url='https://habr.com/ru/rss/hubs/cryptocurrency/',
                priority=8,  # Высокий приоритет для локального контента
                timeout=25
            ),
            'Новости Майнинга (Мир) ⚙️': FeedConfig(
                url='https://cointelegraph.com/rss/tag/mining',
                priority=7,
                timeout=40  # Увеличен таймаут для проблемного фида
            ),
            'Крипто-новости СНГ 💡': FeedConfig(
                url='https://forklog.com/feed',
                priority=9,  # Максимальный приоритет для оперативности
                timeout=20
            ),
            'Мировые Крипто-новости 🌍': FeedConfig(
                url='https://www.coindesk.com/arc/outboundfeeds/rss/',
                priority=6,
                timeout=25
            ),
            'Глубокая аналитика (Eng) 🧐': FeedConfig(
                url='https://www.theblock.co/rss.xml',
                priority=7,
                timeout=40  # Увеличен таймаут для проблемного фида
            )
        }
        
        # === Timing Configuration ===
        self.POST_DELAY_SECONDS = int(os.getenv('POST_DELAY_SECONDS', '900'))  # 15 минут
        self.IDLE_DELAY_SECONDS = int(os.getenv('IDLE_DELAY_SECONDS', '300'))  # 5 минут
        self.FEED_FETCH_TIMEOUT = 30
        
        # === Database Configuration ===
        mount_path = os.environ.get('RENDER_DISK_MOUNT_PATH', '.')
        self.DB_PATH = Path(mount_path) / 'news_database.sqlite'
        self.DB_BACKUP_ENABLED = True
        self.DB_BACKUP_INTERVAL_HOURS = 24
        
        # === Image Configuration ===
        self.MIN_IMAGE_WIDTH = int(os.getenv('MIN_IMAGE_WIDTH', '400'))
        self.MIN_IMAGE_HEIGHT = int(os.getenv('MIN_IMAGE_HEIGHT', '200'))
        self.IMAGE_CHECK_TIMEOUT = 10
        self.IMAGE_PARTIAL_READ_BYTES = 8192
        
        # === HTTP Configuration ===
        self.COMMON_HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Session Configuration
        self.SESSION_TIMEOUT_TOTAL = 300  # 5 минут общий timeout
        self.SESSION_TIMEOUT_CONNECT = 30
        self.SESSION_MAX_RETRIES = 3
        
        # === Content Parsing ===
        self.MAX_ARTICLE_TEXT_LENGTH = 12000
        self.MAX_SUMMARY_RETRIES = 2
        
        # === Logging Configuration ===
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
        
        self._initialized = True
        self._validate_config()
    
    def _get_required_env(self, key: str) -> str:
        """Получает обязательную переменную окружения"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
    
    def _get_optional_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получает опциональную переменную окружения"""
        return os.getenv(key, default)
    
    def has_coingecko(self) -> bool:
        """Проверяет наличие CoinGecko API ключа"""
        return bool(self.COINGECKO_API_KEY)
    
    def has_alchemy(self) -> bool:
        """Проверяет наличие Alchemy API ключа"""
        return bool(self.ALCHEMY_API_KEY)
    
    def has_coinmarketcap(self) -> bool:
        """Проверяет наличие CoinMarketCap API ключа"""
        return bool(self.COINMARKETCAP_API_KEY)
    
    def _validate_config(self):
        """Валидация конфигурации при инициализации"""
        # Проверка корректности ID канала
        if not self.TELEGRAM_CHANNEL_ID.startswith('@') and not self.TELEGRAM_CHANNEL_ID.startswith('-'):
            print(f"⚠️  [CONFIG] Channel ID '{self.TELEGRAM_CHANNEL_ID}' может быть некорректным")
        
        # Проверка наличия хотя бы одного активного фида
        active_feeds = [name for name, feed in self.RSS_FEEDS.items() if feed.enabled]
        if not active_feeds:
            raise ValueError("No active RSS feeds configured")
        
        print(f"✅ [CONFIG] Валидация пройдена. Активных фидов: {len(active_feeds)}")
        
        # Информация об опциональных API
        if self.has_coingecko():
            print("✅ [CONFIG] CoinGecko API настроен")
        else:
            print("⚠️  [CONFIG] CoinGecko API не найден (рекомендуется для цен)")
    
    def get_sorted_feeds(self) -> List[tuple]:
        """Возвращает фиды отсортированные по приоритету (высший первым)"""
        return sorted(
            [(name, feed) for name, feed in self.RSS_FEEDS.items() if feed.enabled],
            key=lambda x: x[1].priority,
            reverse=True
        )
    
    def get_feed_by_name(self, name: str) -> FeedConfig:
        """Получает конфигурацию фида по имени"""
        if name not in self.RSS_FEEDS:
            raise KeyError(f"Feed '{name}' not found in configuration")
        return self.RSS_FEEDS[name]
    
    @property
    def ai_prompt_template(self) -> str:
        """Централизованный промпт для AI"""
        return """
Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.

Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже. Не добавляй никаких комментариев или вводных фраз. Твой ответ должен начинаться сразу с заголовка.

{emoji} **{title}**

*Здесь напиши главную суть новости в 2-3 предложениях. Используй профессиональный, но понятный язык. Объясни, почему это важно.*

**Детали:**
- Ключевой факт или цифра из статьи.
- Контекст или причина произошедшего.
- Возможные последствия для рынка или индустрии.

*(Сгенерируй 3 релевантных хэштега на русском, например: #биткоин #регулирование #SEC)*
"""


# Глобальный экземпляр конфигурации
config = Config()

# Обратная совместимость со старым кодом
TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHANNEL_ID = config.TELEGRAM_CHANNEL_ID
GEMINI_API_KEY = config.GEMINI_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY
RSS_FEEDS = {name: feed.url for name, feed in config.RSS_FEEDS.items()}
POST_DELAY_SECONDS = config.POST_DELAY_SECONDS
IDLE_DELAY_SECONDS = config.IDLE_DELAY_SECONDS
DB_PATH = str(config.DB_PATH)
MIN_IMAGE_WIDTH = config.MIN_IMAGE_WIDTH
MIN_IMAGE_HEIGHT = config.MIN_IMAGE_HEIGHT
COMMON_HEADERS = config.COMMON_HEADERS