# app/settings.py (РЕВОЛЮЦИОННАЯ ВЕРСИЯ v4.0 - Production Ready)
"""
INTELLIGENT CRYPTO MONITOR - Configuration

НОВЫЕ ВОЗМОЖНОСТИ v4.0:
✅ Production-ready настройки для Render.com
✅ Таймауты для HTTP/RPC запросов
✅ Контроль памяти и ресурсов
✅ Улучшенная обработка ошибок
✅ Smart Money Discovery - настройки автопоиска трейдеров
✅ Validation Engine - параметры очистки базы
✅ Performance Tracking - отслеживание результатов
✅ Adaptive Thresholds - динамические пороги
✅ Learning System - параметры самообучения
✅ Market Regime Detection - определение bull/bear
✅ Trading System - генерация торговых сигналов
✅ Bot Commands - интерактивные команды (/stats, /positions, /help)
✅ News Processor - мониторинг новостей
✅ Whale Monitor - отслеживание китов
"""

import os
from dotenv import load_dotenv
from typing import List, Optional, Dict
from datetime import datetime

load_dotenv()

# ============================================================================
# PRODUCTION НАСТРОЙКИ (НОВОЕ v4.0) - КРИТИЧНО ДЛЯ RENDER.COM
# ============================================================================

# HTTP Server
PORT = int(os.getenv('PORT', '8000'))

# HTTP Timeouts (критично для Render)
HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', '30'))  # секунды
RPC_TIMEOUT = int(os.getenv('RPC_TIMEOUT', '15'))  # секунды для RPC запросов
WEBHOOK_TIMEOUT = int(os.getenv('WEBHOOK_TIMEOUT', '10'))  # секунды для webhook

# Memory Control (критично для Render Free Tier - 512MB)
MAX_MEMORY_MB = int(os.getenv('MAX_MEMORY_MB', '450'))  # оставляем 62MB запаса
GC_INTERVAL_SECONDS = int(os.getenv('GC_INTERVAL_SECONDS', '300'))  # 5 минут

# Webhook URL (для Telegram webhook mode)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # будет автоопределён если пусто
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', '')

# Connection Pools
HTTP_MAX_CONNECTIONS = int(os.getenv('HTTP_MAX_CONNECTIONS', '50'))
HTTP_MAX_KEEPALIVE = int(os.getenv('HTTP_MAX_KEEPALIVE', '10'))

# System Status
WHALE_ENABLED = os.getenv('WHALE_ENABLED', 'true').lower() == 'true'
NEWS_ENABLED = os.getenv('NEWS_ENABLED', 'false').lower() == 'true'

# ============================================================================
# ОБЩИЕ НАСТРОЙКИ
# ============================================================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID') or os.getenv('TELEGRAM_CHANNEL_ID')

# ИСПРАВЛЕНО: Надёжное получение ADMIN_CHAT_ID
_admin_chat_raw = os.getenv('ADMIN_CHAT_ID', '').strip()
ADMIN_CHAT_ID = _admin_chat_raw if _admin_chat_raw else CHAT_ID

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID обязательны")

# Старые настройки (совместимость)
TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN
TELEGRAM_CHANNEL_ID = CHAT_ID

# ============================================================================
# BOT COMMANDS - НОВОЕ!
# ============================================================================
# Используем тот же токен для команд (или отдельный если указан)
BOT_TOKEN = os.getenv('BOT_TOKEN', TELEGRAM_BOT_TOKEN)

# ============================================================================
# WHALE MONITOR - ОСНОВНЫЕ ПАРАМЕТРЫ
# ============================================================================
ASSETS = os.getenv('ASSETS', '*')
ASSETS_LIST = [] if ASSETS == '*' else [a.strip() for a in ASSETS.split(',') if a.strip()]

# Базовые пороги (оптимизировано для production)
MIN_USD = float(os.getenv('MIN_USD', '100000'))  # снижено с 500k
MIN_USD_FLOOR = float(os.getenv('MIN_USD_FLOOR', '50000'))
MIN_USD_K = float(os.getenv('MIN_USD_K', '0.02'))
MIN_USD_PCTL = float(os.getenv('MIN_USD_PCTL', '75'))

# Временные параметры (оптимизировано для production)
POLL_SECONDS = int(os.getenv('POLL_SECONDS', '7'))  # быстрый опрос
START_FROM_MINUTES_AGO = int(os.getenv('START_FROM_MINUTES_AGO', '15'))  # короткая история

# Discovery параметры
DISCOVERY_TOP_N_PER_CHAIN = int(os.getenv('DISCOVERY_TOP_N_PER_CHAIN', '200'))
DISCOVERY_REFRESH_HOURS = int(os.getenv('DISCOVERY_REFRESH_HOURS', '12'))
DISCOVERY_BLACKLIST = [b.strip() for b in os.getenv('DISCOVERY_BLACKLIST', '').split(',') if b.strip()]
MIN_TOKEN_AGE_DAYS = int(os.getenv('MIN_TOKEN_AGE_DAYS', '7'))

# Лимиты публикаций
POSTS_PER_HOUR_CAP = int(os.getenv('POSTS_PER_HOUR_CAP', '6'))

# Визуализация (оптимизировано для экономии памяти)
ENABLE_IMAGES = int(os.getenv('ENABLE_IMAGES', '0')) == 1  # отключено для production
CHART_BACKEND = os.getenv('CHART_BACKEND', 'sparkline')
CHART_THEME = os.getenv('CHART_THEME', 'dark')
CHART_WIDTH = int(os.getenv('CHART_WIDTH', '800'))
CHART_HEIGHT = int(os.getenv('CHART_HEIGHT', '600'))
EXCHANGE_PREFERENCE = [e.strip() for e in os.getenv('EXCHANGE_PREFERENCE', 'binance,okx,bybit,coinbase').split(',')]

# Логирование (оптимизировано для production)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DEBUG_FILTERS = int(os.getenv('DEBUG_FILTERS', '0')) == 1  # отключено для production

# Настройки алертов
ENABLE_ALERTS = int(os.getenv('ENABLE_ALERTS', '1')) == 1
ALERT_COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', '300'))
SEND_STARTUP_NOTIFICATION = int(os.getenv('SEND_STARTUP_NOTIFICATION', '1')) == 1
SEND_DAILY_STATS = int(os.getenv('SEND_DAILY_STATS', '1')) == 1

# Rate Limiting
RATE_LIMIT_ENABLED = int(os.getenv('RATE_LIMIT_ENABLED', '1')) == 1
RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '5'))
RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '60'))

