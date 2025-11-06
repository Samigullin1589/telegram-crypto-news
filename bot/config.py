# bot/config.py - BOT CONFIG v4.1 - PRODUCTION READY

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FeedConfig:
    url: str
    priority: int
    timeout: int = 30
    enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 5
    fallback_urls: List[str] = None
    category: str = 'general'
    language: str = 'ru'
    
    def __post_init__(self):
        if not 1 <= self.priority <= 10:
            raise ValueError(f"Priority must be between 1-10, got {self.priority}")
        
        if self.fallback_urls is None:
            self.fallback_urls = []


class Config:
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print("\n" + "="*80)
        print("⚙️  BOT CONFIG v4.1 - INITIALIZATION")
        print("="*80 + "\n")
        
        self.TELEGRAM_BOT_TOKEN = self._get_required_env('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHANNEL_ID = self._get_required_env('TELEGRAM_CHANNEL_ID')
        self.ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', self.TELEGRAM_CHANNEL_ID)
        
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
        
        self.GEMINI_MODEL = 'gemini-1.5-flash'
        self.OPENAI_MODEL = 'gpt-4o-mini'
        self.ANTHROPIC_MODEL = 'claude-3-haiku-20240307'
        
        self.AI_MAX_RETRIES = 3
        self.AI_BACKOFF_FACTOR = 2
        self.AI_TIMEOUT = 60
        self.AI_MAX_TOKENS = 1000
        self.AI_TEMPERATURE = 0.3
        
        self.ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
        self.BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', '')
        self.POLYGONSCAN_API_KEY = os.getenv('POLYGONSCAN_API_KEY', '')
        self.ARBISCAN_API_KEY = os.getenv('ARBISCAN_API_KEY', '')
        self.BASESCAN_API_KEY = os.getenv('BASESCAN_API_KEY', '')
        self.SNOWTRACE_API_KEY = os.getenv('SNOWTRACE_API_KEY', '')
        self.OPTIMISM_ETHERSCAN_API_KEY = os.getenv('OPTIMISM_ETHERSCAN_API_KEY', '')
        self.FTMSCAN_API_KEY = os.getenv('FTMSCAN_API_KEY', '')
        
        self.HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
        self.SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')
        
        self.COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
        self.ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
        self.COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
        self.CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY')
        self.NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
        self.DEXSCREENER_API_KEY = os.getenv('DEXSCREENER_API_KEY')
        self.BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')
        
        self.RSS_FEEDS: Dict[str, FeedConfig] = {
            'Крипто и Блокчейн РФ/СНГ 🇷🇺': FeedConfig(
                url='https://habr.com/ru/rss/hubs/cryptocurrency/',
                priority=8,
                timeout=25,
                max_retries=3,
                category='blockchain',
                language='ru',
                fallback_urls=[
                    'https://habr.com/ru/rss/hub/cryptocurrency/',
                    'https://habr.com/ru/rss/hubs/blockchain/'
                ]
            ),
            'Новости Майнинга (Мир) ⚙️': FeedConfig(
                url='https://cointelegraph.com/rss/tag/mining',
                priority=7,
                timeout=50,
                max_retries=5,
                retry_delay=10,
                category='mining',
                language='en',
                fallback_urls=[
                    'https://cointelegraph.com/rss',
                    'https://cryptopotato.com/feed/'
                ]
            ),
            'Крипто-новости СНГ 💡': FeedConfig(
                url='https://forklog.com/feed',
                priority=9,
                timeout=20,
                max_retries=3,
                category='news',
                language='ru',
                fallback_urls=[
                    'https://forklog.com/feed/',
                    'https://bits.media/feed/'
                ]
            ),
            'Мировые Крипто-новости 🌍': FeedConfig(
                url='https://www.coindesk.com/arc/outboundfeeds/rss/',
                priority=6,
                timeout=25,
                max_retries=3,
                category='news',
                language='en',
                fallback_urls=[
                    'https://coindesk.com/arc/outboundfeeds/rss',
                    'https://decrypt.co/feed'
                ]
            ),
            'Глубокая аналитика (Eng) 🧐': FeedConfig(
                url='https://www.theblock.co/rss.xml',
                priority=7,
                timeout=50,
                max_retries=5,
                retry_delay=10,
                category='analytics',
                language='en',
                fallback_urls=[
                    'https://theblock.co/rss',
                    'https://cryptobriefing.com/feed/',
                    'https://thedefiant.io/feed'
                ]
            ),
            'Bitcoin Magazine 📰': FeedConfig(
                url='https://bitcoinmagazine.com/.rss/full/',
                priority=6,
                timeout=25,
                max_retries=3,
                category='bitcoin',
                language='en'
            ),
            'CryptoPanic News 🚨': FeedConfig(
                url='https://cryptopanic.com/api/v1/posts/?auth_token=public&kind=news',
                priority=8,
                timeout=20,
                max_retries=3,
                category='news',
                language='en',
                enabled=True
            ),
            'Ethereum Foundation Blog 💎': FeedConfig(
                url='https://blog.ethereum.org/feed.xml',
                priority=7,
                timeout=30,
                max_retries=3,
                category='ethereum',
                language='en',
                enabled=True
            ),
            'Binance Academy 📚': FeedConfig(
                url='https://academy.binance.com/en/rss.xml',
                priority=6,
                timeout=25,
                max_retries=3,
                category='education',
                language='en',
                enabled=True
            ),
            'Cointelegraph Ru 🇷🇺': FeedConfig(
                url='https://ru.cointelegraph.com/rss',
                priority=8,
                timeout=30,
                max_retries=3,
                category='news',
                language='ru',
                fallback_urls=[
                    'https://ru.cointelegraph.com/rss/',
                ]
            ),
        }
        
        self.FETCH_INTERVAL = int(os.getenv('FETCH_INTERVAL', '300'))
        self.POSTS_PER_HOUR_CAP = int(os.getenv('POSTS_PER_HOUR_CAP', '3'))
        self.MIN_CONFIDENCE_SCORE = int(os.getenv('MIN_CONFIDENCE_SCORE', '70'))
        self.NEWS_CHECK_INTERVAL = self.FETCH_INTERVAL
        
        self.WHALE_THRESHOLDS = {
            'ethereum': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'bsc': {
                'min_native_value': 100,
                'min_usd_value': 50000,
                'whale_threshold_usd': 500000,
                'mega_whale_threshold_usd': 5000000
            },
            'polygon': {
                'min_native_value': 50000,
                'min_usd_value': 25000,
                'whale_threshold_usd': 250000,
                'mega_whale_threshold_usd': 2500000
            },
            'arbitrum': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'optimism': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'base': {
                'min_native_value': 50,
                'min_usd_value': 100000,
                'whale_threshold_usd': 1000000,
                'mega_whale_threshold_usd': 10000000
            },
            'avalanche': {
                'min_native_value': 500,
                'min_usd_value': 15000,
                'whale_threshold_usd': 150000,
                'mega_whale_threshold_usd': 1500000
            },
            'solana': {
                'min_native_value': 100,
                'min_usd_value': 10000,
                'whale_threshold_usd': 100000,
                'mega_whale_threshold_usd': 1000000
            }
        }
        
        self.ENABLED_CHAINS = os.getenv('ENABLED_CHAINS', 'ethereum,solana,bsc,polygon,arbitrum,base,optimism,avalanche').split(',')
        
        self.MIN_USD = float(os.getenv('MIN_USD', '100000'))
        
        self.WHALE_ENABLED = os.getenv('WHALE_ENABLED', 'true').lower() == 'true'
        self.NEWS_ENABLED = os.getenv('NEWS_ENABLED', 'true').lower() == 'true'
        self.ANALYTICS_ENABLED = os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true'
        self.TRADING_ENABLED = os.getenv('TRADING_ENABLED', 'false').lower() == 'true'
        self.HYPERLIQUID_ENABLED = os.getenv('HYPERLIQUID_ENABLED', 'false').lower() == 'true'
        
        self.POST_DELAY_SECONDS = int(os.getenv('POST_DELAY_SECONDS', '900'))
        self.IDLE_DELAY_SECONDS = int(os.getenv('IDLE_DELAY_SECONDS', '300'))
        self.FEED_FETCH_TIMEOUT = 30
        self.RATE_LIMIT_DELAY_SECONDS = 60
        
        self._setup_paths()
        
        self.MIN_IMAGE_WIDTH = int(os.getenv('MIN_IMAGE_WIDTH', '400'))
        self.MIN_IMAGE_HEIGHT = int(os.getenv('MIN_IMAGE_HEIGHT', '200'))
        self.MAX_IMAGE_SIZE_MB = int(os.getenv('MAX_IMAGE_SIZE_MB', '10'))
        self.IMAGE_CHECK_TIMEOUT = 10
        self.IMAGE_PARTIAL_READ_BYTES = 8192
        self.IMAGE_QUALITY = 85
        self.IMAGE_COMPRESSION_ENABLED = True
        
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
        
        self.SESSION_TIMEOUT_TOTAL = 300
        self.SESSION_TIMEOUT_CONNECT = 30
        self.SESSION_MAX_RETRIES = 3
        self.SESSION_RETRY_DELAY = 5
        self.CONNECTION_POOL_SIZE = 100
        self.CONNECTION_POOL_MAX_SIZE = 200
        
        self.MAX_ARTICLE_TEXT_LENGTH = 12000
        self.MAX_SUMMARY_LENGTH = 500
        self.MAX_SUMMARY_RETRIES = 2
        self.SUMMARY_ENABLED = True
        
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
        self.DEBUG_MODE = os.getenv('DEBUG', 'false').lower() == 'true'
        self.LOG_FILE_ENABLED = os.getenv('LOG_FILE_ENABLED', 'false').lower() == 'true'
        self.LOG_FILE_PATH = self.DATA_DIR / 'logs' / 'bot.log'
        
        if self.LOG_FILE_ENABLED:
            self.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        self.RATE_LIMIT_ENABLED = True
        self.MAX_REQUESTS_PER_MINUTE = 60
        self.MAX_API_CALLS_PER_SECOND = 5
        self.RATE_LIMIT_BURST = 10
        
        self.CACHE_ENABLED = True
        self.CACHE_TTL_SECONDS = 3600
        self.CACHE_MAX_SIZE_MB = 100
        
        self.RETRY_ENABLED = True
        self.RETRY_MAX_ATTEMPTS = 3
        self.RETRY_INITIAL_DELAY = 1
        self.RETRY_MAX_DELAY = 60
        self.RETRY_EXPONENTIAL_BASE = 2
        
        self.HEALTH_CHECK_ENABLED = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
        self.HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
        self.HEALTH_CHECK_TIMEOUT = 10
        
        self.METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
        self.METRICS_INTERVAL = int(os.getenv('METRICS_INTERVAL', '60'))
        
        self.PORT = int(os.getenv('PORT', '8000'))
        self.HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', '30'))
        self.RPC_TIMEOUT = int(os.getenv('RPC_TIMEOUT', '15'))
        self.WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', '10'))
        
        self.MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', '450'))
        self.GC_INTERVAL_SECONDS = int(os.getenv('GC_INTERVAL_SECONDS', '300'))
        
        self.NOTIFICATION_CHANNELS = {
            'whale_alerts': self.TELEGRAM_CHANNEL_ID,
            'news': self.TELEGRAM_CHANNEL_ID,
            'analytics': self.TELEGRAM_CHANNEL_ID,
            'errors': self.ADMIN_CHAT_ID,
            'health': self.ADMIN_CHAT_ID
        }
        
        self.TELEGRAM_MAX_MESSAGE_LENGTH = 4096
        self.TELEGRAM_MAX_CAPTION_LENGTH = 1024
        self.TELEGRAM_RETRY_AFTER_DELAY = 5
        self.TELEGRAM_RATE_LIMIT_DELAY = 1
        
        self.BLOCKCHAIN_EXPLORERS = {
            'ethereum': 'https://etherscan.io',
            'bsc': 'https://bscscan.com',
            'polygon': 'https://polygonscan.com',
            'arbitrum': 'https://arbiscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'base': 'https://basescan.org',
            'avalanche': 'https://snowtrace.io',
            'solana': 'https://solscan.io',
            'fantom': 'https://ftmscan.com'
        }
        
        self.CHAIN_NATIVE_SYMBOLS = {
            'ethereum': 'ETH',
            'bsc': 'BNB',
            'polygon': 'MATIC',
            'arbitrum': 'ETH',
            'optimism': 'ETH',
            'base': 'ETH',
            'avalanche': 'AVAX',
            'solana': 'SOL',
            'fantom': 'FTM'
        }
        
        self.CHAIN_NAMES = {
            'ethereum': 'Ethereum',
            'bsc': 'BNB Chain',
            'polygon': 'Polygon',
            'arbitrum': 'Arbitrum',
            'optimism': 'Optimism',
            'base': 'Base',
            'avalanche': 'Avalanche',
            'solana': 'Solana',
            'fantom': 'Fantom'
        }
        
        self.CHAIN_COLORS = {
            'ethereum': '#627EEA',
            'bsc': '#F3BA2F',
            'polygon': '#8247E5',
            'arbitrum': '#28A0F0',
            'optimism': '#FF0420',
            'base': '#0052FF',
            'avalanche': '#E84142',
            'solana': '#14F195',
            'fantom': '#1969FF'
        }
        
        self.CHAIN_EMOJIS = {
            'ethereum': '🔷',
            'bsc': '🟡',
            'polygon': '🟣',
            'arbitrum': '🔵',
            'optimism': '🔴',
            'base': '🔵',
            'avalanche': '🔺',
            'solana': '🌅',
            'fantom': '👻'
        }
        
        self._initialized = True
        self._validate_config()
        self._print_summary()
    
    def _setup_paths(self):
        """Настройка путей к данным с fallback логикой"""
        base_dir = Path.cwd()
        
        data_root = Path('data')
        data_root.mkdir(parents=True, exist_ok=True)
        
        self.DATA_DIR = data_root
        
        self.DB_PATH = self.DATA_DIR / 'news_database.sqlite'
        self.NEWS_DB_PATH = self.DB_PATH
        self.DB_BACKUP_ENABLED = True
        self.DB_BACKUP_INTERVAL_HOURS = 24
        self.DB_MAX_AGE_DAYS = 90
        
        self.STATE_FILE = self.DATA_DIR / 'state.json'
        self.WALLET_DB_JSON_PATH = self.DATA_DIR / 'wallets.json'
        
        self.CACHE_DIR = self.DATA_DIR / 'cache'
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        (self.DATA_DIR / 'history').mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / 'learning').mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / 'wallets').mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / 'positions').mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / 'performance').mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / 'backups').mkdir(parents=True, exist_ok=True)
        
        print(f"✅ [PATHS] Data directory: {self.DATA_DIR.absolute()}")
        print(f"✅ [PATHS] Database: {self.DB_PATH.absolute()}")
    
    def _get_required_env(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
    
    def _get_optional_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)
    
    def has_scanner_api_key(self, chain: str) -> bool:
        key_mapping = {
            'ethereum': self.ETHERSCAN_API_KEY,
            'bsc': self.BSCSCAN_API_KEY,
            'polygon': self.POLYGONSCAN_API_KEY,
            'arbitrum': self.ARBISCAN_API_KEY,
            'base': self.BASESCAN_API_KEY,
            'avalanche': self.SNOWTRACE_API_KEY,
            'optimism': self.OPTIMISM_ETHERSCAN_API_KEY,
            'fantom': self.FTMSCAN_API_KEY,
            'solana': self.HELIUS_API_KEY or self.SOLSCAN_API_KEY
        }
        return bool(key_mapping.get(chain, ''))
    
    def get_scanner_api_key(self, chain: str) -> Optional[str]:
        key_mapping = {
            'ethereum': self.ETHERSCAN_API_KEY,
            'bsc': self.BSCSCAN_API_KEY,
            'polygon': self.POLYGONSCAN_API_KEY,
            'arbitrum': self.ARBISCAN_API_KEY,
            'base': self.BASESCAN_API_KEY,
            'avalanche': self.SNOWTRACE_API_KEY,
            'optimism': self.OPTIMISM_ETHERSCAN_API_KEY,
            'fantom': self.FTMSCAN_API_KEY,
            'solana': self.HELIUS_API_KEY or self.SOLSCAN_API_KEY
        }
        return key_mapping.get(chain)
    
    def get_missing_scanner_keys(self) -> List[str]:
        return [chain for chain in self.ENABLED_CHAINS if not self.has_scanner_api_key(chain)]
    
    def has_coingecko(self) -> bool:
        return bool(self.COINGECKO_API_KEY)
    
    def has_alchemy(self) -> bool:
        return bool(self.ALCHEMY_API_KEY)
    
    def has_coinmarketcap(self) -> bool:
        return bool(self.COINMARKETCAP_API_KEY)
    
    def has_ai_provider(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY or self.GEMINI_API_KEY)
    
    def get_ai_provider(self) -> Optional[str]:
        if self.OPENAI_API_KEY:
            return 'openai'
        elif self.ANTHROPIC_API_KEY:
            return 'anthropic'
        elif self.GEMINI_API_KEY:
            return 'gemini'
        return None
    
    def get_chain_explorer_url(self, chain: str, address: str = None, tx_hash: str = None) -> str:
        base_url = self.BLOCKCHAIN_EXPLORERS.get(chain, '')
        
        if not base_url:
            return ''
        
        if tx_hash:
            return f"{base_url}/tx/{tx_hash}"
        elif address:
            return f"{base_url}/address/{address}"
        else:
            return base_url
    
    def get_chain_symbol(self, chain: str) -> str:
        return self.CHAIN_NATIVE_SYMBOLS.get(chain, 'UNKNOWN')
    
    def get_chain_name(self, chain: str) -> str:
        return self.CHAIN_NAMES.get(chain, chain.capitalize())
    
    def get_chain_emoji(self, chain: str) -> str:
        return self.CHAIN_EMOJIS.get(chain, '⛓️')
    
    def get_chain_color(self, chain: str) -> str:
        return self.CHAIN_COLORS.get(chain, '#000000')
    
    def is_chain_enabled(self, chain: str) -> bool:
        return chain in self.ENABLED_CHAINS
    
    def _validate_config(self):
        if not self.TELEGRAM_CHANNEL_ID.startswith('@') and not self.TELEGRAM_CHANNEL_ID.startswith('-'):
            print(f"⚠️  [CONFIG] Channel ID '{self.TELEGRAM_CHANNEL_ID}' может быть некорректным")
        
        active_feeds = [name for name, feed in self.RSS_FEEDS.items() if feed.enabled]
        if not active_feeds:
            print("⚠️  [CONFIG] No active RSS feeds configured")
        
        if not self.has_ai_provider():
            print("⚠️  [CONFIG] No AI provider configured (OpenAI/Anthropic/Gemini)")
        
        missing_keys = self.get_missing_scanner_keys()
        if missing_keys:
            print(f"⚠️  [CONFIG] Missing API keys for: {', '.join(missing_keys)}")
    
    def _print_summary(self):
        print("✅ [CONFIG] Configuration validated successfully")
        print(f"   Active feeds: {len([f for f in self.RSS_FEEDS.values() if f.enabled])}")
        print(f"   Enabled chains: {', '.join(self.ENABLED_CHAINS)}")
        print(f"   AI Provider: {self.get_ai_provider() or 'None'}")
        print(f"   Features: Whale={self.WHALE_ENABLED}, News={self.NEWS_ENABLED}, Analytics={self.ANALYTICS_ENABLED}")
        print(f"   Database: {self.DB_PATH}")
        print("")
    
    def get_sorted_feeds(self) -> List[tuple]:
        return sorted(
            [(name, feed) for name, feed in self.RSS_FEEDS.items() if feed.enabled],
            key=lambda x: x[1].priority,
            reverse=True
        )
    
    def get_feed_by_name(self, name: str) -> FeedConfig:
        if name not in self.RSS_FEEDS:
            raise KeyError(f"Feed '{name}' not found in configuration")
        return self.RSS_FEEDS[name]
    
    def get_feed_config(self, name: str) -> Optional[FeedConfig]:
        return self.RSS_FEEDS.get(name)
    
    def get_all_feeds(self) -> Dict[str, FeedConfig]:
        return self.RSS_FEEDS
    
    def get_enabled_feeds(self) -> Dict[str, FeedConfig]:
        return {name: feed for name, feed in self.RSS_FEEDS.items() if feed.enabled}
    
    def enable_feed(self, name: str):
        if name in self.RSS_FEEDS:
            self.RSS_FEEDS[name].enabled = True
    
    def disable_feed(self, name: str):
        if name in self.RSS_FEEDS:
            self.RSS_FEEDS[name].enabled = False
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        return self.WHALE_THRESHOLDS.get(chain, {
            'min_native_value': 10,
            'min_usd_value': 10000,
            'whale_threshold_usd': 100000,
            'mega_whale_threshold_usd': 1000000
        })
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        threshold = self.get_whale_threshold(chain)
        return usd_value >= threshold.get('whale_threshold_usd', 1000000)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        threshold = self.get_whale_threshold(chain)
        return usd_value >= threshold.get('mega_whale_threshold_usd', 10000000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'telegram': {
                'bot_token': '***' if self.TELEGRAM_BOT_TOKEN else None,
                'channel_id': self.TELEGRAM_CHANNEL_ID,
                'admin_chat_id': self.ADMIN_CHAT_ID
            },
            'ai': {
                'provider': self.get_ai_provider(),
                'openai_configured': bool(self.OPENAI_API_KEY),
                'anthropic_configured': bool(self.ANTHROPIC_API_KEY),
                'gemini_configured': bool(self.GEMINI_API_KEY)
            },
            'feeds': {
                'total': len(self.RSS_FEEDS),
                'enabled': len([f for f in self.RSS_FEEDS.values() if f.enabled]),
                'sources': list(self.get_enabled_feeds().keys())
            },
            'chains': {
                'enabled': self.ENABLED_CHAINS,
                'configured_scanners': [c for c in self.ENABLED_CHAINS if self.has_scanner_api_key(c)]
            },
            'features': {
                'whale_alerts': self.WHALE_ENABLED,
                'news': self.NEWS_ENABLED,
                'analytics': self.ANALYTICS_ENABLED,
                'trading': self.TRADING_ENABLED,
                'hyperliquid': self.HYPERLIQUID_ENABLED
            },
            'thresholds': {
                'min_usd': self.MIN_USD,
                'min_confidence_score': self.MIN_CONFIDENCE_SCORE,
                'posts_per_hour': self.POSTS_PER_HOUR_CAP
            },
            'database': {
                'path': str(self.DB_PATH),
                'backup_enabled': self.DB_BACKUP_ENABLED,
                'max_age_days': self.DB_MAX_AGE_DAYS
            }
        }
    
    @property
    def ai_prompt_template(self) -> str:
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
    
    @property
    def features_enabled(self) -> Dict[str, bool]:
        return {
            'whale_alerts': self.WHALE_ENABLED,
            'news': self.NEWS_ENABLED,
            'analytics': self.ANALYTICS_ENABLED,
            'trading': self.TRADING_ENABLED,
            'hyperliquid': self.HYPERLIQUID_ENABLED
        }


