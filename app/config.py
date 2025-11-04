# app/config.py - УНИФИЦИРОВАННАЯ КОНФИГУРАЦИЯ v5.2

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ChartBackend(str, Enum):
    SPARKLINE = "sparkline"
    MATPLOTLIB = "matplotlib"
    PLOTLY = "plotly"


class WalletDBType(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


@dataclass
class TelegramConfig:
    token: str
    channel_id: str
    admin_chat_id: str
    webhook_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.channel_id:
            raise ValueError("TELEGRAM_CHANNEL_ID is required")
        if not self.admin_chat_id:
            self.admin_chat_id = self.channel_id


@dataclass
class ProductionConfig:
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
    enabled: bool = True
    calls_per_minute: int = 60
    burst_size: int = 10
    solana_requests: int = 50
    solana_window_seconds: int = 60
    solana_retry_on_429: bool = True


@dataclass
class ChainConfig:
    enabled_chains: List[str]
    rpc_urls: Dict[str, str]
    api_keys: Dict[str, str]
    fallback_urls: Dict[str, str] = field(default_factory=dict)


@dataclass
class WhaleConfig:
    min_usd_threshold: float = 50000.0
    min_confidence_score: int = 6
    posts_per_hour_cap: int = 5
    poll_seconds: int = 120
    start_from_minutes_ago: int = 60


@dataclass
class HyperliquidConfig:
    enabled: bool = True
    api_url: str = "https://api.hyperliquid.xyz"
    min_trade_usd: float = 100000.0
    min_liquidation_usd: float = 50000.0
    min_whale_activity_usd: float = 500000.0
    notify_whale_activity: bool = True
    notify_liquidations: bool = True


@dataclass
class TradingConfig:
    enabled: bool = True
    signal_interval_hours: int = 1
    monitored_assets: List[str] = field(default_factory=lambda: [
        "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "MATIC", "LINK"
    ])
    position_update_interval_seconds: int = 60


@dataclass
class NewsConfig:
    enabled: bool = True
    fetch_interval: int = 300
    posts_per_hour_cap: int = 3
    min_confidence_score: int = 6
    db_path: str = "news_database.sqlite"
    sources: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "name": "CoinDesk",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "category": "news"
        },
        {
            "name": "Cointelegraph",
            "url": "https://cointelegraph.com/rss",
            "category": "news"
        },
        {
            "name": "Decrypt",
            "url": "https://decrypt.co/feed",
            "category": "news"
        },
        {
            "name": "The Block",
            "url": "https://www.theblock.co/rss.xml",
            "category": "news"
        },
        {
            "name": "CryptoSlate",
            "url": "https://cryptoslate.com/feed/",
            "category": "news"
        },
        {
            "name": "Bitcoin Magazine",
            "url": "https://bitcoinmagazine.com/.rss/full/",
            "category": "bitcoin"
        },
        {
            "name": "NewsBTC",
            "url": "https://www.newsbtc.com/feed/",
            "category": "news"
        },
        {
            "name": "U.Today",
            "url": "https://u.today/rss",
            "category": "news"
        },
        {
            "name": "BeInCrypto",
            "url": "https://beincrypto.com/feed/",
            "category": "news"
        },
        {
            "name": "CryptoNews",
            "url": "https://cryptonews.com/news/feed/",
            "category": "news"
        }
    ])
    ai_enabled: bool = True
    ai_provider: str = "openai"
    max_article_age_hours: int = 24
    duplicate_check_enabled: bool = True
    image_download_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 5


@dataclass
class SmartDiscoveryConfig:
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
    enabled: bool = True
    interval_days: int = 1
    min_score_to_keep: int = 30
    remove_inactive_days: int = 30
    revalidation_period_days: int = 7
    performance_tracking_enabled: bool = True
    auto_remove_failing: bool = True


@dataclass
class PerformanceConfig:
    tracking_enabled: bool = True
    success_threshold: float = 0.05
    time_window_hours: int = 24
    min_events_for_evaluation: int = 5
    store_detailed_history: bool = True
    calculate_roi: bool = True


@dataclass
class AdaptiveThresholdsConfig:
    enabled: bool = True
    base_min_confidence: int = 40
    market_volatility_adjustment: bool = True
    performance_based_adjustment: bool = True
    adjustment_interval_hours: int = 6
    min_threshold: int = 30
    max_threshold: int = 70


