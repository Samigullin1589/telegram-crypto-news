# app/config.py - УНИФИЦИРОВАННАЯ КОНФИГУРАЦИЯ v5.0
"""
UNIFIED CONFIGURATION MODULE - Единый источник истины

ИСПРАВЛЕНО (04.11.2025):
✅ Объединены bot/config.py и app/settings.py
✅ Валидация всех параметров
✅ Type hints для всех настроек
✅ Singleton pattern
✅ Умные дефолты
✅ Comprehensive documentation
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()


# ============================================================================
# ENUMS
# ============================================================================

class LogLevel(str, Enum):
    """Уровни логирования"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ChartBackend(str, Enum):
    """Бэкенды для графиков"""
    SPARKLINE = "sparkline"
    MATPLOTLIB = "matplotlib"
    PLOTLY = "plotly"


class WalletDBType(str, Enum):
    """Типы хранилища для wallet database"""
    JSON = "json"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class TelegramConfig:
    """Telegram Bot Configuration"""
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
    """Production Environment Settings"""
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
    """Rate Limiting Configuration"""
    enabled: bool = True
    calls_per_minute: int = 60
    burst_size: int = 10
    
    # Solana specific (более строгие лимиты)
    solana_requests: int = 50
    solana_window_seconds: int = 60
    solana_retry_on_429: bool = True


@dataclass
class ChainConfig:
    """Blockchain Configuration"""
    enabled_chains: List[str]
    rpc_urls: Dict[str, str]
    api_keys: Dict[str, str]
    fallback_urls: Dict[str, str] = field(default_factory=dict)


@dataclass
class WhaleConfig:
    """Whale Detection Configuration"""
    min_usd_threshold: float = 50000.0
    min_confidence_score: int = 6
    posts_per_hour_cap: int = 5
    poll_seconds: int = 120
    start_from_minutes_ago: int = 60


@dataclass
class HyperliquidConfig:
    """Hyperliquid Exchange Configuration"""
    enabled: bool = True
    api_url: str = "https://api.hyperliquid.xyz"
    min_trade_usd: float = 100000.0
    min_liquidation_usd: float = 50000.0
    min_whale_activity_usd: float = 500000.0
    notify_whale_activity: bool = True
    notify_liquidations: bool = True


@dataclass
class TradingConfig:
    """Trading System Configuration"""
    enabled: bool = True
    signal_interval_hours: int = 1
    monitored_assets: List[str] = field(default_factory=lambda: [
        "BTC", "ETH", "SOL", "BNB", "XRP"
    ])
    position_update_interval_seconds: int = 60


# ============================================================================
# MAIN CONFIG CLASS
# ============================================================================