# Retry настройки (с таймаутами)
RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
RETRY_BACKOFF_FACTOR = int(os.getenv('RETRY_BACKOFF_FACTOR', '2'))
RETRY_TIMEOUT = int(os.getenv('RETRY_TIMEOUT', '15'))  # снижено с 30

# Health Check
HEALTH_CHECK_ENABLED = int(os.getenv('HEALTH_CHECK_ENABLED', '1')) == 1
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
HEALTH_CHECK_MAX_SILENCE = int(os.getenv('HEALTH_CHECK_MAX_SILENCE', '600'))

# ============================================================================
# WHALE MONITOR - WATCHLIST (ИСПРАВЛЕНИЕ ОШИБКИ)
# ============================================================================
WATCHLIST_FILE = os.getenv('WATCHLIST_FILE', 'data/watchlist.json')
WATCHLIST_ENABLED = int(os.getenv('WATCHLIST_ENABLED', '1')) == 1
WATCHLIST_AUTO_ADD_TOP_PERFORMERS = int(os.getenv('WATCHLIST_AUTO_ADD_TOP_PERFORMERS', '1')) == 1
WATCHLIST_MIN_PERFORMANCE_TO_ADD = float(os.getenv('WATCHLIST_MIN_PERFORMANCE_TO_ADD', '0.50'))
WATCHLIST_MAX_SIZE = int(os.getenv('WATCHLIST_MAX_SIZE', '100'))

# ============================================================================
# NEWS PROCESSOR - НАСТРОЙКИ (ИСПРАВЛЕНИЕ ОШИБКИ)
# ============================================================================
NEWS_PROCESSOR_ENABLED = NEWS_ENABLED
NEWS_CHECK_INTERVAL_MINUTES = int(os.getenv('NEWS_CHECK_INTERVAL_MINUTES', '15'))
NEWS_MAX_AGE_HOURS = int(os.getenv('NEWS_MAX_AGE_HOURS', '24'))
NEWS_MIN_IMPACT_SCORE = int(os.getenv('NEWS_MIN_IMPACT_SCORE', '7'))
NEWS_SOURCES = [s.strip() for s in os.getenv('NEWS_SOURCES', 'cryptopanic,newsapi,coingecko').split(',') if s.strip()]
NEWS_SENTIMENT_ANALYSIS_ENABLED = int(os.getenv('NEWS_SENTIMENT_ANALYSIS_ENABLED', '0')) == 1
NEWS_AUTO_TRANSLATE = int(os.getenv('NEWS_AUTO_TRANSLATE', '0')) == 1
NEWS_TARGET_LANGUAGE = os.getenv('NEWS_TARGET_LANGUAGE', 'ru')

# Google Cloud Translation API (опционально)
GOOGLE_CLOUD_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# ============================================================================
# TRADING SYSTEM
# ============================================================================

# Главный переключатель Trading System
TRADING_ENABLED = os.getenv('TRADING_ENABLED', 'true').lower() == 'true'  # включено по умолчанию

# Настройки торговых сигналов
TRADING_MIN_CONFIDENCE = int(os.getenv('TRADING_MIN_CONFIDENCE', '70'))
TRADING_MAX_SIGNALS_PER_DAY = int(os.getenv('TRADING_MAX_SIGNALS_PER_DAY', '10'))
TRADING_SIGNAL_COOLDOWN_MINUTES = int(os.getenv('TRADING_SIGNAL_COOLDOWN_MINUTES', '60'))
TRADING_SIGNAL_INTERVAL_HOURS = int(os.getenv('TRADING_SIGNAL_INTERVAL_HOURS', '1'))

# Risk Management
TRADING_MAX_POSITION_SIZE_USD = float(os.getenv('TRADING_MAX_POSITION_SIZE_USD', '10000'))
TRADING_MAX_OPEN_POSITIONS = int(os.getenv('TRADING_MAX_OPEN_POSITIONS', '5'))
TRADING_DEFAULT_STOP_LOSS_PERCENT = float(os.getenv('TRADING_DEFAULT_STOP_LOSS_PERCENT', '3.0'))
TRADING_DEFAULT_TAKE_PROFIT_PERCENT = float(os.getenv('TRADING_DEFAULT_TAKE_PROFIT_PERCENT', '8.0'))

# Signal Filters
TRADING_MIN_TECHNICAL_SCORE = int(os.getenv('TRADING_MIN_TECHNICAL_SCORE', '70'))
TRADING_MIN_FUNDAMENTAL_SCORE = int(os.getenv('TRADING_MIN_FUNDAMENTAL_SCORE', '60'))
TRADING_MIN_ML_CONFIDENCE = int(os.getenv('TRADING_MIN_ML_CONFIDENCE', '75'))

# Dry Run Mode (для тестирования)
TRADING_DRY_RUN = os.getenv('TRADING_DRY_RUN', 'true').lower() == 'true'

# ============================================================================
# НОВОЕ: SMART MONEY DISCOVERY (Автопоиск успешных трейдеров)
# ============================================================================

# Главный переключатель
SMART_DISCOVERY_ENABLED = int(os.getenv('SMART_DISCOVERY_ENABLED', '1')) == 1

# Интервал запуска (часы)
SMART_DISCOVERY_INTERVAL_HOURS = int(os.getenv('SMART_DISCOVERY_INTERVAL_HOURS', '6'))

# Критерии отбора токенов
SMART_DISCOVERY_MIN_PRICE_CHANGE = float(os.getenv('SMART_DISCOVERY_MIN_PRICE_CHANGE', '3.0'))  # x3 минимум
SMART_DISCOVERY_MAX_TOKENS_TO_ANALYZE = int(os.getenv('SMART_DISCOVERY_MAX_TOKENS_TO_ANALYZE', '20'))  # топ-20

# Критерии успешности кошельков
SMART_DISCOVERY_MIN_WALLET_ROI = float(os.getenv('SMART_DISCOVERY_MIN_WALLET_ROI', '1.0'))  # +100% ROI
SMART_DISCOVERY_MIN_WIN_RATE = float(os.getenv('SMART_DISCOVERY_MIN_WIN_RATE', '0.60'))  # 60% winrate
SMART_DISCOVERY_MIN_TRADES = int(os.getenv('SMART_DISCOVERY_MIN_TRADES', '5'))  # минимум сделок
SMART_DISCOVERY_LOOKBACK_DAYS = int(os.getenv('SMART_DISCOVERY_LOOKBACK_DAYS', '90'))  # анализ истории