@dataclass
class AnalyticsConfig:
    enabled: bool = True
    sentiment_analysis: bool = True
    risk_scoring: bool = True
    correlation_analysis: bool = True
    anomaly_detection: bool = True
    market_regime_detection: bool = True
    calculate_intervals: int = 300


@dataclass
class DatabaseConfig:
    type: str = "sqlite"
    path: str = "data/crypto_monitor.db"
    news_db_path: str = "news_database.sqlite"
    wallet_db_path: str = "data/wallets/tracked_wallets.json"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7
    connection_pool_size: int = 5


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
        
        print("🔧 [CONFIG] Инициализация конфигурации...")
        
        self.telegram = TelegramConfig(
            token=self._get_required_env('TELEGRAM_BOT_TOKEN', 'TELEGRAM_TOKEN', 'BOT_TOKEN'),
            channel_id=self._get_required_env('TELEGRAM_CHANNEL_ID', 'CHAT_ID', 'CHANNEL_ID'),
            admin_chat_id=os.getenv('ADMIN_CHAT_ID', os.getenv('TELEGRAM_CHANNEL_ID', '')),
            webhook_url=os.getenv('WEBHOOK_URL', '')
        )
        
        self.production = ProductionConfig(
            port=int(os.getenv('PORT', '8000')),
            http_timeout=int(os.getenv('HTTP_TIMEOUT', '30')),
            rpc_timeout=int(os.getenv('RPC_TIMEOUT', '15')),
            webhook_timeout=int(os.getenv('WEBHOOK_TIMEOUT', '10')),
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450')),
            gc_interval_seconds=int(os.getenv('GC_INTERVAL_SECONDS', '300')),
            max_connections=int(os.getenv('MAX_CONNECTIONS', '50')),
            max_keepalive=int(os.getenv('MAX_KEEPALIVE', '10'))
        )
        
        self.rate_limit = RateLimitConfig(
            enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            calls_per_minute=int(os.getenv('RATE_LIMIT_CALLS', '60')),
            burst_size=int(os.getenv('RATE_LIMIT_BURST', '10')),
            solana_requests=int(os.getenv('SOLANA_RATE_LIMIT_REQUESTS', '50')),
            solana_window_seconds=int(os.getenv('SOLANA_RATE_LIMIT_WINDOW', '60')),
            solana_retry_on_429=os.getenv('SOLANA_RETRY_ON_429', '1') == '1'
        )
        
        enabled_chains = os.getenv('ENABLED_CHAINS', 'ethereum,bsc,polygon,arbitrum,base,solana')
        self.chains = ChainConfig(
            enabled_chains=[c.strip() for c in enabled_chains.split(',') if c.strip()],
            rpc_urls={
                'ethereum': os.getenv('ETHEREUM_RPC_URL', 'https://eth.llamarpc.com'),
                'bsc': os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org'),
                'polygon': os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com'),
                'arbitrum': os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc'),
                'base': os.getenv('BASE_RPC_URL', 'https://mainnet.base.org'),
                'solana': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
                'optimism': os.getenv('OPTIMISM_RPC_URL', 'https://mainnet.optimism.io'),
                'avalanche': os.getenv('AVALANCHE_RPC_URL', 'https://api.avax.network/ext/bc/C/rpc'),
            },
            api_keys={
                'etherscan': os.getenv('ETHERSCAN_API_KEY', ''),
                'bscscan': os.getenv('BSCSCAN_API_KEY', ''),
                'polygonscan': os.getenv('POLYGONSCAN_API_KEY', ''),
                'arbiscan': os.getenv('ARBISCAN_API_KEY', ''),
                'basescan': os.getenv('BASESCAN_API_KEY', ''),
                'helius': os.getenv('HELIUS_API_KEY', ''),
                'optimism': os.getenv('OPTIMISM_API_KEY', ''),
                'snowtrace': os.getenv('SNOWTRACE_API_KEY', ''),
            },
            fallback_urls={
                'ethereum': os.getenv('ETHEREUM_FALLBACK_RPC', 'https://rpc.ankr.com/eth'),
                'solana': os.getenv('SOLANA_FALLBACK_RPC', 'https://solana-api.projectserum.com'),
            }
        )
        
        self.whale = WhaleConfig(
            min_usd_threshold=float(os.getenv('WHALE_MIN_VALUE_USD', os.getenv('MIN_USD_THRESHOLD', '50000'))),
            min_confidence_score=int(os.getenv('MIN_CONFIDENCE_SCORE', '6')),
            posts_per_hour_cap=int(os.getenv('POSTS_PER_HOUR_CAP', '5')),
            poll_seconds=int(os.getenv('POLL_SECONDS', '120')),
            start_from_minutes_ago=int(os.getenv('START_FROM_MINUTES_AGO', '60'))
        )
        
        self.hyperliquid = HyperliquidConfig(
            enabled=os.getenv('HYPERLIQUID_ENABLED', 'true').lower() == 'true',
            api_url=os.getenv('HYPERLIQUID_API_URL', 'https://api.hyperliquid.xyz'),
            min_trade_usd=float(os.getenv('HYPERLIQUID_MIN_TRADE_USD', '100000')),
            min_liquidation_usd=float(os.getenv('HYPERLIQUID_MIN_LIQUIDATION_USD', '50000')),
            min_whale_activity_usd=float(os.getenv('HYPERLIQUID_MIN_WHALE_ACTIVITY_USD', '500000')),
            notify_whale_activity=os.getenv('HYPERLIQUID_NOTIFY_WHALE_ACTIVITY', 'true').lower() == 'true',
            notify_liquidations=os.getenv('HYPERLIQUID_NOTIFY_LIQUIDATIONS', 'true').lower() == 'true'
        )
        
        monitored_assets_str = os.getenv('TRADING_MONITORED_ASSETS', 'BTC,ETH,SOL,BNB,XRP,ADA,AVAX,DOT,MATIC,LINK')
        self.trading = TradingConfig(
            enabled=os.getenv('TRADING_ENABLED', 'true').lower() == 'true',
            signal_interval_hours=int(os.getenv('TRADING_SIGNAL_INTERVAL_HOURS', '1')),
            monitored_assets=[a.strip() for a in monitored_assets_str.split(',') if a.strip()],
            position_update_interval_seconds=int(os.getenv('POSITION_UPDATE_INTERVAL_SECONDS', '60'))
        )
        
        self.news = NewsConfig(
            enabled=os.getenv('NEWS_ENABLED', 'true').lower() == 'true',
            fetch_interval=int(os.getenv('FETCH_INTERVAL', os.getenv('NEWS_CHECK_INTERVAL', '300'))),
            posts_per_hour_cap=int(os.getenv('NEWS_POSTS_PER_HOUR', '3')),
            min_confidence_score=int(os.getenv('NEWS_MIN_CONFIDENCE_SCORE', '6')),
            db_path=os.getenv('NEWS_DB_PATH', 'news_database.sqlite'),
            ai_enabled=os.getenv('NEWS_AI_ENABLED', 'true').lower() == 'true',
            ai_provider=os.getenv('NEWS_AI_PROVIDER', 'openai'),
            max_article_age_hours=int(os.getenv('NEWS_MAX_AGE_HOURS', '24')),
            duplicate_check_enabled=os.getenv('NEWS_DUPLICATE_CHECK', 'true').lower() == 'true',
            image_download_enabled=os.getenv('NEWS_IMAGE_DOWNLOAD', 'true').lower() == 'true',
            max_retries=int(os.getenv('NEWS_MAX_RETRIES', '3')),
            retry_delay_seconds=int(os.getenv('NEWS_RETRY_DELAY', '5'))
        )
        
        self.smart_discovery = SmartDiscoveryConfig(
            enabled=os.getenv('SMART_DISCOVERY_ENABLED', 'true').lower() == 'true',
            interval_hours=int(os.getenv('SMART_DISCOVERY_INTERVAL_HOURS', '6')),
            max_new_wallets=int(os.getenv('SMART_DISCOVERY_MAX_NEW_WALLETS', '10')),
            min_success_rate=float(os.getenv('SMART_DISCOVERY_MIN_SUCCESS_RATE', '0.6')),
            min_transactions=int(os.getenv('SMART_DISCOVERY_MIN_TRANSACTIONS', '10')),
            profitability_threshold=float(os.getenv('SMART_DISCOVERY_PROFIT_THRESHOLD', '0.15')),
            consistency_weight=float(os.getenv('SMART_DISCOVERY_CONSISTENCY_WEIGHT', '0.4')),
            profitability_weight=float(os.getenv('SMART_DISCOVERY_PROFIT_WEIGHT', '0.3')),
            volume_weight=float(os.getenv('SMART_DISCOVERY_VOLUME_WEIGHT', '0.3')),
            scan_depth_days=int(os.getenv('SMART_DISCOVERY_SCAN_DEPTH_DAYS', '30'))
        )
        
        self.validation = ValidationConfig(
            enabled=os.getenv('VALIDATION_ENABLED', 'true').lower() == 'true',
            interval_days=int(os.getenv('VALIDATION_INTERVAL_DAYS', '1')),
            min_score_to_keep=int(os.getenv('VALIDATION_MIN_SCORE_TO_KEEP', '30')),
            remove_inactive_days=int(os.getenv('VALIDATION_REMOVE_INACTIVE_DAYS', '30')),
            revalidation_period_days=int(os.getenv('VALIDATION_REVALIDATION_DAYS', '7')),
            performance_tracking_enabled=os.getenv('VALIDATION_PERFORMANCE_TRACKING', 'true').lower() == 'true',
            auto_remove_failing=os.getenv('VALIDATION_AUTO_REMOVE_FAILING', 'true').lower() == 'true'
        )
        
        self.performance = PerformanceConfig(
            tracking_enabled=os.getenv('PERFORMANCE_TRACKING_ENABLED', 'true').lower() == 'true',
            success_threshold=float(os.getenv('PERFORMANCE_SUCCESS_THRESHOLD', '0.05')),
            time_window_hours=int(os.getenv('PERFORMANCE_TIME_WINDOW_HOURS', '24')),
            min_events_for_evaluation=int(os.getenv('PERFORMANCE_MIN_EVENTS', '5')),
            store_detailed_history=os.getenv('PERFORMANCE_STORE_HISTORY', 'true').lower() == 'true',
            calculate_roi=os.getenv('PERFORMANCE_CALCULATE_ROI', 'true').lower() == 'true'
        )
        
        self.adaptive_thresholds = AdaptiveThresholdsConfig(
            enabled=os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', 'true').lower() == 'true',
            base_min_confidence=int(os.getenv('ADAPTIVE_BASE_MIN_CONFIDENCE', '40')),
            market_volatility_adjustment=os.getenv('ADAPTIVE_VOLATILITY_ADJUST', 'true').lower() == 'true',
            performance_based_adjustment=os.getenv('ADAPTIVE_PERFORMANCE_ADJUST', 'true').lower() == 'true',
            adjustment_interval_hours=int(os.getenv('ADAPTIVE_ADJUSTMENT_INTERVAL', '6')),
            min_threshold=int(os.getenv('ADAPTIVE_MIN_THRESHOLD', '30')),
            max_threshold=int(os.getenv('ADAPTIVE_MAX_THRESHOLD', '70'))
        )
        
        self.analytics = AnalyticsConfig(
            enabled=os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true',
            sentiment_analysis=os.getenv('ANALYTICS_SENTIMENT', 'true').lower() == 'true',
            risk_scoring=os.getenv('ANALYTICS_RISK_SCORING', 'true').lower() == 'true',
            correlation_analysis=os.getenv('ANALYTICS_CORRELATION', 'true').lower() == 'true',
            anomaly_detection=os.getenv('ANALYTICS_ANOMALY_DETECTION', 'true').lower() == 'true',
            market_regime_detection=os.getenv('ANALYTICS_MARKET_REGIME', 'true').lower() == 'true',
            calculate_intervals=int(os.getenv('ANALYTICS_CALCULATE_INTERVAL', '300'))
        )
        
        self.database = DatabaseConfig(
            type=os.getenv('DATABASE_TYPE', 'sqlite'),
            path=os.getenv('DATABASE_PATH', 'data/crypto_monitor.db'),
            news_db_path=os.getenv('NEWS_DB_PATH', os.getenv('DB_PATH', 'news_database.sqlite')),
            wallet_db_path=os.getenv('WALLET_DB_JSON_PATH', 'data/wallets/tracked_wallets.json'),
            backup_enabled=os.getenv('DATABASE_BACKUP_ENABLED', 'true').lower() == 'true',
            backup_interval_hours=int(os.getenv('DATABASE_BACKUP_INTERVAL', '24')),
            max_backups=int(os.getenv('DATABASE_MAX_BACKUPS', '7')),
            connection_pool_size=int(os.getenv('DATABASE_POOL_SIZE', '5'))
        )
        
        self.features_enabled = {
            'whale': os.getenv('WHALE_ENABLED', 'true').lower() == 'true',
            'news': os.getenv('NEWS_ENABLED', 'true').lower() == 'true',
            'chains': os.getenv('CHAINS_ENABLED', 'true').lower() == 'true',
            'analytics': os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true',
            'trading': os.getenv('TRADING_ENABLED', 'true').lower() == 'true',
            'hyperliquid': os.getenv('HYPERLIQUID_ENABLED', 'true').lower() == 'true',
            'smart_discovery': os.getenv('SMART_DISCOVERY_ENABLED', 'true').lower() == 'true',
            'validation': os.getenv('VALIDATION_ENABLED', 'true').lower() == 'true',
            'adaptive_thresholds': os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', 'true').lower() == 'true',
            'performance_tracking': os.getenv('PERFORMANCE_TRACKING_ENABLED', 'true').lower() == 'true',
        }
        
        self.data_dir = Path(os.getenv('DATA_DIR', 'data'))
        self.state_file = self.data_dir / os.getenv('STATE_FILE', 'state.json')
        self.wallet_db_path = Path(os.getenv('WALLET_DB_JSON_PATH', 'data/wallets/tracked_wallets.json'))
        
        self._create_directories()
        
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        self.health_check_enabled = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
        self.health_check_max_silence = int(os.getenv('HEALTH_CHECK_MAX_SILENCE', '3600'))
        self.send_startup_notification = os.getenv('SEND_STARTUP_NOTIFICATION', 'true').lower() == 'true'
        self.send_daily_stats = os.getenv('SEND_DAILY_STATS', 'true').lower() == 'true'
        
        self.coingecko_api_key = os.getenv('COINGECKO_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY', '')
        
        self._initialized = True
        self._validate()
        self._print_summary()
    
    def _get_required_env(self, *keys: str) -> str:
        for key in keys:
            value = os.getenv(key)
            if value:
                return value
        raise ValueError(f"Требуется одна из переменных окружения: {', '.join(keys)}")
    
    def _create_directories(self):
        directories = [
            self.data_dir,
            self.data_dir / 'history',
            self.data_dir / 'learning',
            self.data_dir / 'wallets',
            self.data_dir / 'positions',
            self.data_dir / 'performance',
            self.data_dir / 'backups',
            self.data_dir / 'cache',
            Path('logs')
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"⚠️ [CONFIG] Не удалось создать директорию {directory}: {e}")
    
    def _validate(self):
        errors = []
        warnings = []
        
        if self.production.max_memory_mb < 100:
            errors.append("MAX_MEMORY_MB слишком мало (минимум 100MB)")
        
        if self.production.max_memory_mb > 1024:
            warnings.append("MAX_MEMORY_MB больше 512MB - может не подойти для Render Free Tier")
        
        if not self.chains.enabled_chains:
            errors.append("Нет активных блокчейнов (ENABLED_CHAINS)")
        
        if self.whale.min_usd_threshold < 1000:
            warnings.append("WHALE_MIN_VALUE_USD очень низкий - может быть много ложных срабатываний")
        
        if self.whale.posts_per_hour_cap > 10:
            warnings.append("POSTS_PER_HOUR_CAP высокий - может спамить канал")
        
        if self.news.enabled and not self.openai_api_key and not self.anthropic_api_key and not self.gemini_api_key:
            warnings.append("News enabled но нет AI ключей - AI анализ будет отключен")
        
        if self.trading.enabled and len(self.trading.monitored_assets) > 20:
            warnings.append("Слишком много активов для мониторинга - может быть медленно")
        
        for chain in self.chains.enabled_chains:
            if chain not in self.chains.rpc_urls:
                errors.append(f"Нет RPC URL для chain: {chain}")
        
        if errors:
            print("❌ [CONFIG] Критические ошибки конфигурации:")
            for error in errors:
                print(f"   • {error}")
            raise ValueError("Некорректная конфигурация")
        
        if warnings:
            print("⚠️ [CONFIG] Предупреждения:")
            for warning in warnings:
                print(f"   • {warning}")
    
    def _print_summary(self):
        print("\n" + "="*80)
        print("⚙️  КОНФИГУРАЦИЯ ЗАГРУЖЕНА")
        print("="*80)
        
        print(f"\n📱 TELEGRAM:")
        print(f"   Bot: {self.telegram.token[:10]}...{self.telegram.token[-4:]}")
        print(f"   Channel: {self.telegram.channel_id}")
        print(f"   Admin: {self.telegram.admin_chat_id}")
        
        print(f"\n🌐 PRODUCTION:")
        print(f"   Port: {self.production.port}")
        print(f"   Memory Limit: {self.production.max_memory_mb}MB")
        print(f"   HTTP Timeout: {self.production.http_timeout}s")
        print(f"   GC Interval: {self.production.gc_interval_seconds}s")
        
        print(f"\n⛓️  CHAINS ({len(self.chains.enabled_chains)}):")
        print(f"   {', '.join(self.chains.enabled_chains)}")
        
        print(f"\n🐋 WHALE DETECTION:")
        print(f"   Min USD: ${self.whale.min_usd_threshold:,.0f}")
        print(f"   Min Confidence: {self.whale.min_confidence_score}")
        print(f"   Posts/Hour Cap: {self.whale.posts_per_hour_cap}")
        
        if self.news.enabled:
            print(f"\n📰 NEWS BOT:")
            print(f"   Sources: {len(self.news.sources)}")
            print(f"   Fetch Interval: {self.news.fetch_interval}s")
            print(f"   AI Provider: {self.news.ai_provider if self.news.ai_enabled else 'disabled'}")
        
        if self.trading.enabled:
            print(f"\n📈 TRADING:")
            print(f"   Assets: {len(self.trading.monitored_assets)}")
            print(f"   Signal Interval: {self.trading.signal_interval_hours}h")
        
        if self.hyperliquid.enabled:
            print(f"\n💹 HYPERLIQUID:")
            print(f"   Min Trade: ${self.hyperliquid.min_trade_usd:,.0f}")
            print(f"   Min Liquidation: ${self.hyperliquid.min_liquidation_usd:,.0f}")
        
        print(f"\n✨ FEATURES:")
        enabled = [name for name, status in self.features_enabled.items() if status]
        disabled = [name for name, status in self.features_enabled.items() if not status]
        print(f"   Enabled: {', '.join(enabled)}")
        if disabled:
            print(f"   Disabled: {', '.join(disabled)}")
        
        print(f"\n📊 RATE LIMITING:")
        print(f"   General: {self.rate_limit.calls_per_minute}/min")
        print(f"   Solana: {self.rate_limit.solana_requests}/{self.rate_limit.solana_window_seconds}s")
        
        print(f"\n💾 STORAGE:")
        print(f"   Data Dir: {self.data_dir}")
        print(f"   Database: {self.database.type}")
        
        api_keys = []
        if self.openai_api_key:
            api_keys.append("OpenAI")
        if self.anthropic_api_key:
            api_keys.append("Anthropic")
        if self.gemini_api_key:
            api_keys.append("Gemini")
        if self.coingecko_api_key:
            api_keys.append("CoinGecko")
        if api_keys:
            print(f"\n🔑 API KEYS:")
            print(f"   {', '.join(api_keys)}")
        
        print("\n" + "="*80 + "\n")
    
    def is_feature_enabled(self, feature: str) -> bool:
        return self.features_enabled.get(feature, False)
    
    def get_rpc_url(self, chain: str) -> str:
        return self.chains.rpc_urls.get(chain, '')
    
    def get_fallback_rpc_url(self, chain: str) -> Optional[str]:
        return self.chains.fallback_urls.get(chain)
    
    def has_api_key(self, service: str) -> bool:
        if service in self.chains.api_keys:
            return bool(self.chains.api_keys[service])
        
        key_map = {
            'coingecko': self.coingecko_api_key,
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'gemini': self.gemini_api_key,
            'alchemy': self.alchemy_api_key,
        }
        return bool(key_map.get(service, ''))
    
    def get_api_key(self, service: str) -> str:
        if service in self.chains.api_keys:
            return self.chains.api_keys[service]
        
        key_map = {
            'coingecko': self.coingecko_api_key,
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'gemini': self.gemini_api_key,
            'alchemy': self.alchemy_api_key,
        }
        return key_map.get(service, '')
    
    def get_missing_api_keys(self) -> List[str]:
        missing = []
        
        for chain in self.chains.enabled_chains:
            if chain == 'ethereum':
                scanner_service = 'etherscan'
            elif chain == 'bsc':
                scanner_service = 'bscscan'
            elif chain == 'polygon':
                scanner_service = 'polygonscan'
            elif chain == 'arbitrum':
                scanner_service = 'arbiscan'
            elif chain == 'base':
                scanner_service = 'basescan'
            elif chain == 'solana':
                scanner_service = 'helius'
            elif chain == 'optimism':
                scanner_service = 'optimism'
            elif chain == 'avalanche':
                scanner_service = 'snowtrace'
            else:
                continue
            
            if not self.has_api_key(scanner_service):
                missing.append(scanner_service)
        
        return missing
    
    def get_chain_explorer_url(self, chain: str) -> str:
        explorer_urls = {
            'ethereum': 'https://etherscan.io',
            'bsc': 'https://bscscan.com',
            'polygon': 'https://polygonscan.com',
            'arbitrum': 'https://arbiscan.io',
            'base': 'https://basescan.org',
            'solana': 'https://solscan.io',
            'optimism': 'https://optimistic.etherscan.io',
            'avalanche': 'https://snowtrace.io',
        }
        return explorer_urls.get(chain, '')
    
    def get_ai_provider(self) -> Optional[str]:
        if self.news.ai_enabled:
            if self.news.ai_provider == 'openai' and self.openai_api_key:
                return 'openai'
            elif self.news.ai_provider == 'anthropic' and self.anthropic_api_key:
                return 'anthropic'
            elif self.news.ai_provider == 'gemini' and self.gemini_api_key:
                return 'gemini'
            
            if self.openai_api_key:
                return 'openai'
            elif self.anthropic_api_key:
                return 'anthropic'
            elif self.gemini_api_key:
                return 'gemini'
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'telegram': {
                'channel_id': self.telegram.channel_id,
                'has_token': bool(self.telegram.token),
            },
            'production': {
                'port': self.production.port,
                'max_memory_mb': self.production.max_memory_mb,
            },
            'chains': {
                'enabled': self.chains.enabled_chains,
                'count': len(self.chains.enabled_chains),
            },
            'features': self.features_enabled,
            'whale': {
                'min_usd': self.whale.min_usd_threshold,
                'min_confidence': self.whale.min_confidence_score,
            },
            'trading': {
                'enabled': self.trading.enabled,
                'assets_count': len(self.trading.monitored_assets),
            },
            'news': {
                'enabled': self.news.enabled,
                'sources_count': len(self.news.sources),
            }
        }