config = Config()


TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_CHANNEL_ID = config.TELEGRAM_CHANNEL_ID
CHAT_ID = config.TELEGRAM_CHANNEL_ID
CHANNEL_ID = config.TELEGRAM_CHANNEL_ID
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID

GEMINI_API_KEY = config.GEMINI_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY
ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY

ETHERSCAN_API_KEY = config.ETHERSCAN_API_KEY
BSCSCAN_API_KEY = config.BSCSCAN_API_KEY
POLYGONSCAN_API_KEY = config.POLYGONSCAN_API_KEY
ARBISCAN_API_KEY = config.ARBISCAN_API_KEY
BASESCAN_API_KEY = config.BASESCAN_API_KEY
SNOWTRACE_API_KEY = config.SNOWTRACE_API_KEY
OPTIMISM_ETHERSCAN_API_KEY = config.OPTIMISM_ETHERSCAN_API_KEY
FTMSCAN_API_KEY = config.FTMSCAN_API_KEY
HELIUS_API_KEY = config.HELIUS_API_KEY
SOLSCAN_API_KEY = config.SOLSCAN_API_KEY

COINGECKO_API_KEY = config.COINGECKO_API_KEY
ALCHEMY_API_KEY = config.ALCHEMY_API_KEY
COINMARKETCAP_API_KEY = config.COINMARKETCAP_API_KEY
CRYPTOPANIC_API_KEY = config.CRYPTOPANIC_API_KEY
NEWSAPI_KEY = config.NEWSAPI_KEY
DEXSCREENER_API_KEY = config.DEXSCREENER_API_KEY
BIRDEYE_API_KEY = config.BIRDEYE_API_KEY