class Config:
    """
    Unified Configuration - Singleton
    
    Единая точка доступа ко всем настройкам приложения.
    Загружается один раз при импорте модуля.
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
        
        print("🔧 [CONFIG] Инициализация конфигурации...")
        
        # === TELEGRAM ===
        self.telegram = TelegramConfig(
            token=self._get_required_env('TELEGRAM_BOT_TOKEN', 'TELEGRAM_TOKEN'),
            channel_id=self._get_required_env('TELEGRAM_CHANNEL_ID', 'CHAT_ID'),
            admin_chat_id=os.getenv('ADMIN_CHAT_ID', ''),
            webhook_url=os.getenv('WEBHOOK_URL', '')
        )
        
        # === PRODUCTION ===
        self.production = ProductionConfig(
            port=int(os.getenv('PORT', '8000')),
            http_timeout=int(os.getenv('HTTP_TIMEOUT', '30')),
            rpc_timeout=int(os.getenv('RPC_TIMEOUT', '15')),
            webhook_timeout=int(os.getenv('WEBHOOK_TIMEOUT', '10')),
            max_memory_mb=int(os.getenv('MAX_MEMORY_MB', '450')),
            gc_interval_seconds=int(os.getenv('GC_INTERVAL_SECONDS', '300'))
        )
        
        # === RATE LIMITING ===
        self.rate_limit = RateLimitConfig(
            enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            calls_per_minute=int(os.getenv('RATE_LIMIT_CALLS', '60')),
            solana_requests=int(os.getenv('SOLANA_RATE_LIMIT_REQUESTS', '50')),
            solana_window_seconds=int(os.getenv('SOLANA_RATE_LIMIT_WINDOW', '60')),
            solana_retry_on_429=os.getenv('SOLANA_RETRY_ON_429', '1') == '1'
        )
        
        # === CHAINS ===
        enabled_chains = os.getenv('ENABLED_CHAINS', 'ethereum,bsc,polygon,arbitrum,base,solana')
        self.chains = ChainConfig(
            enabled_chains=[c.strip() for c in enabled_chains.split(',')],
            rpc_urls={
                'ethereum': os.getenv('ETHEREUM_RPC_URL', 'https://eth.llamarpc.com'),
                'bsc': os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org'),
                'polygon': os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com'),
                'arbitrum': os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc'),
                'base': os.getenv('BASE_RPC_URL', 'https://mainnet.base.org'),
                'solana': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
            },
            api_keys={
                'etherscan': os.getenv('ETHERSCAN_API_KEY', ''),
                'bscscan': os.getenv('BSCSCAN_API_KEY', ''),
                'polygonscan': os.getenv('POLYGONSCAN_API_KEY', ''),
                'arbiscan': os.getenv('ARBISCAN_API_KEY', ''),
                'basescan': os.getenv('BASESCAN_API_KEY', ''),
                'helius': os.getenv('HELIUS_API_KEY', ''),
            }
        )
        
        # === WHALE DETECTION ===
        self.whale = WhaleConfig(
            min_usd_threshold=float(os.getenv('WHALE_MIN_VALUE_USD', '50000')),
            min_confidence_score=int(os.getenv('MIN_CONFIDENCE_SCORE', '6')),
            posts_per_hour_cap=int(os.getenv('POSTS_PER_HOUR_CAP', '5')),
            poll_seconds=int(os.getenv('POLL_SECONDS', '120')),
            start_from_minutes_ago=int(os.getenv('START_FROM_MINUTES_AGO', '60'))
        )
        
        # === HYPERLIQUID ===
        self.hyperliquid = HyperliquidConfig(
            enabled=os.getenv('HYPERLIQUID_ENABLED', 'true').lower() == 'true',
            api_url=os.getenv('HYPERLIQUID_API_URL', 'https://api.hyperliquid.xyz'),
            min_trade_usd=float(os.getenv('HYPERLIQUID_MIN_TRADE_USD', '100000')),
            min_liquidation_usd=float(os.getenv('HYPERLIQUID_MIN_LIQUIDATION_USD', '50000')),
            min_whale_activity_usd=float(os.getenv('HYPERLIQUID_MIN_WHALE_ACTIVITY_USD', '500000')),
            notify_whale_activity=os.getenv('HYPERLIQUID_NOTIFY_WHALE_ACTIVITY', 'true').lower() == 'true',
            notify_liquidations=os.getenv('HYPERLIQUID_NOTIFY_LIQUIDATIONS', 'true').lower() == 'true'
        )
        
        # === TRADING ===
        monitored_assets_str = os.getenv('TRADING_MONITORED_ASSETS', 'BTC,ETH,SOL,BNB,XRP')
        self.trading = TradingConfig(
            enabled=os.getenv('TRADING_ENABLED', 'true').lower() == 'true',
            signal_interval_hours=int(os.getenv('TRADING_SIGNAL_INTERVAL_HOURS', '1')),
            monitored_assets=[a.strip() for a in monitored_assets_str.split(',')],
            position_update_interval_seconds=int(os.getenv('POSITION_UPDATE_INTERVAL_SECONDS', '60'))
        )
        
        # === FEATURES ===
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
        
        # === PATHS ===
        self.data_dir = Path(os.getenv('DATA_DIR', 'data'))
        self.state_file = self.data_dir / 'state.json'
        self.wallet_db_path = self.data_dir / 'wallets' / 'tracked_wallets.json'
        
        # Создаём директории
        self._create_directories()
        
        # === LOGGING ===
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # === HEALTH CHECKS ===
        self.health_check_enabled = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
        
        # === API KEYS (опциональные) ===
        self.coingecko_api_key = os.getenv('COINGECKO_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        
        self._initialized = True
        self._validate()
        self._print_summary()
    
    def _get_required_env(self, *keys: str) -> str:
        """
        Получить обязательную переменную окружения
        Пробует несколько вариантов имён
        """
        for key in keys:
            value = os.getenv(key)
            if value:
                return value
        raise ValueError(f"Требуется одна из переменных окружения: {', '.join(keys)}")
    
    def _create_directories(self):
        """Создать необходимые директории"""
        directories = [
            self.data_dir,
            self.data_dir / 'history',
            self.data_dir / 'learning',
            self.data_dir / 'wallets',
            self.data_dir / 'positions',
            self.data_dir / 'performance',
            Path('logs')
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _validate(self):
        """Валидация конфигурации"""
        errors = []
        
        # Проверяем критичные настройки
        if self.production.max_memory_mb < 100:
            errors.append("MAX_MEMORY_MB слишком мало (минимум 100MB)")
        
        if self.production.max_memory_mb > 1024:
            errors.append("MAX_MEMORY_MB слишком много для Render Free Tier (максимум 512MB)")
        
        if not self.chains.enabled_chains:
            errors.append("Нет активных блокчейнов (ENABLED_CHAINS)")
        
        if self.whale.min_usd_threshold < 1000:
            errors.append("WHALE_MIN_VALUE_USD слишком низкий (минимум 1000)")
        
        if errors:
            print("❌ [CONFIG] Ошибки валидации:")
            for error in errors:
                print(f"   • {error}")
            raise ValueError("Некорректная конфигурация")
    
    def _print_summary(self):
        """Вывести краткую сводку конфигурации"""
        print("\n" + "="*80)
        print("⚙️  КОНФИГУРАЦИЯ ЗАГРУЖЕНА")
        print("="*80)
        
        print(f"\n📱 TELEGRAM:")
        print(f"   Bot: {self.telegram.token[:10]}...{self.telegram.token[-4:]}")
        print(f"   Channel: {self.telegram.channel_id}")
        
        print(f"\n🌐 PRODUCTION:")
        print(f"   Port: {self.production.port}")
        print(f"   Memory Limit: {self.production.max_memory_mb}MB")
        print(f"   HTTP Timeout: {self.production.http_timeout}s")
        
        print(f"\n⛓️  CHAINS:")
        print(f"   Enabled: {', '.join(self.chains.enabled_chains)}")
        
        print(f"\n🐋 WHALE:")
        print(f"   Min USD: ${self.whale.min_usd_threshold:,.0f}")
        print(f"   Min Confidence: {self.whale.min_confidence_score}")
        
        print(f"\n✨ FEATURES:")
        enabled = [name for name, status in self.features_enabled.items() if status]
        print(f"   {', '.join(enabled)}")
        
        print(f"\n📊 RATE LIMITING:")
        print(f"   General: {self.rate_limit.calls_per_minute}/min")
        print(f"   Solana: {self.rate_limit.solana_requests}/{self.rate_limit.solana_window_seconds}s")
        
        print("\n" + "="*80 + "\n")
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Проверка активности фичи"""
        return self.features_enabled.get(feature, False)
    
    def get_rpc_url(self, chain: str) -> str:
        """Получить RPC URL для блокчейна"""
        return self.chains.rpc_urls.get(chain, '')
    
    def has_api_key(self, service: str) -> bool:
        """Проверка наличия API ключа"""
        if service in self.chains.api_keys:
            return bool(self.chains.api_keys[service])
        
        # Проверяем другие API ключи
        key_map = {
            'coingecko': self.coingecko_api_key,
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
        }
        return bool(key_map.get(service, ''))
    
    def get_missing_api_keys(self) -> List[str]:
        """Список отсутствующих API ключей"""
        missing = []
        
        for chain in self.chains.enabled_chains:
            scanner_service = f"{chain}scan" if chain != 'ethereum' else 'etherscan'
            if not self.has_api_key(scanner_service):
                missing.append(scanner_service)
        
        return missing


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Создаём глобальный экземпляр конфигурации
config = Config()