config = Config()

TELEGRAM_BOT_TOKEN = config.telegram.token
TELEGRAM_TOKEN = config.telegram.token
BOT_TOKEN = config.telegram.token
TELEGRAM_CHANNEL_ID = config.telegram.channel_id
CHAT_ID = config.telegram.channel_id
CHANNEL_ID = config.telegram.channel_id
ADMIN_CHAT_ID = config.telegram.admin_chat_id

PORT = config.production.port
HTTP_TIMEOUT = config.production.http_timeout
RPC_TIMEOUT = config.production.rpc_timeout
WEBHOOK_TIMEOUT = config.production.webhook_timeout
MAX_MEMORY_MB = config.production.max_memory_mb
GC_INTERVAL_SECONDS = config.production.gc_interval_seconds

MIN_USD = config.whale.min_usd_threshold
MIN_USD_THRESHOLD = config.whale.min_usd_threshold
WHALE_MIN_VALUE_USD = config.whale.min_usd_threshold
MIN_CONFIDENCE_SCORE = config.whale.min_confidence_score
POSTS_PER_HOUR_CAP = config.whale.posts_per_hour_cap
POLL_SECONDS = config.whale.poll_seconds
START_FROM_MINUTES_AGO = config.whale.start_from_minutes_ago

ENABLED_CHAINS = config.chains.enabled_chains
CHAINS_ENABLED = config.is_feature_enabled('chains')

