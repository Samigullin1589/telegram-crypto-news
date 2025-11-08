# app/config/models.py
"""
Configuration Data Models v2.0
Типизированные модели конфигурации с валидацией
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class LogLevel(str, Enum):
    """Уровни логирования"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


@dataclass
class TelegramConfig:
    """
    Конфигурация Telegram бота
    Обязательные параметры для работы с Telegram API
    """
    token: str
    channel_id: str
    admin_chat_id: str
    webhook_url: Optional[str] = None
    
    def __post_init__(self):
        """Валидация обязательных параметров"""
        if not self.token:
            raise ValueError('TELEGRAM_BOT_TOKEN обязателен для работы бота')
        if not self.channel_id:
            raise ValueError('TELEGRAM_CHANNEL_ID обязателен для публикаций')
        if not self.admin_chat_id:
            self.admin_chat_id = self.channel_id


@dataclass
class ProductionConfig:
    """
    Конфигурация production окружения
    Параметры для оптимальной работы на Render
    """
    port: int = 8000
    http_timeout: int = 30
    rpc_timeout: int = 15
    webhook_timeout: int = 10
    max_memory_mb: int = 450
    gc_interval_seconds: int = 300
    max_connections: int = 50
    max_keepalive: int = 10
    
    def __post_init__(self):
        """Валидация production параметров"""
        if self.port < 1024 or self.port > 65535:
            raise ValueError(f'Некорректный порт: {self.port}')
        if self.max_memory_mb < 256:
            raise ValueError(f'Недостаточно памяти: {self.max_memory_mb}MB')


@dataclass
class RateLimitConfig:
    """
    Конфигурация rate limiting
    Управление частотой запросов к внешним API
    """
    enabled: bool = True
    calls_per_minute: int = 60
    burst_size: int = 10
    solana_requests: int = 50
    solana_window_seconds: int = 60
    solana_retry_on_429: bool = True
    
    def __post_init__(self):
        """Валидация rate limit параметров"""
        if self.enabled:
            if self.calls_per_minute < 1:
                raise ValueError('calls_per_minute должен быть > 0')
            if self.burst_size < 1:
                raise ValueError('burst_size должен быть > 0')