# ============================================================================
# BACKWARD COMPATIBILITY (для старого кода)
# ============================================================================

# Telegram
TELEGRAM_BOT_TOKEN = config.telegram.token
TELEGRAM_TOKEN = config.telegram.token  # alias
TELEGRAM_CHANNEL_ID = config.telegram.channel_id
CHAT_ID = config.telegram.channel_id  # alias
ADMIN_CHAT_ID = config.telegram.admin_chat_id

# Production
PORT = config.production.port
HTTP_TIMEOUT = config.production.http_timeout
RPC_TIMEOUT = config.production.rpc_timeout
MAX_MEMORY_MB = config.production.max_memory_mb

# Whale
MIN_USD = config.whale.min_usd_threshold
MIN_CONFIDENCE_SCORE = config.whale.min_confidence_score
POSTS_PER_HOUR_CAP = config.whale.posts_per_hour_cap
POLL_SECONDS = config.whale.poll_seconds

# Chains
ENABLED_CHAINS = config.chains.enabled_chains
CHAINS_ENABLED = config.is_feature_enabled('chains')

# Features
WHALE_ENABLED = config.is_feature_enabled('whale')
NEWS_ENABLED = config.is_feature_enabled('news')
ANALYTICS_ENABLED = config.is_feature_enabled('analytics')
TRADING_ENABLED = config.is_feature_enabled('trading')
HYPERLIQUID_ENABLED = config.is_feature_enabled('hyperliquid')

# Paths
DATA_DIR = str(config.data_dir)
STATE_FILE = str(config.state_file)
WALLET_DB_JSON_PATH = str(config.wallet_db_path)

# Logging
LOG_LEVEL = config.log_level

# Health
HEALTH_CHECK_ENABLED = config.health_check_enabled
HEALTH_CHECK_INTERVAL = config.health_check_interval


# ============================================================================
# EXPORTS
# ============================================================================

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
    # Backward compatibility
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'ADMIN_CHAT_ID',
    'PORT',
    'HTTP_TIMEOUT',
    'RPC_TIMEOUT',
    'MAX_MEMORY_MB',
    'ENABLED_CHAINS',
    'WHALE_ENABLED',
    'NEWS_ENABLED',
    'ANALYTICS_ENABLED',
    'TRADING_ENABLED',
    'HYPERLIQUID_ENABLED',
]