WHALE_ENABLED = config.is_feature_enabled('whale')
NEWS_ENABLED = config.is_feature_enabled('news')
ANALYTICS_ENABLED = config.is_feature_enabled('analytics')
TRADING_ENABLED = config.is_feature_enabled('trading')
HYPERLIQUID_ENABLED = config.is_feature_enabled('hyperliquid')
SMART_DISCOVERY_ENABLED = config.is_feature_enabled('smart_discovery')
VALIDATION_ENABLED = config.is_feature_enabled('validation')
ADAPTIVE_THRESHOLDS_ENABLED = config.is_feature_enabled('adaptive_thresholds')
PERFORMANCE_TRACKING_ENABLED = config.is_feature_enabled('performance_tracking')

FETCH_INTERVAL = config.news.fetch_interval
NEWS_CHECK_INTERVAL = config.news.fetch_interval
NEWS_SOURCES = config.news.sources
NEWS_DB_PATH = config.database.news_db_path
DB_PATH = config.database.news_db_path

DATA_DIR = str(config.data_dir)
STATE_FILE = str(config.state_file)
WALLET_DB_JSON_PATH = str(config.wallet_db_path)

LOG_LEVEL = config.log_level

HEALTH_CHECK_ENABLED = config.health_check_enabled
HEALTH_CHECK_INTERVAL = config.health_check_interval
HEALTH_CHECK_MAX_SILENCE = config.health_check_max_silence
SEND_STARTUP_NOTIFICATION = config.send_startup_notification
SEND_DAILY_STATS = config.send_daily_stats