@dataclass
class ChainConfig:
    """
    Конфигурация блокчейнов
    RPC endpoints и API ключи для каждой сети
    """
    enabled_chains: List[str]
    rpc_urls: Dict[str, str]
    api_keys: Dict[str, str]
    fallback_urls: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация конфигурации chains"""
        if not self.enabled_chains:
            raise ValueError('Должен быть включён хотя бы один блокчейн')
        
        for chain in self.enabled_chains:
            if chain not in self.rpc_urls:
                raise ValueError(f'Отсутствует RPC URL для {chain}')


@dataclass
class WhaleConfig:
    """
    Конфигурация whale мониторинга
    Пороги и параметры обнаружения крупных транзакций
    """
    min_usd_threshold: float = 10000.0
    chain_thresholds: Dict[str, float] = field(default_factory=dict)
    min_confidence_score: int = 6
    posts_per_hour_cap: int = 5
    poll_seconds: int = 120
    start_from_minutes_ago: int = 60
    
    def __post_init__(self):
        """Валидация whale параметров"""
        if self.min_usd_threshold < 100:
            raise ValueError(f'min_usd_threshold слишком мал: ${self.min_usd_threshold}')
        
        if self.min_confidence_score < 0 or self.min_confidence_score > 10:
            raise ValueError(f'min_confidence_score должен быть 0-10: {self.min_confidence_score}')
        
        if self.posts_per_hour_cap < 1:
            raise ValueError(f'posts_per_hour_cap должен быть > 0: {self.posts_per_hour_cap}')
        
        # Валидация chain-specific порогов
        for chain, threshold in self.chain_thresholds.items():
            if threshold < 100:
                raise ValueError(f'Порог для {chain} слишком мал: ${threshold}')
    
    def get_threshold_for_chain(self, chain: str) -> float:
        """
        Получение порога для конкретного блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Порог в USD
        """
        return self.chain_thresholds.get(chain, self.min_usd_threshold)


@dataclass
class HyperliquidConfig:
    """
    Конфигурация Hyperliquid биржи
    Параметры мониторинга perpetual futures
    """
    enabled: bool = True
    api_url: str = 'https://api.hyperliquid.xyz'
    min_trade_usd: float = 100000.0
    min_liquidation_usd: float = 50000.0
    min_whale_activity_usd: float = 500000.0
    notify_whale_activity: bool = True
    notify_liquidations: bool = True
    
    def __post_init__(self):
        """Валидация Hyperliquid параметров"""
        if self.enabled:
            if not self.api_url:
                raise ValueError('api_url обязателен когда Hyperliquid включён')
            if self.min_trade_usd < 1000:
                raise ValueError(f'min_trade_usd слишком мал: ${self.min_trade_usd}')


@dataclass
class TradingConfig:
    """
    Конфигурация торговой системы
    Мониторинг позиций и генерация сигналов
    """
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
    
    def __post_init__(self):
        """Валидация trading параметров"""
        if self.enabled:
            if not self.monitored_assets:
                raise ValueError('monitored_assets не может быть пустым')
            if self.signal_interval_hours < 1:
                raise ValueError('signal_interval_hours должен быть >= 1')


@dataclass
class NewsConfig:
    """
    Конфигурация новостного бота
    RSS источники и AI обработка
    """
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
    
    def __post_init__(self):
        """Валидация news параметров"""
        if self.enabled:
            if self.fetch_interval < 60:
                raise ValueError('fetch_interval должен быть >= 60 секунд')
            if not self.sources:
                raise ValueError('sources не может быть пустым')


@dataclass
class SmartDiscoveryConfig:
    """
    Конфигурация умного обнаружения кошельков
    Поиск успешных трейдеров по on-chain активности
    """
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
    
    def __post_init__(self):
        """Валидация smart discovery параметров"""
        if self.enabled:
            total_weight = (
                self.consistency_weight + 
                self.profitability_weight + 
                self.volume_weight
            )
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f'Сумма весов должна быть 1.0, получено: {total_weight}')


@dataclass
class ValidationConfig:
    """
    Конфигурация валидации кошельков
    Периодическая проверка производительности
    """
    enabled: bool = True
    interval_days: int = 1
    min_score_to_keep: int = 30
    remove_inactive_days: int = 30
    revalidation_period_days: int = 7
    performance_tracking_enabled: bool = True
    auto_remove_failing: bool = True
    
    def __post_init__(self):
        """Валидация validation параметров"""
        if self.enabled:
            if self.min_score_to_keep < 0 or self.min_score_to_keep > 100:
                raise ValueError('min_score_to_keep должен быть 0-100')


@dataclass
class PerformanceConfig:
    """
    Конфигурация отслеживания производительности
    Метрики успешности предсказаний
    """
    tracking_enabled: bool = True
    success_threshold: float = 0.05
    time_window_hours: int = 24
    min_events_for_evaluation: int = 5
    store_detailed_history: bool = True
    calculate_roi: bool = True
    
    def __post_init__(self):
        """Валидация performance параметров"""
        if self.tracking_enabled:
            if self.success_threshold < 0 or self.success_threshold > 1:
                raise ValueError('success_threshold должен быть 0-1')


@dataclass
class AdaptiveThresholdsConfig:
    """
    Конфигурация адаптивных порогов
    Автоматическая подстройка под рынок
    """
    enabled: bool = True
    base_min_confidence: int = 40
    market_volatility_adjustment: bool = True
    performance_based_adjustment: bool = True
    adjustment_interval_hours: int = 6
    min_threshold: int = 30
    max_threshold: int = 70
    
    def __post_init__(self):
        """Валидация adaptive thresholds параметров"""
        if self.enabled:
            if self.min_threshold >= self.max_threshold:
                raise ValueError('min_threshold должен быть < max_threshold')
            if self.base_min_confidence < self.min_threshold:
                raise ValueError('base_min_confidence < min_threshold')
            if self.base_min_confidence > self.max_threshold:
                raise ValueError('base_min_confidence > max_threshold')


@dataclass
class AnalyticsConfig:
    """
    Конфигурация аналитики
    Дополнительные расчёты и метрики
    """
    enabled: bool = True
    sentiment_analysis: bool = True
    risk_scoring: bool = True
    correlation_analysis: bool = True
    anomaly_detection: bool = True
    market_regime_detection: bool = True
    calculate_intervals: int = 300
    
    def __post_init__(self):
        """Валидация analytics параметров"""
        if self.enabled:
            if self.calculate_intervals < 60:
                raise ValueError('calculate_intervals должен быть >= 60')


@dataclass
class DatabaseConfig:
    """
    Конфигурация базы данных
    Пути к файлам и параметры хранения
    """
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
    
    def __post_init__(self):
        """Валидация database параметров"""
        valid_types = ['sqlite', 'postgresql', 'mysql']
        if self.type not in valid_types:
            raise ValueError(f'Некорректный тип БД: {self.type}. Допустимые: {valid_types}')
        
        if self.connection_pool_size < 1:
            raise ValueError('connection_pool_size должен быть >= 1')


@dataclass
class MetricsConfig:
    """
    Конфигурация метрик и мониторинга
    Prometheus и Sentry интеграции
    """
    enabled: bool = False
    port: int = 9090
    sentry_dsn: Optional[str] = None
    
    def __post_init__(self):
        """Валидация metrics параметров"""
        if self.enabled:
            if self.port < 1024 or self.port > 65535:
                raise ValueError(f'Некорректный порт метрик: {self.port}')


@dataclass
class DiscoveryConfig:
    """
    Конфигурация token discovery
    Автоматическое обнаружение новых токенов
    """
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
    
    def __post_init__(self):
        """Валидация discovery параметров"""
        if self.enabled:
            if self.min_volume_usd < 1000:
                raise ValueError('min_volume_usd должен быть >= $1,000')
            if self.min_market_cap_usd < 10000:
                raise ValueError('min_market_cap_usd должен быть >= $10,000')
            if self.top_n_per_chain < 1:
                raise ValueError('top_n_per_chain должен быть >= 1')
    
    def is_blacklisted(self, token_symbol: str) -> bool:
        """
        Проверка токена в blacklist
        
        Args:
            token_symbol: Символ токена
            
        Returns:
            True если токен в blacklist
        """
        return token_symbol.upper() in self.blacklist