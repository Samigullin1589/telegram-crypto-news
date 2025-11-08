# app/config/settings.py
"""
Configuration Settings v2.0
Модульная система конфигурации с валидацией и гибкими порогами
"""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.config.models import (
    TelegramConfig,
    ProductionConfig,
    RateLimitConfig,
    ChainConfig,
    WhaleConfig,
    HyperliquidConfig,
    TradingConfig,
    NewsConfig,
    SmartDiscoveryConfig,
    ValidationConfig,
    PerformanceConfig,
    AdaptiveThresholdsConfig,
    AnalyticsConfig,
    DatabaseConfig,
    MetricsConfig,
    DiscoveryConfig
)
from app.config.env_loader import EnvironmentLoader
from app.config.validators import ConfigValidator
from app.config.printer import ConfigPrinter
from app.config.paths import PathManager, EnvironmentPaths

logger = logging.getLogger(__name__)


class Config:
    """
    Главный класс конфигурации приложения
    Singleton pattern для единого источника конфигурации
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
        
        print('🔧 [CONFIG] Инициализация конфигурации системы...')
        
        # Загрузчик переменных окружения
        self.env = EnvironmentLoader()
        
        # Загрузка всех конфигурационных секций
        self._load_telegram_config()
        self._load_production_config()
        self._load_rate_limit_config()
        self._load_chains_config()
        self._load_whale_config()
        self._load_hyperliquid_config()
        self._load_trading_config()
        self._load_news_config()
        self._load_smart_discovery_config()
        self._load_validation_config()
        self._load_performance_config()
        self._load_adaptive_thresholds_config()
        self._load_analytics_config()
        self._load_database_config()
        self._load_metrics_config()
        self._load_discovery_config()
        self._load_features()
        self._load_paths()
        self._load_misc_settings()
        self._load_api_keys()
        
        self._initialized = True
        
        # Валидация и вывод информации
        self._validate()
        self._print_summary()
    
    def _load_telegram_config(self):
        """Загрузка конфигурации Telegram"""
        self.telegram = TelegramConfig(
            token=self.env.get_required_env('TELEGRAM_BOT_TOKEN', 'TELEGRAM_TOKEN', 'BOT_TOKEN'),
            channel_id=self.env.get_required_env('TELEGRAM_CHANNEL_ID', 'CHAT_ID', 'CHANNEL_ID'),
            admin_chat_id=self.env.get_env('ADMIN_CHAT_ID', self.env.get_env('TELEGRAM_CHANNEL_ID', '')),
            webhook_url=self.env.get_env('WEBHOOK_URL', '')
        )
    
    def _load_production_config(self):
        """Загрузка production конфигурации"""
        self.production = ProductionConfig(
            port=self.env.get_int_env('PORT', 8000),
            http_timeout=self.env.get_int_env('HTTP_TIMEOUT', 30),
            rpc_timeout=self.env.get_int_env('RPC_TIMEOUT', 15),
            webhook_timeout=self.env.get_int_env('WEBHOOK_TIMEOUT', 10),
            max_memory_mb=self.env.get_int_env('MAX_MEMORY_MB', 450),
            gc_interval_seconds=self.env.get_int_env('GC_INTERVAL_SECONDS', 300),
            max_connections=self.env.get_int_env('MAX_CONNECTIONS', 50),
            max_keepalive=self.env.get_int_env('MAX_KEEPALIVE', 10)
        )
    
    def _load_rate_limit_config(self):
        """Загрузка конфигурации rate limiting"""
        self.rate_limit = RateLimitConfig(
            enabled=self.env.get_bool_env('RATE_LIMIT_ENABLED', True),
            calls_per_minute=self.env.get_int_env('RATE_LIMIT_CALLS', 60),
            burst_size=self.env.get_int_env('RATE_LIMIT_BURST', 10),
            solana_requests=self.env.get_int_env('SOLANA_RATE_LIMIT_REQUESTS', 50),
            solana_window_seconds=self.env.get_int_env('SOLANA_RATE_LIMIT_WINDOW', 60),
            solana_retry_on_429=self.env.get_bool_env('SOLANA_RETRY_ON_429', True)
        )
    
    def _load_chains_config(self):
        """Загрузка конфигурации блокчейнов"""
        # Список активных блокчейнов
        enabled_chains = self.env.get_list_env(
            'ENABLED_CHAINS',
            ['ethereum', 'bsc', 'polygon', 'arbitrum', 'base', 'solana']
        )
        
        # RPC endpoints для каждого блокчейна
        rpc_urls = {
            'ethereum': self.env.get_env('ETHEREUM_RPC_URL', 'https://eth.llamarpc.com'),
            'bsc': self.env.get_env('BSC_RPC_URL', 'https://bsc-dataseed.binance.org'),
            'polygon': self.env.get_env('POLYGON_RPC_URL', 'https://polygon-rpc.com'),
            'arbitrum': self.env.get_env('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc'),
            'base': self.env.get_env('BASE_RPC_URL', 'https://mainnet.base.org'),
            'solana': self.env.get_env('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
            'tron': self.env.get_env('TRON_RPC_URL', 'https://api.trongrid.io'),
            'optimism': self.env.get_env('OPTIMISM_RPC_URL', 'https://mainnet.optimism.io'),
            'avalanche': self.env.get_env('AVALANCHE_RPC_URL', 'https://api.avax.network/ext/bc/C/rpc'),
        }
        
        # API ключи для explorer и RPC сервисов
        api_keys = {
            'etherscan': self.env.get_env('ETHERSCAN_API_KEY', ''),
            'bscscan': self.env.get_env('BSCSCAN_API_KEY', ''),
            'polygonscan': self.env.get_env('POLYGONSCAN_API_KEY', ''),
            'arbiscan': self.env.get_env('ARBISCAN_API_KEY', ''),
            'basescan': self.env.get_env('BASESCAN_API_KEY', ''),
            'helius': self.env.get_env('HELIUS_API_KEY', ''),
            'optimism': self.env.get_env('OPTIMISM_API_KEY', ''),
            'snowtrace': self.env.get_env('SNOWTRACE_API_KEY', ''),
        }
        
        # Fallback RPC URLs
        fallback_urls = {
            'ethereum': self.env.get_env('ETHEREUM_FALLBACK_RPC', 'https://rpc.ankr.com/eth'),
            'solana': self.env.get_env('SOLANA_FALLBACK_RPC', 'https://solana-api.projectserum.com'),
        }
        
        self.chains = ChainConfig(
            enabled_chains=enabled_chains,
            rpc_urls=rpc_urls,
            api_keys=api_keys,
            fallback_urls=fallback_urls
        )
    
    def _load_whale_config(self):
        """
        Загрузка конфигурации whale мониторинга
        КРИТИЧНО: Пороги должны быть реалистичными для обнаружения событий
        """
        # Базовый порог в USD - СНИЖЕН до реалистичного значения
        base_threshold = self.env.get_float_env(
            'WHALE_MIN_VALUE_USD',
            self.env.get_float_env('MIN_USD_THRESHOLD', 10000.0)  # $10K вместо $50K
        )
        
        # Специфичные пороги для разных блокчейнов
        chain_thresholds = {
            'ethereum': self.env.get_float_env('WHALE_ETHEREUM_MIN_USD', base_threshold),
            'bsc': self.env.get_float_env('WHALE_BSC_MIN_USD', base_threshold * 0.5),  # $5K
            'polygon': self.env.get_float_env('WHALE_POLYGON_MIN_USD', base_threshold * 0.3),  # $3K
            'arbitrum': self.env.get_float_env('WHALE_ARBITRUM_MIN_USD', base_threshold * 0.5),  # $5K
            'base': self.env.get_float_env('WHALE_BASE_MIN_USD', base_threshold * 0.5),  # $5K
            'solana': self.env.get_float_env('WHALE_SOLANA_MIN_USD', base_threshold * 0.5),  # $5K
        }
        
        self.whale = WhaleConfig(
            min_usd_threshold=base_threshold,
            chain_thresholds=chain_thresholds,
            min_confidence_score=self.env.get_int_env('MIN_CONFIDENCE_SCORE', 6),
            posts_per_hour_cap=self.env.get_int_env('POSTS_PER_HOUR_CAP', 5),
            poll_seconds=self.env.get_int_env('POLL_SECONDS', 120),
            start_from_minutes_ago=self.env.get_int_env('START_FROM_MINUTES_AGO', 60)
        )
        
        logger.info(f"🐋 [CONFIG] Whale пороги установлены:")
        logger.info(f"  • Базовый: ${base_threshold:,.0f}")
        for chain, threshold in chain_thresholds.items():
            logger.info(f"  • {chain}: ${threshold:,.0f}")
    
    def _load_hyperliquid_config(self):
        """Загрузка конфигурации Hyperliquid"""
        self.hyperliquid = HyperliquidConfig(
            enabled=self.env.get_bool_env('HYPERLIQUID_ENABLED', True),
            api_url=self.env.get_env('HYPERLIQUID_API_URL', 'https://api.hyperliquid.xyz'),
            min_trade_usd=self.env.get_float_env('HYPERLIQUID_MIN_TRADE_USD', 100000.0),
            min_liquidation_usd=self.env.get_float_env('HYPERLIQUID_MIN_LIQUIDATION_USD', 50000.0),
            min_whale_activity_usd=self.env.get_float_env('HYPERLIQUID_MIN_WHALE_ACTIVITY_USD', 500000.0),
            notify_whale_activity=self.env.get_bool_env('HYPERLIQUID_NOTIFY_WHALE_ACTIVITY', True),
            notify_liquidations=self.env.get_bool_env('HYPERLIQUID_NOTIFY_LIQUIDATIONS', True)
        )
    
    def _load_trading_config(self):
        """Загрузка конфигурации торговли"""
        monitored_assets = self.env.get_list_env(
            'TRADING_MONITORED_ASSETS',
            ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK']
        )
        
        self.trading = TradingConfig(
            enabled=self.env.get_bool_env('TRADING_ENABLED', True),
            signal_interval_hours=self.env.get_int_env('TRADING_SIGNAL_INTERVAL_HOURS', 1),
            monitored_assets=monitored_assets,
            position_update_interval_seconds=self.env.get_int_env('POSITION_UPDATE_INTERVAL_SECONDS', 60)
        )
    
    def _load_news_config(self):
        """Загрузка конфигурации новостей"""
        self.news = NewsConfig(
            enabled=self.env.get_bool_env('NEWS_ENABLED', True),
            fetch_interval=self.env.get_int_env(
                'FETCH_INTERVAL',
                self.env.get_int_env('NEWS_CHECK_INTERVAL', 300)
            ),
            posts_per_hour_cap=self.env.get_int_env('NEWS_POSTS_PER_HOUR', 3),
            min_confidence_score=self.env.get_int_env('NEWS_MIN_CONFIDENCE_SCORE', 6),
            db_path=self.env.get_env('NEWS_DB_PATH', 'news_database.sqlite'),
            ai_enabled=self.env.get_bool_env('NEWS_AI_ENABLED', True),
            ai_provider=self.env.get_env('NEWS_AI_PROVIDER', 'openai'),
            max_article_age_hours=self.env.get_int_env('NEWS_MAX_AGE_HOURS', 24),
            duplicate_check_enabled=self.env.get_bool_env('NEWS_DUPLICATE_CHECK', True),
            image_download_enabled=self.env.get_bool_env('NEWS_IMAGE_DOWNLOAD', True),
            max_retries=self.env.get_int_env('NEWS_MAX_RETRIES', 3),
            retry_delay_seconds=self.env.get_int_env('NEWS_RETRY_DELAY', 5)
        )
    
    def _load_smart_discovery_config(self):
        """Загрузка конфигурации smart discovery"""
        self.smart_discovery = SmartDiscoveryConfig(
            enabled=self.env.get_bool_env('SMART_DISCOVERY_ENABLED', True),
            interval_hours=self.env.get_int_env('SMART_DISCOVERY_INTERVAL_HOURS', 6),
            max_new_wallets=self.env.get_int_env('SMART_DISCOVERY_MAX_NEW_WALLETS', 10),
            min_success_rate=self.env.get_float_env('SMART_DISCOVERY_MIN_SUCCESS_RATE', 0.6),
            min_transactions=self.env.get_int_env('SMART_DISCOVERY_MIN_TRANSACTIONS', 10),
            profitability_threshold=self.env.get_float_env('SMART_DISCOVERY_PROFIT_THRESHOLD', 0.15),
            consistency_weight=self.env.get_float_env('SMART_DISCOVERY_CONSISTENCY_WEIGHT', 0.4),
            profitability_weight=self.env.get_float_env('SMART_DISCOVERY_PROFIT_WEIGHT', 0.3),
            volume_weight=self.env.get_float_env('SMART_DISCOVERY_VOLUME_WEIGHT', 0.3),
            scan_depth_days=self.env.get_int_env('SMART_DISCOVERY_SCAN_DEPTH_DAYS', 30)
        )
    
    def _load_validation_config(self):
        """Загрузка конфигурации валидации"""
        self.validation = ValidationConfig(
            enabled=self.env.get_bool_env('VALIDATION_ENABLED', True),
            interval_days=self.env.get_int_env('VALIDATION_INTERVAL_DAYS', 1),
            min_score_to_keep=self.env.get_int_env('VALIDATION_MIN_SCORE_TO_KEEP', 30),
            remove_inactive_days=self.env.get_int_env('VALIDATION_REMOVE_INACTIVE_DAYS', 30),
            revalidation_period_days=self.env.get_int_env('VALIDATION_REVALIDATION_DAYS', 7),
            performance_tracking_enabled=self.env.get_bool_env('VALIDATION_PERFORMANCE_TRACKING', True),
            auto_remove_failing=self.env.get_bool_env('VALIDATION_AUTO_REMOVE_FAILING', True)
        )
    
    def _load_performance_config(self):
        """Загрузка конфигурации производительности"""
        self.performance = PerformanceConfig(
            tracking_enabled=self.env.get_bool_env('PERFORMANCE_TRACKING_ENABLED', True),
            success_threshold=self.env.get_float_env('PERFORMANCE_SUCCESS_THRESHOLD', 0.05),
            time_window_hours=self.env.get_int_env('PERFORMANCE_TIME_WINDOW_HOURS', 24),
            min_events_for_evaluation=self.env.get_int_env('PERFORMANCE_MIN_EVENTS', 5),
            store_detailed_history=self.env.get_bool_env('PERFORMANCE_STORE_HISTORY', True),
            calculate_roi=self.env.get_bool_env('PERFORMANCE_CALCULATE_ROI', True)
        )
    
    def _load_adaptive_thresholds_config(self):
        """Загрузка конфигурации адаптивных порогов"""
        self.adaptive_thresholds = AdaptiveThresholdsConfig(
            enabled=self.env.get_bool_env('ADAPTIVE_THRESHOLDS_ENABLED', True),
            base_min_confidence=self.env.get_int_env('ADAPTIVE_BASE_MIN_CONFIDENCE', 40),
            market_volatility_adjustment=self.env.get_bool_env('ADAPTIVE_VOLATILITY_ADJUST', True),
            performance_based_adjustment=self.env.get_bool_env('ADAPTIVE_PERFORMANCE_ADJUST', True),
            adjustment_interval_hours=self.env.get_int_env('ADAPTIVE_ADJUSTMENT_INTERVAL', 6),
            min_threshold=self.env.get_int_env('ADAPTIVE_MIN_THRESHOLD', 30),
            max_threshold=self.env.get_int_env('ADAPTIVE_MAX_THRESHOLD', 70)
        )
    
    def _load_analytics_config(self):
        """Загрузка конфигурации аналитики"""
        self.analytics = AnalyticsConfig(
            enabled=self.env.get_bool_env('ANALYTICS_ENABLED', True),
            sentiment_analysis=self.env.get_bool_env('ANALYTICS_SENTIMENT', True),
            risk_scoring=self.env.get_bool_env('ANALYTICS_RISK_SCORING', True),
            correlation_analysis=self.env.get_bool_env('ANALYTICS_CORRELATION', True),
            anomaly_detection=self.env.get_bool_env('ANALYTICS_ANOMALY_DETECTION', True),
            market_regime_detection=self.env.get_bool_env('ANALYTICS_MARKET_REGIME', True),
            calculate_intervals=self.env.get_int_env('ANALYTICS_CALCULATE_INTERVAL', 300)
        )
    
    def _load_database_config(self):
        """Загрузка конфигурации базы данных"""
        self.database = DatabaseConfig(
            type=self.env.get_env('DATABASE_TYPE', 'sqlite'),
            path=self.env.get_env('DATABASE_PATH', 'data/crypto_monitor.db'),
            news_db_path=self.env.get_env(
                'NEWS_DB_PATH',
                self.env.get_env('DB_PATH', 'news_database.sqlite')
            ),
            wallet_db_path=self.env.get_env('WALLET_DB_JSON_PATH', 'data/wallets/tracked_wallets.json'),
            watchlist_file=self.env.get_env('WATCHLIST_FILE', 'data/wallets/watchlist.json'),
            history_file=self.env.get_env('HISTORY_FILE', 'data/history/events.json'),
            backup_enabled=self.env.get_bool_env('DATABASE_BACKUP_ENABLED', True),
            backup_interval_hours=self.env.get_int_env('DATABASE_BACKUP_INTERVAL', 24),
            max_backups=self.env.get_int_env('DATABASE_MAX_BACKUPS', 7),
            connection_pool_size=self.env.get_int_env('DATABASE_POOL_SIZE', 5)
        )
    
    def _load_metrics_config(self):
        """Загрузка конфигурации метрик"""
        self.metrics = MetricsConfig(
            enabled=self.env.get_bool_env('ENABLE_METRICS', False),
            port=self.env.get_int_env('METRICS_PORT', 9090),
            sentry_dsn=self.env.get_env('SENTRY_DSN', None)
        )
    
    def _load_discovery_config(self):
        """Загрузка конфигурации discovery engine"""
        # Парсинг blacklist из строки
        blacklist_str = self.env.get_env('DISCOVERY_BLACKLIST', '')
        blacklist_set = set()
        
        if blacklist_str:
            blacklist_set = {item.strip().upper() for item in blacklist_str.split(',') if item.strip()}
        else:
            # Дефолтный blacklist
            blacklist_set = {
                'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD',
                'WBTC', 'WETH', 'WBNB', 'WMATIC', 'WAVAX',
                'STETH', 'RETH', 'CBETH',
                'SPAM', 'SCAM', 'TEST', 'FAKE'
            }
        
        self.discovery = DiscoveryConfig(
            enabled=self.env.get_bool_env('DISCOVERY_ENABLED', True),
            interval_hours=self.env.get_int_env('DISCOVERY_INTERVAL_HOURS', 6),
            top_n_per_chain=self.env.get_int_env('DISCOVERY_TOP_N_PER_CHAIN', 50),
            min_token_age_days=self.env.get_int_env('MIN_TOKEN_AGE_DAYS', 30),
            min_volume_usd=self.env.get_float_env('DISCOVERY_MIN_VOLUME_USD', 100000.0),
            min_market_cap_usd=self.env.get_float_env('DISCOVERY_MIN_MARKET_CAP_USD', 1000000.0),
            max_price_change_percent=self.env.get_float_env('DISCOVERY_MAX_PRICE_CHANGE_PERCENT', 200.0),
            blacklist=blacklist_set,
            watchlist_file=self.env.get_env('WATCHLIST_FILE', 'data/wallets/watchlist.json')
        )
    
    def _load_features(self):
        """Загрузка флагов фич"""
        self.features_enabled = {
            'whale': self.env.get_bool_env('WHALE_ENABLED', True),
            'news': self.env.get_bool_env('NEWS_ENABLED', True),
            'chains': self.env.get_bool_env('CHAINS_ENABLED', True),
            'analytics': self.env.get_bool_env('ANALYTICS_ENABLED', True),
            'trading': self.env.get_bool_env('TRADING_ENABLED', True),
            'hyperliquid': self.env.get_bool_env('HYPERLIQUID_ENABLED', True),
            'smart_discovery': self.env.get_bool_env('SMART_DISCOVERY_ENABLED', True),
            'validation': self.env.get_bool_env('VALIDATION_ENABLED', True),
            'adaptive_thresholds': self.env.get_bool_env('ADAPTIVE_THRESHOLDS_ENABLED', True),
            'performance_tracking': self.env.get_bool_env('PERFORMANCE_TRACKING_ENABLED', True),
            'discovery': self.env.get_bool_env('DISCOVERY_ENABLED', True),
        }
    
    def _load_paths(self):
        """Загрузка путей к файлам и директориям"""
        data_dir = EnvironmentPaths.get_data_dir()
        self.path_manager = PathManager(data_dir)
        
        self.data_dir = self.path_manager.data_dir
        self.state_file = self.path_manager.state_file
        self.wallet_db_path = self.path_manager.wallet_db_path
        self.watchlist_file = self.path_manager.watchlist_file
        self.history_file = self.path_manager.history_file
        self.positions_dir = self.path_manager.positions_dir
        self.performance_dir = self.path_manager.performance_dir
        
        self.path_manager.create_directories()
    
    def _load_misc_settings(self):
        """Загрузка прочих настроек"""
        self.webhook_url = self.env.get_env('WEBHOOK_URL', '')
        self.render_external_url = self.env.get_env('RENDER_EXTERNAL_URL', '')
        self.render_service_name = self.env.get_env('RENDER_SERVICE_NAME', 'crypto-compass')
        
        self.log_level = self.env.get_env('LOG_LEVEL', 'INFO').upper()
        
        self.health_check_enabled = self.env.get_bool_env('HEALTH_CHECK_ENABLED', True)
        self.health_check_interval = self.env.get_int_env('HEALTH_CHECK_INTERVAL', 300)
        self.health_check_max_silence = self.env.get_int_env('HEALTH_CHECK_MAX_SILENCE', 3600)
        self.send_startup_notification = self.env.get_bool_env('SEND_STARTUP_NOTIFICATION', True)
        self.send_daily_stats = self.env.get_bool_env('SEND_DAILY_STATS', True)
    
    def _load_api_keys(self):
        """Загрузка API ключей"""
        self.coingecko_api_key = self.env.get_env('COINGECKO_API_KEY', '')
        self.openai_api_key = self.env.get_env('OPENAI_API_KEY', '')
        self.anthropic_api_key = self.env.get_env('ANTHROPIC_API_KEY', '')
        self.gemini_api_key = self.env.get_env('GEMINI_API_KEY', '')
        self.alchemy_api_key = self.env.get_env('ALCHEMY_API_KEY', '')
    
    def _validate(self):
        """Валидация конфигурации"""
        validator = ConfigValidator()
        
        all_errors = []
        all_warnings = []
        
        # Валидация лимитов памяти
        errors, warnings = validator.validate_memory_limits(self.production.max_memory_mb)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Валидация блокчейнов
        errors, warnings = validator.validate_chains(self.chains.enabled_chains, self.chains.rpc_urls)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Валидация whale конфигурации
        errors, warnings = validator.validate_whale_config(
            self.whale.min_usd_threshold,
            self.whale.posts_per_hour_cap
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Валидация AI ключей для новостей
        ai_keys = {
            'openai': self.openai_api_key,
            'anthropic': self.anthropic_api_key,
            'gemini': self.gemini_api_key
        }
        errors, warnings = validator.validate_news_config(self.news.enabled, ai_keys)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Валидация торговой конфигурации
        errors, warnings = validator.validate_trading_config(
            self.trading.enabled,
            self.trading.monitored_assets
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Валидация discovery конфигурации
        errors, warnings = validator.validate_discovery_config(
            self.discovery.min_token_age_days,
            self.discovery.min_volume_usd,
            self.discovery.min_market_cap_usd
        )
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # Обработка ошибок валидации
        if all_errors:
            print('❌ [CONFIG] Критические ошибки конфигурации:')
            for error in all_errors:
                print(f'   • {error}')
            raise ValueError('Некорректная конфигурация. Исправьте ошибки и перезапустите.')
        
        # Вывод предупреждений
        if all_warnings:
            print('⚠️  [CONFIG] Предупреждения конфигурации:')
            for warning in all_warnings:
                print(f'   • {warning}')
    
    def _print_summary(self):
        """Вывод summary конфигурации"""
        # Сбор информации о доступных API ключах
        api_keys_list = []
        if self.openai_api_key:
            api_keys_list.append('OpenAI')
        if self.anthropic_api_key:
            api_keys_list.append('Anthropic')
        if self.gemini_api_key:
            api_keys_list.append('Gemini')
        if self.coingecko_api_key:
            api_keys_list.append('CoinGecko')
        
        # Формирование данных для вывода
        config_data = {
            'telegram': {
                'token': self.telegram.token,
                'channel_id': self.telegram.channel_id,
                'admin_chat_id': self.telegram.admin_chat_id
            },
            'production': {
                'port': self.production.port,
                'max_memory_mb': self.production.max_memory_mb,
                'http_timeout': self.production.http_timeout,
                'gc_interval_seconds': self.production.gc_interval_seconds
            },
            'chains': {
                'enabled_chains': self.chains.enabled_chains
            },
            'whale': {
                'min_usd_threshold': self.whale.min_usd_threshold,
                'chain_thresholds': self.whale.chain_thresholds,
                'min_confidence_score': self.whale.min_confidence_score,
                'posts_per_hour_cap': self.whale.posts_per_hour_cap
            },
            'news_enabled': self.news.enabled,
            'news': {
                'sources_count': len(self.news.sources),
                'fetch_interval': self.news.fetch_interval,
                'ai_enabled': self.news.ai_enabled,
                'ai_provider': self.news.ai_provider
            },
            'trading_enabled': self.trading.enabled,
            'trading': {
                'assets_count': len(self.trading.monitored_assets),
                'signal_interval_hours': self.trading.signal_interval_hours
            },
            'hyperliquid_enabled': self.hyperliquid.enabled,
            'hyperliquid': {
                'min_trade_usd': self.hyperliquid.min_trade_usd,
                'min_liquidation_usd': self.hyperliquid.min_liquidation_usd
            },
            'discovery_enabled': self.discovery.enabled,
            'discovery': {
                'top_n_per_chain': self.discovery.top_n_per_chain,
                'min_token_age_days': self.discovery.min_token_age_days,
                'min_volume_usd': self.discovery.min_volume_usd,
                'min_market_cap_usd': self.discovery.min_market_cap_usd,
                'blacklist_size': len(self.discovery.blacklist)
            },
            'features': self.features_enabled,
            'rate_limit': {
                'calls_per_minute': self.rate_limit.calls_per_minute,
                'solana_requests': self.rate_limit.solana_requests,
                'solana_window_seconds': self.rate_limit.solana_window_seconds
            },
            'storage': {
                'data_dir': str(self.data_dir),
                'database_type': self.database.type
            },
            'api_keys': api_keys_list
        }
        
        ConfigPrinter.print_summary(config_data)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """
        Проверка включена ли фича
        
        Args:
            feature: Название фичи
            
        Returns:
            True если фича включена
        """
        return self.features_enabled.get(feature, False)
    
    def get_rpc_url(self, chain: str) -> str:
        """
        Получение RPC URL для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            RPC URL
        """
        return self.chains.rpc_urls.get(chain, '')
    
    def get_fallback_rpc_url(self, chain: str) -> Optional[str]:
        """
        Получение fallback RPC URL для блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Fallback RPC URL или None
        """
        return self.chains.fallback_urls.get(chain)
    
    def get_whale_threshold(self, chain: str) -> float:
        """
        Получение порога для конкретного блокчейна
        
        Args:
            chain: Название блокчейна
            
        Returns:
            Порог в USD
        """
        # Проверка chain-specific порога
        if hasattr(self.whale, 'chain_thresholds') and self.whale.chain_thresholds:
            chain_threshold = self.whale.chain_thresholds.get(chain)
            if chain_threshold is not None:
                return chain_threshold
        
        # Fallback на базовый порог
        return self.whale.min_usd_threshold
    
    def has_api_key(self, service: str) -> bool:
        """
        Проверка наличия API ключа
        
        Args:
            service: Название сервиса
            
        Returns:
            True если ключ есть
        """
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
        """
        Получение API ключа
        
        Args:
            service: Название сервиса
            
        Returns:
            API ключ
        """
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
    
    def get_ai_provider(self) -> Optional[str]:
        """
        Определение AI провайдера для использования
        
        Returns:
            Название провайдера или None
        """
        if self.news.ai_enabled:
            # Приоритет заданному провайдеру
            if self.news.ai_provider == 'openai' and self.openai_api_key:
                return 'openai'
            elif self.news.ai_provider == 'anthropic' and self.anthropic_api_key:
                return 'anthropic'
            elif self.news.ai_provider == 'gemini' and self.gemini_api_key:
                return 'gemini'
            
            # Fallback на первый доступный
            if self.openai_api_key:
                return 'openai'
            elif self.anthropic_api_key:
                return 'anthropic'
            elif self.gemini_api_key:
                return 'gemini'
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация конфигурации в словарь
        
        Returns:
            Dict с конфигурацией
        """
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
                'chain_thresholds': getattr(self.whale, 'chain_thresholds', {}),
                'min_confidence': self.whale.min_confidence_score,
            },
            'trading': {
                'enabled': self.trading.enabled,
                'assets_count': len(self.trading.monitored_assets),
            },
            'news': {
                'enabled': self.news.enabled,
                'sources_count': len(self.news.sources),
            },
            'discovery': {
                'enabled': self.discovery.enabled,
                'top_n_per_chain': self.discovery.top_n_per_chain,
            }
        }


# Создание глобального экземпляра конфигурации
config = Config()