OPENAI_API_KEY = config.openai_api_key
ANTHROPIC_API_KEY = config.anthropic_api_key
GEMINI_API_KEY = config.gemini_api_key
COINGECKO_API_KEY = config.coingecko_api_key
ALCHEMY_API_KEY = config.alchemy_api_key

ETHERSCAN_API_KEY = config.chains.api_keys.get('etherscan', '')
BSCSCAN_API_KEY = config.chains.api_keys.get('bscscan', '')
POLYGONSCAN_API_KEY = config.chains.api_keys.get('polygonscan', '')
ARBISCAN_API_KEY = config.chains.api_keys.get('arbiscan', '')
BASESCAN_API_KEY = config.chains.api_keys.get('basescan', '')
HELIUS_API_KEY = config.chains.api_keys.get('helius', '')

ETHEREUM_RPC_URL = config.chains.rpc_urls.get('ethereum', '')
BSC_RPC_URL = config.chains.rpc_urls.get('bsc', '')
POLYGON_RPC_URL = config.chains.rpc_urls.get('polygon', '')
ARBITRUM_RPC_URL = config.chains.rpc_urls.get('arbitrum', '')
BASE_RPC_URL = config.chains.rpc_urls.get('base', '')
SOLANA_RPC_URL = config.chains.rpc_urls.get('solana', '')