RSS_FEEDS = {name: feed.url for name, feed in config.RSS_FEEDS.items()}
POST_DELAY_SECONDS = config.POST_DELAY_SECONDS
IDLE_DELAY_SECONDS = config.IDLE_DELAY_SECONDS
DB_PATH = str(config.DB_PATH)
NEWS_DB_PATH = str(config.NEWS_DB_PATH)
MIN_IMAGE_WIDTH = config.MIN_IMAGE_WIDTH
MIN_IMAGE_HEIGHT = config.MIN_IMAGE_HEIGHT
COMMON_HEADERS = config.COMMON_HEADERS

NEWS_SOURCES = [
    {
        'name': name,
        'url': feed.url,
        'priority': feed.priority,
        'category': feed.category,
        'language': feed.language,
        'enabled': feed.enabled
    }
    for name, feed in config.RSS_FEEDS.items()
]

FETCH_INTERVAL = config.FETCH_INTERVAL
NEWS_CHECK_INTERVAL = config.NEWS_CHECK_INTERVAL
POSTS_PER_HOUR_CAP = config.POSTS_PER_HOUR_CAP
MIN_CONFIDENCE_SCORE = config.MIN_CONFIDENCE_SCORE

ENABLED_CHAINS = config.ENABLED_CHAINS
MIN_USD = config.MIN_USD

