# app/config/models.py
"""
Configuration dataclass models
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    token: str
    channel_id: str
    admin_chat_id: str
    webhook_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.token:
            raise ValueError('TELEGRAM_BOT_TOKEN is required')
        if not self.channel_id:
            raise ValueError('TELEGRAM_CHANNEL_ID is required')
        if not self.admin_chat_id:
            self.admin_chat_id = self.channel_id


@dataclass
class ProductionConfig:
    """Production environment configuration"""
    port: int = 8000
    http_timeout: int = 30
    rpc_timeout: int = 15
    webhook_timeout: int = 10
    max_memory_mb: int = 450
    gc_interval_seconds: int = 300
    max_connections: int = 50
    max_keepalive: int = 10


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enabled: bool = True
    calls_per_minute: int = 60
    burst_size: int = 10
    solana_requests: int = 50
    solana_window_seconds: int = 60
    solana_retry_on_429: bool = True


@dataclass
class ChainConfig:
    """Blockchain configuration"""
    enabled_chains: List[str]
    rpc_urls: Dict[str, str]
    api_keys: Dict[str, str]
    fallback_urls: Dict[str, str] = field(default_factory=dict)


@dataclass
class WhaleConfig:
    """Whale detection configuration"""
    min_usd_threshold: float = 10000.0
    min_confidence_score: int = 6
    posts_per_hour_cap: int = 5
    poll_seconds: int = 120
    start_from_minutes_ago: int = 60


@dataclass
class HyperliquidConfig:
    """Hyperliquid exchange configuration"""
    enabled: bool = True
    api_url: str = 'https://api.hyperliquid.xyz'
    min_trade_usd: float = 100000.0
    min_liquidation_usd: float = 50000.0
    min_whale_activity_usd: float = 500000.0
    notify_whale_activity: bool = True
    notify_liquidations: bool = True


@dataclass
class TradingConfig:
    """Trading system configuration"""
    enabled: bool = True
    signal_interval_hours: int = 1
    monitored_assets: List[str] = field(default_factory=lambda: [
        'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK',
        'UNI', 'ATOM', 'LTC', 'BCH', 'NEAR', 'ICP', 'APT', 'ARB', 'OP', 'FTM',
        'ALGO', 'VET', 'FIL', 'HBAR', 'ETC', 'AAVE', 'GRT', 'SAND', 'MANA', 'AXS',
        'XLM', 'XMR', 'THETA', 'EOS', 'MKR', 'STX', 'RUNE', 'INJ', 'LDO', 'QNT',
        'CRV', 'COMP', 'SNX', 'YFI', 'SUSHI', 'BAL', 'ZRX', '1INCH', 'ENJ', 'CHZ'
    ])
    position_update_interval_seconds: int = 60
    auto_update_assets: bool = True
    asset_update_interval_hours: int = 24


@dataclass
class NewsConfig:
    """News bot configuration"""
    enabled: bool = True
    fetch_interval: int = 300
    posts_per_hour_cap: int = 3
    min_confidence_score: int = 6
    db_path: str = 'news_database.sqlite'
    sources: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            'name': 'CoinDesk',
            'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'category': 'news'
        },
        {
            'name': 'Cointelegraph',
            'url': 'https://cointelegraph.com/rss',
            'category': 'news'
        },
        {
            'name': 'Decrypt',
            'url': 'https://decrypt.co/feed',
            'category': 'news'
        },
        {
            'name': 'The Block',
            'url': 'https://www.theblock.co/rss.xml',
            'category': 'news'
        },
        {
            'name': 'Crypto Briefing',
            'url': 'https://cryptobriefing.com/feed/',
            'category': 'news'
        },
        {
            'name': 'Bitcoin Magazine',
            'url': 'https://bitcoinmagazine.com/.rss/full/',
            'category': 'bitcoin'
        },
        {
            'name': 'NewsBTC',
            'url': 'https://www.newsbtc.com/feed/',
            'category': 'news'
        },
        {
            'name': 'U.Today',
            'url': 'https://u.today/rss',
            'category': 'news'
        },
        {
            'name': 'BeInCrypto',
            'url': 'https://beincrypto.com/feed/',
            'category': 'news'
        },
        {
            'name': 'CryptoNews',
            'url': 'https://cryptonews.com/news/feed/',
            'category': 'news'
        },
        {
            'name': 'CryptoPotato',
            'url': 'https://cryptopotato.com/feed/',
            'category': 'news'
        },
        {
            'name': 'Blockworks',
            'url': 'https://blockworks.co/feed',
            'category': 'news'
        },
        {
            'name': 'CoinGape',
            'url': 'https://coingape.com/feed/',
            'category': 'news'
        },
        {
            'name': 'AMBCrypto',
            'url': 'https://ambcrypto.com/feed/',
            'category': 'news'
        },
        {
            'name': 'Crypto Daily',
            'url': 'https://cryptodaily.co.uk/feed',
            'category': 'news'
        }
    ])
    ai_enabled: bool = True
    ai_provider: str = 'openai'
    max_article_age_hours: int = 24
    duplicate_check_enabled: bool = True
    image_download_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 5


@dataclass
class SmartDiscoveryConfig:
    """Smart wallet discovery configuration"""
    enabled: bool = True
    interval_hours: int = 6
    max_new_wallets: int = 10
    min_success_rate: float = 0.6
    min_transactions: int = 10
    profitability_threshold: float = 0.15
    consistency_weight: float = 0.4
    profitability_weight: float = 0.3
    volume_weight: float = 0.3
    scan_depth_days: int = 30


@dataclass
class ValidationConfig:
    """Wallet validation configuration"""
    enabled: bool = True
    interval_days: int = 1
    min_score_to_keep: int = 30
    remove_inactive_days: int = 30
    revalidation_period_days: int = 7
    performance_tracking_enabled: bool = True
    auto_remove_failing: bool = True


@dataclass
class PerformanceConfig:
    """Performance tracking configuration"""
    tracking_enabled: bool = True
    success_threshold: float = 0.05
    time_window_hours: int = 24
    min_events_for_evaluation: int = 5
    store_detailed_history: bool = True
    calculate_roi: bool = True


@dataclass
class AdaptiveThresholdsConfig:
    """Adaptive thresholds configuration"""
    enabled: bool = True
    base_min_confidence: int = 40
    market_volatility_adjustment: bool = True
    performance_based_adjustment: bool = True
    adjustment_interval_hours: int = 6
    min_threshold: int = 30
    max_threshold: int = 70


@dataclass
class AnalyticsConfig:
    """Analytics configuration"""
    enabled: bool = True
    sentiment_analysis: bool = True
    risk_scoring: bool = True
    correlation_analysis: bool = True
    anomaly_detection: bool = True
    market_regime_detection: bool = True
    calculate_intervals: int = 300


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = 'sqlite'
    path: str = 'data/crypto_monitor.db'
    news_db_path: str = 'news_database.sqlite'
    wallet_db_path: str = 'data/wallets/tracked_wallets.json'
    watchlist_file: str = 'data/wallets/watchlist.json'
    history_file: str = 'data/history/events.json'
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7
    connection_pool_size: int = 5


@dataclass
class MetricsConfig:
    """Metrics and monitoring configuration"""
    enabled: bool = False
    port: int = 9090
    sentry_dsn: Optional[str] = None


@dataclass
class DiscoveryConfig:
    """Token discovery configuration"""
    enabled: bool = True
    interval_hours: int = 6
    top_n_per_chain: int = 50
    min_token_age_days: int = 30
    min_volume_usd: float = 100000.0
    min_market_cap_usd: float = 1000000.0
    max_price_change_percent: float = 200.0
    blacklist: Set[str] = field(default_factory=lambda: {
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD',
        'WBTC', 'WETH', 'WBNB', 'WMATIC', 'WAVAX',
        'STETH', 'RETH', 'CBETH',
        'SPAM', 'SCAM', 'TEST', 'FAKE'
    })
    watchlist_file: str = 'data/wallets/watchlist.json'