SOLANA_RATE_LIMIT_REQUESTS = config.rate_limit.solana_requests
SOLANA_RATE_LIMIT_WINDOW = config.rate_limit.solana_window_seconds
SOLANA_RETRY_ON_429 = config.rate_limit.solana_retry_on_429

HYPERLIQUID_API_URL = config.hyperliquid.api_url
HYPERLIQUID_MIN_TRADE_USD = config.hyperliquid.min_trade_usd
HYPERLIQUID_MIN_LIQUIDATION_USD = config.hyperliquid.min_liquidation_usd
HYPERLIQUID_MIN_WHALE_ACTIVITY_USD = config.hyperliquid.min_whale_activity_usd

TRADING_SIGNAL_INTERVAL_HOURS = config.trading.signal_interval_hours
TRADING_MONITORED_ASSETS = config.trading.monitored_assets

SMART_DISCOVERY_INTERVAL_HOURS = config.smart_discovery.interval_hours
SMART_DISCOVERY_MAX_NEW_WALLETS = config.smart_discovery.max_new_wallets

VALIDATION_INTERVAL_DAYS = config.validation.interval_days
VALIDATION_MIN_SCORE_TO_KEEP = config.validation.min_score_to_keep

PERFORMANCE_SUCCESS_THRESHOLD = config.performance.success_threshold

ADAPTIVE_BASE_MIN_CONFIDENCE = config.adaptive_thresholds.base_min_confidence


__all__ = [
    'config',
    'Config',
    'TelegramConfig',
    'ProductionConfig',
    'RateLimitConfig',
    'ChainConfig',
    'WhaleConfig',
    'HyperliquidConfig',
    'TradingConfig',
    'NewsConfig',
    'SmartDiscoveryConfig',
    'ValidationConfig',
    'PerformanceConfig',
    'AdaptiveThresholdsConfig',
    'AnalyticsConfig',
    'DatabaseConfig',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_TOKEN',
    'BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'CHAT_ID',
    'CHANNEL_ID',
    'ADMIN_CHAT_ID',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'MAX_MEMORY_MB',
    'MIN_USD',
    'MIN_CONFIDENCE_SCORE',
    'POSTS_PER_HOUR_CAP',
    'ENABLED_CHAINS',
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
    'FETCH_INTERVAL',
    'NEWS_SOURCES',
    'DATA_DIR',
    'STATE_FILE',
    'WALLET_DB_JSON_PATH',
    'LOG_LEVEL',
    'HEALTH_CHECK_ENABLED',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
]