# Ограничения
SMART_DISCOVERY_MAX_WALLETS_PER_RUN = int(os.getenv('SMART_DISCOVERY_MAX_WALLETS_PER_RUN', '50'))  # макс кошельков для анализа
SMART_DISCOVERY_MAX_NEW_WALLETS = int(os.getenv('SMART_DISCOVERY_MAX_NEW_WALLETS', '10'))  # макс новых за раз

# Источники данных
SMART_DISCOVERY_SOURCES = os.getenv('SMART_DISCOVERY_SOURCES', 'coingecko,dexscreener').split(',')

# ============================================================================
# НОВОЕ: VALIDATION ENGINE (Автоочистка базы)
# ============================================================================

# Главный переключатель
VALIDATION_ENABLED = int(os.getenv('VALIDATION_ENABLED', '1')) == 1

# Интервал запуска (дни)
VALIDATION_INTERVAL_DAYS = int(os.getenv('VALIDATION_INTERVAL_DAYS', '7'))

# Критерии удаления
VALIDATION_MAX_INACTIVE_DAYS = int(os.getenv('VALIDATION_MAX_INACTIVE_DAYS', '30'))  # снижено с 60
VALIDATION_MIN_SCORE_TO_KEEP = int(os.getenv('VALIDATION_MIN_SCORE_TO_KEEP', '30'))  # минимальный скор
VALIDATION_MIN_TRADES_TO_KEEP = int(os.getenv('VALIDATION_MIN_TRADES_TO_KEEP', '3'))  # минимум сделок
VALIDATION_MIN_WIN_RATE_TO_KEEP = float(os.getenv('VALIDATION_MIN_WIN_RATE_TO_KEEP', '0.40'))  # минимальный winrate
VALIDATION_MIN_ROI_TO_KEEP = float(os.getenv('VALIDATION_MIN_ROI_TO_KEEP', '-0.20'))  # -20% ROI минимум

# Дополнительные проверки
VALIDATION_CHECK_LAST_TRADE = int(os.getenv('VALIDATION_CHECK_LAST_TRADE', '1')) == 1
VALIDATION_CHECK_PERFORMANCE = int(os.getenv('VALIDATION_CHECK_PERFORMANCE', '1')) == 1

# Уведомления
VALIDATION_NOTIFY_ON_REMOVAL = int(os.getenv('VALIDATION_NOTIFY_ON_REMOVAL', '1')) == 1
VALIDATION_NOTIFY_THRESHOLD = int(os.getenv('VALIDATION_NOTIFY_THRESHOLD', '5'))  # уведомить если удалено >5

# ============================================================================
# НОВОЕ: PERFORMANCE TRACKING (Отслеживание результатов)
# ============================================================================

# Главный переключатель
PERFORMANCE_TRACKING_ENABLED = int(os.getenv('PERFORMANCE_TRACKING_ENABLED', '1')) == 1

# Интервалы проверки (в минутах) - конвертируем в часы
PERFORMANCE_CHECK_INTERVALS = [int(x) for x in os.getenv('PERFORMANCE_CHECK_INTERVALS', '1,4,24,72,168').split(',')]  # 1ч, 4ч, 24ч, 72ч, 168ч

# История
PERFORMANCE_HISTORY_SIZE = int(os.getenv('PERFORMANCE_HISTORY_SIZE', '1000'))  # макс сигналов в истории
PERFORMANCE_LOOKBACK_DAYS = int(os.getenv('PERFORMANCE_LOOKBACK_DAYS', '90'))  # период анализа

# Критерии успеха
PERFORMANCE_SUCCESS_THRESHOLD = float(os.getenv('PERFORMANCE_SUCCESS_THRESHOLD', '0.05'))  # +5% минимум
PERFORMANCE_MIN_CONFIDENCE_FOR_TRACKING = int(os.getenv('PERFORMANCE_MIN_CONFIDENCE_FOR_TRACKING', '50'))  # минимальная confidence для трекинга

# Уведомления
PERFORMANCE_NOTIFY_ON_MILESTONES = int(os.getenv('PERFORMANCE_NOTIFY_ON_MILESTONES', '1')) == 1
PERFORMANCE_MILESTONE_SIGNALS = [int(x) for x in os.getenv('PERFORMANCE_MILESTONE_SIGNALS', '10,50,100,500').split(',')]

# Автоматическая обратная связь в систему
PERFORMANCE_ENABLE_AUTO_FEEDBACK = int(os.getenv('PERFORMANCE_ENABLE_AUTO_FEEDBACK', '1')) == 1

# ============================================================================
# НОВОЕ: ADAPTIVE THRESHOLDS (Динамические пороги)
# ============================================================================