WHALE_ENABLED = config.WHALE_ENABLED
NEWS_ENABLED = config.NEWS_ENABLED
ANALYTICS_ENABLED = config.ANALYTICS_ENABLED
TRADING_ENABLED = config.TRADING_ENABLED
HYPERLIQUID_ENABLED = config.HYPERLIQUID_ENABLED

DATA_DIR = config.DATA_DIR
STATE_FILE = config.STATE_FILE
WALLET_DB_JSON_PATH = config.WALLET_DB_JSON_PATH

LOG_LEVEL = config.LOG_LEVEL
HEALTH_CHECK_ENABLED = config.HEALTH_CHECK_ENABLED

PORT = config.PORT
HTTP_TIMEOUT = config.HTTP_TIMEOUT
RPC_TIMEOUT = config.RPC_TIMEOUT
MAX_MEMORY_MB = config.MAX_MEMORY_MB


__all__ = [
    'config',
    'Config',
    'FeedConfig',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_TOKEN',
    'BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'CHAT_ID',
    'CHANNEL_ID',
    'ADMIN_CHAT_ID',
    'GEMINI_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'ETHERSCAN_API_KEY',
    'BSCSCAN_API_KEY',
    'POLYGONSCAN_API_KEY',
    'ARBISCAN_API_KEY',
    'BASESCAN_API_KEY',
    'SNOWTRACE_API_KEY',
    'OPTIMISM_ETHERSCAN_API_KEY',
    'FTMSCAN_API_KEY',
    'HELIUS_API_KEY',
    'SOLSCAN_API_KEY',
    'COINGECKO_API_KEY',
    'ALCHEMY_API_KEY',
    'COINMARKETCAP_API_KEY',
    'CRYPTOPANIC_API_KEY',
    'NEWSAPI_KEY',
    'DEXSCREENER_API_KEY',
    'BIRDEYE_API_KEY',
    'RSS_FEEDS',
    'NEWS_SOURCES',
    'FETCH_INTERVAL',
    'NEWS_CHECK_INTERVAL',
    'POSTS_PER_HOUR_CAP',
    'MIN_CONFIDENCE_SCORE',
    'POST_DELAY_SECONDS',
    'IDLE_DELAY_SECONDS',
    'DB_PATH',
    'NEWS_DB_PATH',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    'MIN_IMAGE_WIDTH',
    'MIN_IMAGE_HEIGHT',
    'COMMON_HEADERS',
    'ENABLED_CHAINS',
    'MIN_USD',
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'MAX_MEMORY_MB',
]