# Главный переключатель
ADAPTIVE_THRESHOLDS_ENABLED = int(os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', '1')) == 1

# Базовые значения (отправная точка)
ADAPTIVE_BASE_MIN_CONFIDENCE = int(os.getenv('ADAPTIVE_BASE_MIN_CONFIDENCE', '70'))  # повышено с 30
ADAPTIVE_BASE_MIN_SIZE_REL = float(os.getenv('ADAPTIVE_BASE_MIN_SIZE_REL', '0.01'))  # снижено с 0.10
ADAPTIVE_BASE_MIN_VOLUME_24H = float(os.getenv('ADAPTIVE_BASE_MIN_VOLUME_24H', '1000000'))  # $1M

# Market Regime Detection
ADAPTIVE_BULL_THRESHOLD = float(os.getenv('ADAPTIVE_BULL_THRESHOLD', '10.0'))  # BTC +10% за неделю
ADAPTIVE_BEAR_THRESHOLD = float(os.getenv('ADAPTIVE_BEAR_THRESHOLD', '-10.0'))  # BTC -10% за неделю
ADAPTIVE_MARKET_REGIME_UPDATE_HOURS = int(os.getenv('ADAPTIVE_MARKET_REGIME_UPDATE_HOURS', '6'))

# Модификаторы для бычьего рынка
ADAPTIVE_BULL_CONFIDENCE_MODIFIER = int(os.getenv('ADAPTIVE_BULL_CONFIDENCE_MODIFIER', '-5'))  # снижаем порог
ADAPTIVE_BULL_SIZE_REL_MODIFIER = float(os.getenv('ADAPTIVE_BULL_SIZE_REL_MODIFIER', '-0.02'))  # -2%
ADAPTIVE_BULL_VOLUME_MODIFIER = float(os.getenv('ADAPTIVE_BULL_VOLUME_MODIFIER', '0.8'))  # x0.8

# Модификаторы для медвежьего рынка
ADAPTIVE_BEAR_CONFIDENCE_MODIFIER = int(os.getenv('ADAPTIVE_BEAR_CONFIDENCE_MODIFIER', '+10'))  # повышаем порог
ADAPTIVE_BEAR_SIZE_REL_MODIFIER = float(os.getenv('ADAPTIVE_BEAR_SIZE_REL_MODIFIER', '+0.05'))  # +5%
ADAPTIVE_BEAR_VOLUME_MODIFIER = float(os.getenv('ADAPTIVE_BEAR_VOLUME_MODIFIER', '1.5'))  # x1.5

# Адаптация на основе производительности
ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION = int(os.getenv('ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION', '20'))  # минимум сигналов
ADAPTIVE_LOW_ACCURACY_THRESHOLD = float(os.getenv('ADAPTIVE_LOW_ACCURACY_THRESHOLD', '0.40'))  # 40%
ADAPTIVE_HIGH_ACCURACY_THRESHOLD = float(os.getenv('ADAPTIVE_HIGH_ACCURACY_THRESHOLD', '0.65'))  # 65%
ADAPTIVE_ACCURACY_ADJUSTMENT = int(os.getenv('ADAPTIVE_ACCURACY_ADJUSTMENT', '5'))  # ±5 к порогам

# ============================================================================
# НОВОЕ: LEARNING SYSTEM (Система самообучения)
# ============================================================================

# Главный переключатель
LEARNING_SYSTEM_ENABLED = int(os.getenv('LEARNING_SYSTEM_ENABLED', '1')) == 1

# Что учить
LEARNING_ENABLE_WALLET_SCORING = int(os.getenv('LEARNING_ENABLE_WALLET_SCORING', '1')) == 1
LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS = int(os.getenv('LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS', '1')) == 1
LEARNING_ENABLE_PATTERN_DETECTION = int(os.getenv('LEARNING_ENABLE_PATTERN_DETECTION', '1')) == 1

# Параметры обучения
LEARNING_RATE = float(os.getenv('LEARNING_RATE', '0.1'))  # скорость обучения
LEARNING_MIN_SAMPLES = int(os.getenv('LEARNING_MIN_SAMPLES', '30'))  # минимум данных для обучения
LEARNING_WINDOW_DAYS = int(os.getenv('LEARNING_WINDOW_DAYS', '30'))  # окно данных

# Начальные веса типов сигналов
LEARNING_SIGNAL_TYPE_WEIGHTS = {
    'large_buy': float(os.getenv('LEARNING_WEIGHT_LARGE_BUY', '1.0')),
    'accumulation': float(os.getenv('LEARNING_WEIGHT_ACCUMULATION', '1.2')),
    'new_wallet': float(os.getenv('LEARNING_WEIGHT_NEW_WALLET', '0.8')),
    'dex_listing': float(os.getenv('LEARNING_WEIGHT_DEX_LISTING', '0.9')),
    'whale_transfer': float(os.getenv('LEARNING_WEIGHT_WHALE_TRANSFER', '1.0')),
}

# Сохранение моделей
LEARNING_SAVE_MODELS = int(os.getenv('LEARNING_SAVE_MODELS', '1')) == 1
LEARNING_MODEL_UPDATE_INTERVAL_HOURS = int(os.getenv('LEARNING_MODEL_UPDATE_INTERVAL_HOURS', '24'))

# ============================================================================
# WALLET DATABASE
# ============================================================================

# Тип базы данных
WALLET_DB_TYPE = os.getenv('WALLET_DB_TYPE', 'json')  # 'json' или 'sqlite'
WALLET_DB_JSON_PATH = os.getenv('WALLET_DB_JSON_PATH', 'data/wallets.json')
WALLET_DB_SQLITE_PATH = os.getenv('WALLET_DB_SQLITE_PATH', 'data/wallets.db')

# Система оценки кошельков
WALLET_BASE_SCORE = int(os.getenv('WALLET_BASE_SCORE', '50'))  # начальный скор (переименовано из WALLET_INITIAL_SCORE)
WALLET_INITIAL_SCORE = WALLET_BASE_SCORE  # алиас для совместимости
WALLET_MIN_SCORE = int(os.getenv('WALLET_MIN_SCORE', '0'))
WALLET_MAX_SCORE = int(os.getenv('WALLET_MAX_SCORE', '100'))

# Обновление скора
WALLET_SCORE_UPDATE_ON_SUCCESS = int(os.getenv('WALLET_SCORE_UPDATE_ON_SUCCESS', '+5'))
WALLET_SCORE_UPDATE_ON_FAILURE = int(os.getenv('WALLET_SCORE_UPDATE_ON_FAILURE', '-3'))
WALLET_SCORE_DECAY_PER_DAY = float(os.getenv('WALLET_SCORE_DECAY_PER_DAY', '1.0'))  # естественная деградация

# Лимиты
WALLET_MAX_TRACKED = int(os.getenv('WALLET_MAX_TRACKED', '500'))  # максимум кошельков
WALLET_AUTO_PRUNE = int(os.getenv('WALLET_AUTO_PRUNE', '1')) == 1  # автоудаление худших

# ============================================================================
# API КЛЮЧИ И ДОСТУПЫ
# ============================================================================

# Blockchain explorers
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', ETHERSCAN_API_KEY)
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
TRONSCAN_API_KEY = os.getenv('TRONSCAN_API_KEY', '')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')

# Multi-chain API keys
BASE_API_KEY = os.getenv('BASE_API_KEY', ETHERSCAN_API_KEY)
BASESCAN_API_KEY = BASE_API_KEY  # алиас
ARBITRUM_API_KEY = os.getenv('ARBITRUM_API_KEY', ETHERSCAN_API_KEY)
ARBISCAN_API_KEY = ARBITRUM_API_KEY  # алиас
OPTIMISM_API_KEY = os.getenv('OPTIMISM_API_KEY', ETHERSCAN_API_KEY)
AVALANCHE_API_KEY = os.getenv('AVALANCHE_API_KEY', '')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
POLYGONSCAN_API_KEY = POLYGON_API_KEY  # алиас

# RPC endpoints
ETH_RPC_URL = os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
ETH_RPC_BACKUP = os.getenv('ETH_RPC_BACKUP', 'https://rpc.ankr.com/eth')

BSC_RPC_URL = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
BSC_RPC_BACKUP = os.getenv('BSC_RPC_BACKUP', 'https://rpc.ankr.com/bsc')

SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
SOLANA_RPC_URLS = os.getenv('SOLANA_RPC_URLS', SOLANA_RPC_URL).split(',')
SOLANA_RPC_BACKUP = os.getenv('SOLANA_RPC_BACKUP', 'https://rpc.ankr.com/solana')

TRON_RPC_URL = os.getenv('TRON_RPC_URL', 'https://api.trongrid.io')

BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')

ARBITRUM_RPC_URL = os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc')

POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')

ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', '')

# Рыночные данные
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', '')

# AI сервисы
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Новости
CRYPTOPANIC_KEY = os.getenv('CRYPTOPANIC_KEY', '')
NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')

# ============================================================================
# CHAINS CONFIGURATION
# ============================================================================

CHAINS_ENABLED = os.getenv('CHAINS_ENABLED', 'true').lower() == 'true'
ENABLED_CHAINS = [c.strip() for c in os.getenv('ENABLED_CHAINS', 'ethereum,bsc,solana,tron,base,arbitrum,polygon').split(',') if c.strip()]

# ============================================================================
# ANALYTICS
# ============================================================================

ANALYTICS_ENABLED = os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true'

# ============================================================================
# ФАЙЛОВАЯ СИСТЕМА
# ============================================================================

# Базовые директории
DATA_DIR = os.getenv('DATA_DIR', 'data')
STATE_FILE = os.path.join(DATA_DIR, 'state.json')

# History директория (для Whale Scheduler)
HISTORY_DIR = os.path.join(DATA_DIR, 'history')

# Learning System директории
LEARNING_DIR = os.path.join(DATA_DIR, 'learning')
LEARNING_MODELS_DIR = os.path.join(LEARNING_DIR, 'models')
LEARNING_HISTORY_DIR = os.path.join(LEARNING_DIR, 'history')

# Wallet директории
WALLETS_DIR = os.path.join(DATA_DIR, 'wallets')
POSITIONS_DIR = os.path.join(DATA_DIR, 'positions')
PERFORMANCE_DIR = os.path.join(DATA_DIR, 'performance')

# Создание директорий
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(LEARNING_DIR, exist_ok=True)
os.makedirs(LEARNING_MODELS_DIR, exist_ok=True)
os.makedirs(LEARNING_HISTORY_DIR, exist_ok=True)
os.makedirs(WALLETS_DIR, exist_ok=True)
os.makedirs(POSITIONS_DIR, exist_ok=True)
os.makedirs(PERFORMANCE_DIR, exist_ok=True)

# ============================================================================
# ВАЛИДАЦИЯ КОНФИГУРАЦИИ
# ============================================================================

def validate_config():
    """Проверяет корректность настроек и выводит предупреждения"""
    
    warnings = []
    
    # Проверка критичных параметров для production
    if HTTP_TIMEOUT < 10:
        warnings.append(f"HTTP_TIMEOUT ({HTTP_TIMEOUT}s) очень низкий, рекомендуется >= 10s")
    
    if RPC_TIMEOUT < 5:
        warnings.append(f"RPC_TIMEOUT ({RPC_TIMEOUT}s) очень низкий, рекомендуется >= 5s")
    
    if MAX_MEMORY_MB > 480:
        warnings.append(f"MAX_MEMORY_MB ({MAX_MEMORY_MB}MB) близко к лимиту Render Free (512MB)")
    
    # Проверка API ключей
    if not ETHERSCAN_API_KEY:
        warnings.append("ETHERSCAN_API_KEY не установлен - мониторинг Ethereum ограничен")
    
    if not HELIUS_API_KEY and not SOLSCAN_API_KEY:
        warnings.append("HELIUS_API_KEY и SOLSCAN_API_KEY не установлены - мониторинг Solana ограничен")
    
    if not COINGECKO_API_KEY:
        warnings.append("COINGECKO_API_KEY не установлен - ограничена информация о ценах")
    
    # Проверка настроек Trading System
    if TRADING_ENABLED:
        if TRADING_MIN_CONFIDENCE > 90:
            warnings.append(f"TRADING_MIN_CONFIDENCE очень высокий ({TRADING_MIN_CONFIDENCE}) - может быть мало сигналов")
        
        if TRADING_MAX_SIGNALS_PER_DAY < 3:
            warnings.append(f"TRADING_MAX_SIGNALS_PER_DAY очень низкий ({TRADING_MAX_SIGNALS_PER_DAY})")
        
        if not TRADING_DRY_RUN:
            warnings.append("⚠️ TRADING_DRY_RUN=false - система в БОЕВОМ режиме!")
    
    # Проверка Smart Discovery
    if SMART_DISCOVERY_ENABLED:
        if SMART_DISCOVERY_MIN_WALLET_ROI < 0.5:
            warnings.append(f"SMART_DISCOVERY_MIN_WALLET_ROI низкий ({SMART_DISCOVERY_MIN_WALLET_ROI}) - может быть много ложных срабатываний")
        
        if SMART_DISCOVERY_MAX_NEW_WALLETS > 20:
            warnings.append(f"SMART_DISCOVERY_MAX_NEW_WALLETS высокий ({SMART_DISCOVERY_MAX_NEW_WALLETS}) - база будет быстро расти")
    
    # Проверка Adaptive Thresholds
    if ADAPTIVE_THRESHOLDS_ENABLED:
        if ADAPTIVE_BASE_MIN_CONFIDENCE < 20:
            warnings.append(f"ADAPTIVE_BASE_MIN_CONFIDENCE очень низкий ({ADAPTIVE_BASE_MIN_CONFIDENCE}) - много шума")
        
        if ADAPTIVE_BASE_MIN_CONFIDENCE > 70:
            warnings.append(f"ADAPTIVE_BASE_MIN_CONFIDENCE очень высокий ({ADAPTIVE_BASE_MIN_CONFIDENCE}) - мало сигналов")
    
    # Проверка Learning System
    if LEARNING_SYSTEM_ENABLED:
        if LEARNING_RATE > 0.5:
            warnings.append(f"LEARNING_RATE очень высокий ({LEARNING_RATE}) - система может быть нестабильной")
        
        if LEARNING_MIN_SAMPLES < 10:
            warnings.append(f"LEARNING_MIN_SAMPLES слишком мал ({LEARNING_MIN_SAMPLES}) - ненадёжное обучение")
    
    # Проверка Wallet Database
    if WALLET_MAX_TRACKED > 1000:
        warnings.append(f"WALLET_MAX_TRACKED очень большой ({WALLET_MAX_TRACKED}) - может быть медленно")
    
    # Проверка Performance Tracking
    if PERFORMANCE_TRACKING_ENABLED:
        if PERFORMANCE_HISTORY_SIZE > 5000:
            warnings.append(f"PERFORMANCE_HISTORY_SIZE очень большой ({PERFORMANCE_HISTORY_SIZE}) - может замедлить работу")
    
    # Проверка News Processor
    if NEWS_PROCESSOR_ENABLED:
        if NEWS_AUTO_TRANSLATE and not (GOOGLE_CLOUD_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS):
            warnings.append("NEWS_AUTO_TRANSLATE включен, но Google Cloud не настроен - переводы будут недоступны")
    
    # Проверка Watchlist
    if WATCHLIST_ENABLED:
        if WATCHLIST_MAX_SIZE > 500:
            warnings.append(f"WATCHLIST_MAX_SIZE очень большой ({WATCHLIST_MAX_SIZE})")
    
    # Проверка валюты
    if MIN_USD < 10000:
        warnings.append(f"MIN_USD очень низкий ({MIN_USD}) - будет много шума")
    
    # Проверка интервала опроса (с поправкой на новые значения)
    if POLL_SECONDS < 5:
        warnings.append(f"POLL_SECONDS очень низкий ({POLL_SECONDS}) - может привести к rate limiting")
    
    return warnings


def print_config():
    """Красиво выводит текущую конфигурацию"""
    warnings = validate_config()
    
    print("=" * 80)
    print("⚙️  КОНФИГУРАЦИЯ СИСТЕМЫ v4.0")
    print("=" * 80)
    
    # ========================================================================
    # PRODUCTION SETTINGS (НОВОЕ v4.0)
    # ========================================================================
    print(f"\n🚀 PRODUCTION\n")
    print(f"  • HTTP Port: {PORT}")
    print(f"  • HTTP Timeout: {HTTP_TIMEOUT}s")
    print(f"  • RPC Timeout: {RPC_TIMEOUT}s")
    print(f"  • Webhook Timeout: {WEBHOOK_TIMEOUT}s")
    print(f"  • Max Memory: {MAX_MEMORY_MB}MB")
    print(f"  • GC Interval: {GC_INTERVAL_SECONDS}s")
    print(f"  • Max Connections: {HTTP_MAX_CONNECTIONS}")
    print(f"  • Whale Enabled: {'✅' if WHALE_ENABLED else '❌'}")
    print(f"  • News Enabled: {'✅' if NEWS_ENABLED else '❌'}")
    
    # ========================================================================
    # НОВЫЕ ФУНКЦИИ v3.0
    # ========================================================================
    print(f"\n✨ SMART FEATURES v3.0+\n")
    
    # Trading System
    print(f"  📈 Trading System:")
    if TRADING_ENABLED:
        print(f"     • Status: ✅ Включен {'(DRY RUN)' if TRADING_DRY_RUN else '(LIVE)'}")
        print(f"     • Минимальная confidence: {TRADING_MIN_CONFIDENCE}%")
        print(f"     • Макс. сигналов/день: {TRADING_MAX_SIGNALS_PER_DAY}")
        print(f"     • Cooldown: {TRADING_SIGNAL_COOLDOWN_MINUTES} мин")
        print(f"     • Stop Loss: {TRADING_DEFAULT_STOP_LOSS_PERCENT}%")
        print(f"     • Take Profit: {TRADING_DEFAULT_TAKE_PROFIT_PERCENT}%")
        print(f"     • Макс. позиций: {TRADING_MAX_OPEN_POSITIONS}")
        print(f"     • Размер позиции: ${TRADING_MAX_POSITION_SIZE_USD:,.0f}")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Smart Discovery
    print(f"\n  🔍 Smart Money Discovery:")
    if SMART_DISCOVERY_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Интервал: каждые {SMART_DISCOVERY_INTERVAL_HOURS}ч")
        print(f"     • Минимальный рост цены: {SMART_DISCOVERY_MIN_PRICE_CHANGE}x")
        print(f"     • Топ токенов для анализа: {SMART_DISCOVERY_MAX_TOKENS_TO_ANALYZE}")
        print(f"     • Минимальный ROI кошелька: {SMART_DISCOVERY_MIN_WALLET_ROI*100:.0f}%")
        print(f"     • Минимальный win rate: {SMART_DISCOVERY_MIN_WIN_RATE*100:.0f}%")
        print(f"     • Макс. новых кошельков/запуск: {SMART_DISCOVERY_MAX_NEW_WALLETS}")
        print(f"     • История: {SMART_DISCOVERY_LOOKBACK_DAYS} дней")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Validation Engine
    print(f"\n  🧹 Validation Engine:")
    if VALIDATION_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Интервал: каждые {VALIDATION_INTERVAL_DAYS} дней")
        print(f"     • Макс. неактивность: {VALIDATION_MAX_INACTIVE_DAYS} дней")
        print(f"     • Минимальный скор: {VALIDATION_MIN_SCORE_TO_KEEP}/100")
        print(f"     • Минимум сделок: {VALIDATION_MIN_TRADES_TO_KEEP}")
        print(f"     • Минимальный win rate: {VALIDATION_MIN_WIN_RATE_TO_KEEP*100:.0f}%")
        print(f"     • Уведомления: {'да' if VALIDATION_NOTIFY_ON_REMOVAL else 'нет'}")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Performance Tracking
    print(f"\n  📊 Performance Tracking:")
    if PERFORMANCE_TRACKING_ENABLED:
        print(f"     • Status: ✅ Включен")
        intervals_str = ", ".join([f"{i}ч" for i in PERFORMANCE_CHECK_INTERVALS])
        print(f"     • Интервалы проверки: {intervals_str}")
        print(f"     • Размер истории: {PERFORMANCE_HISTORY_SIZE} сигналов")
        print(f"     • Период анализа: {PERFORMANCE_LOOKBACK_DAYS} дней")
        print(f"     • Порог успеха: {PERFORMANCE_SUCCESS_THRESHOLD*100:.0f}%")
        print(f"     • Уведомления: {'да' if PERFORMANCE_NOTIFY_ON_MILESTONES else 'нет'}")
        print(f"     • Авто-обратная связь: {'да' if PERFORMANCE_ENABLE_AUTO_FEEDBACK else 'нет'}")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Adaptive Thresholds
    print(f"\n  🎯 Adaptive Thresholds:")
    if ADAPTIVE_THRESHOLDS_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Базовая confidence: {ADAPTIVE_BASE_MIN_CONFIDENCE}%")
        print(f"     • Базовый size_rel: {ADAPTIVE_BASE_MIN_SIZE_REL*100:.0f}%")
        print(f"     • Базовый volume: ${ADAPTIVE_BASE_MIN_VOLUME_24H:,.0f}")
        print(f"     • Bull threshold: BTC {ADAPTIVE_BULL_THRESHOLD:+.0f}%")
        print(f"     • Bear threshold: BTC {ADAPTIVE_BEAR_THRESHOLD:+.0f}%")
        print(f"     • Обновление режима: каждые {ADAPTIVE_MARKET_REGIME_UPDATE_HOURS}ч")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Learning System
    print(f"\n  🧠 Learning System:")
    if LEARNING_SYSTEM_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Wallet Scoring: {'да' if LEARNING_ENABLE_WALLET_SCORING else 'нет'}")
        print(f"     • Signal Type Weights: {'да' if LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS else 'нет'}")
        print(f"     • Pattern Detection: {'да' if LEARNING_ENABLE_PATTERN_DETECTION else 'нет'}")
        print(f"     • Learning Rate: {LEARNING_RATE}")
        print(f"     • Мин. данных: {LEARNING_MIN_SAMPLES} сигналов")
        print(f"     • Окно обучения: {LEARNING_WINDOW_DAYS} дней")
        print(f"     • Начальные веса:")
        for signal_type, weight in LEARNING_SIGNAL_TYPE_WEIGHTS.items():
            print(f"       - {signal_type}: {weight:.1f}")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # News Processor
    print(f"\n  📰 News Processor:")
    if NEWS_PROCESSOR_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Интервал: каждые {NEWS_CHECK_INTERVAL_MINUTES} мин")
        print(f"     • Максимальный возраст: {NEWS_MAX_AGE_HOURS}ч")
        print(f"     • Мин. impact score: {NEWS_MIN_IMPACT_SCORE}/10")
        print(f"     • Источники: {', '.join(NEWS_SOURCES)}")
        print(f"     • Sentiment Analysis: {'да' if NEWS_SENTIMENT_ANALYSIS_ENABLED else 'нет'}")
        print(f"     • Auto Translate: {'да' if NEWS_AUTO_TRANSLATE else 'нет'}")
        if NEWS_AUTO_TRANSLATE:
            print(f"     • Target Language: {NEWS_TARGET_LANGUAGE}")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Watchlist
    print(f"\n  📋 Watchlist:")
    if WATCHLIST_ENABLED:
        print(f"     • Status: ✅ Включен")
        print(f"     • Файл: {WATCHLIST_FILE}")
        print(f"     • Макс. размер: {WATCHLIST_MAX_SIZE}")
        print(f"     • Авто-добавление: {'да' if WATCHLIST_AUTO_ADD_TOP_PERFORMERS else 'нет'}")
        if WATCHLIST_AUTO_ADD_TOP_PERFORMERS:
            print(f"     • Мин. performance: {WATCHLIST_MIN_PERFORMANCE_TO_ADD*100:.0f}%")
    else:
        print(f"     • Status: ❌ Отключен")
    
    # Wallet Database
    print(f"\n  💾 Wallet Database:")
    print(f"     • Тип: {WALLET_DB_TYPE.upper()}")
    print(f"     • Начальный скор: {WALLET_BASE_SCORE}/100")
    print(f"     • Успех/провал: {WALLET_SCORE_UPDATE_ON_SUCCESS:+d}/{WALLET_SCORE_UPDATE_ON_FAILURE:+d}")
    print(f"     • Деградация: -{WALLET_SCORE_DECAY_PER_DAY}/день")
    print(f"     • Макс. кошельков: {WALLET_MAX_TRACKED}")
    print(f"     • Автоудаление: {'да' if WALLET_AUTO_PRUNE else 'нет'}")
    
    # ========================================================================
    # СТАНДАРТНЫЕ РАЗДЕЛЫ
    # ========================================================================
    print(f"\n📡 МОНИТОРИНГ")
    print(f"  • Интервал опроса: {POLL_SECONDS}с")
    print(f"  • Начать с: {START_FROM_MINUTES_AGO} минут назад")
    
    print(f"\n🔔 АЛЕРТЫ")
    if ENABLE_ALERTS:
        print(f"  • Статус: ✅ Включены")
        if ADMIN_CHAT_ID != CHAT_ID:
            print(f"  • Админ ID: {ADMIN_CHAT_ID[:4]}...{ADMIN_CHAT_ID[-4:]}")
        else:
            print(f"  • Админ ID: не настроен (→ публичный канал)")
        print(f"  • Cooldown: {ALERT_COOLDOWN_SECONDS}с")
        print(f"  • Уведомление о запуске: {'да' if SEND_STARTUP_NOTIFICATION else 'нет'}")
        print(f"  • Ежедневная статистика: {'да' if SEND_DAILY_STATS else 'нет'}")
    else:
        print(f"  • Статус: ❌ Отключены")
    
    print(f"\n⚡ ЗАЩИТА ОТ ПЕРЕГРУЗКИ")
    print(f"  • Rate Limiting: {'включен' if RATE_LIMIT_ENABLED else 'выключен'}")
    if RATE_LIMIT_ENABLED:
        print(f"  • Лимит: {RATE_LIMIT_CALLS} запросов / {RATE_LIMIT_PERIOD}с")
    print(f"  • Retry: до {RETRY_MAX_ATTEMPTS} попыток с backoff x{RETRY_BACKOFF_FACTOR}")
    print(f"  • Timeout: {RETRY_TIMEOUT}с")
    print(f"  • Health Check: {'включен' if HEALTH_CHECK_ENABLED else 'выключен'}")
    
    print(f"\n📈 ДОПОЛНИТЕЛЬНО")
    print(f"  • Графики: {'включены' if ENABLE_IMAGES else 'выключены'}")
    print(f"  • Debug фильтров: {'включен' if DEBUG_FILTERS else 'выключен'}")
    print(f"  • Log level: {LOG_LEVEL}")
    
    # API ключи
    print(f"\n🔑 API КЛЮЧИ")
    api_keys = {
        "Etherscan": ETHERSCAN_API_KEY,
        "Helius (Solana)": HELIUS_API_KEY,
        "TronScan": TRONSCAN_API_KEY,
        "CoinGecko": COINGECKO_API_KEY,
        "Alchemy": ALCHEMY_API_KEY,
        "CoinMarketCap": COINMARKETCAP_API_KEY,
        "Gemini AI": GEMINI_API_KEY,
        "OpenAI": OPENAI_API_KEY,
        "CryptoPanic": CRYPTOPANIC_KEY,
        "NewsAPI": NEWS_API_KEY,
        "Google Cloud": GOOGLE_CLOUD_PROJECT_ID,
    }
    for name, key in api_keys.items():
        status = "✅" if key else "❌"
        print(f"  • {name}: {status}")
    
    # Bot Commands
    print(f"\n🤖 BOT COMMANDS")
    if BOT_TOKEN:
        print(f"  • Status: ✅ Enabled")
        print(f"  • Bot Token: {'✅ Configured' if BOT_TOKEN == TELEGRAM_BOT_TOKEN else '✅ Separate token'}")
    else:
        print(f"  • Status: ❌ Disabled (BOT_TOKEN not set)")
    
    print("=" * 80)
    
    # Предупреждения
    if warnings:
        print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print(f"  • {w}")
        print()
    
    # Итоговая сводка
    enabled_systems = []
    if TRADING_ENABLED:
        enabled_systems.append("Trading System")
    if SMART_DISCOVERY_ENABLED:
        enabled_systems.append("Smart Discovery")
    if VALIDATION_ENABLED:
        enabled_systems.append("Validation")
    if PERFORMANCE_TRACKING_ENABLED:
        enabled_systems.append("Performance Tracking")
    if ADAPTIVE_THRESHOLDS_ENABLED:
        enabled_systems.append("Adaptive Thresholds")
    if LEARNING_SYSTEM_ENABLED:
        enabled_systems.append("Learning System")
    if NEWS_PROCESSOR_ENABLED:
        enabled_systems.append("News Processor")
    if WATCHLIST_ENABLED:
        enabled_systems.append("Watchlist")
    if BOT_TOKEN:
        enabled_systems.append("Bot Commands")
    
    if enabled_systems:
        print(f"✅ Активные системы: {', '.join(enabled_systems)}")
        print(f"🎯 Система работает в ИНТЕЛЛЕКТУАЛЬНОМ режиме")
    else:
        print(f"⚠️  Все интеллектуальные системы отключены")
        print(f"🎯 Система работает в БАЗОВОМ режиме")
    
    print()


def get_environment_info():
    """Возвращает информацию об окружении для отладки"""
    return {
        "render": bool(os.environ.get('RENDER')),
        "render_service": os.environ.get('RENDER_SERVICE_NAME', 'N/A'),
        "python_version": os.environ.get('PYTHON_VERSION', 'N/A'),
        "has_disk": bool(os.environ.get('RENDER_DISK_MOUNT_PATH')),
        "disk_path": os.environ.get('RENDER_DISK_MOUNT_PATH', 'N/A'),
        "data_dir": DATA_DIR,
        "learning_dir": LEARNING_DIR,
        "port": PORT,
        "max_memory_mb": MAX_MEMORY_MB,
    }


def get_all_settings() -> Dict:
    """Возвращает все настройки в виде словаря (для экспорта/бэкапа)"""
    return {
        "version": "4.0",
        "timestamp": datetime.utcnow().isoformat(),
        "production": {
            "port": PORT,
            "http_timeout": HTTP_TIMEOUT,
            "rpc_timeout": RPC_TIMEOUT,
            "max_memory_mb": MAX_MEMORY_MB,
            "whale_enabled": WHALE_ENABLED,
            "news_enabled": NEWS_ENABLED,
        },
        "general": {
            "assets": ASSETS,
            "poll_seconds": POLL_SECONDS,
            "posts_per_hour": POSTS_PER_HOUR_CAP,
        },
        "trading_system": {
            "enabled": TRADING_ENABLED,
            "min_confidence": TRADING_MIN_CONFIDENCE,
            "max_signals_per_day": TRADING_MAX_SIGNALS_PER_DAY,
            "dry_run": TRADING_DRY_RUN,
        },
        "smart_discovery": {
            "enabled": SMART_DISCOVERY_ENABLED,
            "interval_hours": SMART_DISCOVERY_INTERVAL_HOURS,
            "min_price_change": SMART_DISCOVERY_MIN_PRICE_CHANGE,
            "min_wallet_roi": SMART_DISCOVERY_MIN_WALLET_ROI,
            "min_win_rate": SMART_DISCOVERY_MIN_WIN_RATE,
        },
        "validation": {
            "enabled": VALIDATION_ENABLED,
            "interval_days": VALIDATION_INTERVAL_DAYS,
            "max_inactive_days": VALIDATION_MAX_INACTIVE_DAYS,
            "min_score": VALIDATION_MIN_SCORE_TO_KEEP,
        },
        "performance_tracking": {
            "enabled": PERFORMANCE_TRACKING_ENABLED,
            "check_intervals": PERFORMANCE_CHECK_INTERVALS,
            "history_size": PERFORMANCE_HISTORY_SIZE,
        },
        "adaptive_thresholds": {
            "enabled": ADAPTIVE_THRESHOLDS_ENABLED,
            "base_confidence": ADAPTIVE_BASE_MIN_CONFIDENCE,
            "base_size_rel": ADAPTIVE_BASE_MIN_SIZE_REL,
            "base_volume": ADAPTIVE_BASE_MIN_VOLUME_24H,
        },
        "learning_system": {
            "enabled": LEARNING_SYSTEM_ENABLED,
            "learning_rate": LEARNING_RATE,
            "signal_type_weights": LEARNING_SIGNAL_TYPE_WEIGHTS,
        },
        "news_processor": {
            "enabled": NEWS_PROCESSOR_ENABLED,
            "interval_minutes": NEWS_CHECK_INTERVAL_MINUTES,
            "min_impact_score": NEWS_MIN_IMPACT_SCORE,
            "sources": NEWS_SOURCES,
        },
        "watchlist": {
            "enabled": WATCHLIST_ENABLED,
            "file": WATCHLIST_FILE,
            "max_size": WATCHLIST_MAX_SIZE,
            "auto_add": WATCHLIST_AUTO_ADD_TOP_PERFORMERS,
        },
        "bot_commands": {
            "enabled": bool(BOT_TOKEN),
        }
    }


# Запуск валидации
validate_config()