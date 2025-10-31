# app/settings.py (РЕВОЛЮЦИОННАЯ ВЕРСИЯ v3.0 - Self-Learning System)
"""
INTELLIGENT CRYPTO MONITOR - Configuration

НОВЫЕ ВОЗМОЖНОСТИ v3.0:
✅ Smart Money Discovery - настройки автопоиска трейдеров
✅ Validation Engine - параметры очистки базы
✅ Performance Tracking - отслеживание результатов
✅ Adaptive Thresholds - динамические пороги
✅ Learning System - параметры самообучения
✅ Market Regime Detection - определение bull/bear
✅ Trading System - генерация торговых сигналов
"""

import os
from dotenv import load_dotenv
from typing import List, Optional, Dict
from datetime import datetime

load_dotenv()

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
# WHALE MONITOR - ОСНОВНЫЕ ПАРАМЕТРЫ
# ============================================================================
ASSETS = os.getenv('ASSETS', '*')
ASSETS_LIST = [] if ASSETS == '*' else [a.strip() for a in ASSETS.split(',') if a.strip()]

# Базовые пороги
MIN_USD = float(os.getenv('MIN_USD', '500000'))
MIN_USD_FLOOR = float(os.getenv('MIN_USD_FLOOR', '50000'))
MIN_USD_K = float(os.getenv('MIN_USD_K', '0.02'))
MIN_USD_PCTL = float(os.getenv('MIN_USD_PCTL', '75'))

# Временные параметры
POLL_SECONDS = int(os.getenv('POLL_SECONDS', '180'))
START_FROM_MINUTES_AGO = int(os.getenv('START_FROM_MINUTES_AGO', '90'))

# Discovery параметры
DISCOVERY_TOP_N_PER_CHAIN = int(os.getenv('DISCOVERY_TOP_N_PER_CHAIN', '200'))
DISCOVERY_REFRESH_HOURS = int(os.getenv('DISCOVERY_REFRESH_HOURS', '12'))
DISCOVERY_BLACKLIST = [b.strip() for b in os.getenv('DISCOVERY_BLACKLIST', '').split(',') if b.strip()]
MIN_TOKEN_AGE_DAYS = int(os.getenv('MIN_TOKEN_AGE_DAYS', '7'))

# Лимиты публикаций
POSTS_PER_HOUR_CAP = int(os.getenv('POSTS_PER_HOUR_CAP', '6'))

# Визуализация
ENABLE_IMAGES = int(os.getenv('ENABLE_IMAGES', '1')) == 1
CHART_BACKEND = os.getenv('CHART_BACKEND', 'sparkline')
CHART_THEME = os.getenv('CHART_THEME', 'dark')
CHART_WIDTH = int(os.getenv('CHART_WIDTH', '800'))
CHART_HEIGHT = int(os.getenv('CHART_HEIGHT', '600'))
EXCHANGE_PREFERENCE = [e.strip() for e in os.getenv('EXCHANGE_PREFERENCE', 'binance,okx,bybit,coinbase').split(',')]

# Логирование
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DEBUG_FILTERS = int(os.getenv('DEBUG_FILTERS', '1')) == 1

# Настройки алертов
ENABLE_ALERTS = int(os.getenv('ENABLE_ALERTS', '1')) == 1
ALERT_COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', '300'))
SEND_STARTUP_NOTIFICATION = int(os.getenv('SEND_STARTUP_NOTIFICATION', '1')) == 1
SEND_DAILY_STATS = int(os.getenv('SEND_DAILY_STATS', '1')) == 1

# Rate Limiting
RATE_LIMIT_ENABLED = int(os.getenv('RATE_LIMIT_ENABLED', '1')) == 1
RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '5'))
RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '60'))

# Retry настройки
RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
RETRY_BACKOFF_FACTOR = int(os.getenv('RETRY_BACKOFF_FACTOR', '2'))
RETRY_TIMEOUT = int(os.getenv('RETRY_TIMEOUT', '30'))

# Health Check
HEALTH_CHECK_ENABLED = int(os.getenv('HEALTH_CHECK_ENABLED', '1')) == 1
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))
HEALTH_CHECK_MAX_SILENCE = int(os.getenv('HEALTH_CHECK_MAX_SILENCE', '600'))

# ============================================================================
# TRADING SYSTEM
# ============================================================================

# Главный переключатель Trading System
TRADING_ENABLED = os.getenv('TRADING_ENABLED', 'false').lower() == 'true'

# Настройки торговых сигналов
TRADING_MIN_CONFIDENCE = int(os.getenv('TRADING_MIN_CONFIDENCE', '70'))
TRADING_MAX_SIGNALS_PER_DAY = int(os.getenv('TRADING_MAX_SIGNALS_PER_DAY', '10'))
TRADING_SIGNAL_COOLDOWN_MINUTES = int(os.getenv('TRADING_SIGNAL_COOLDOWN_MINUTES', '60'))

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
TRADING_DRY_RUN = os.getenv('TRADING_DRY_RUN', 'false').lower() == 'true'

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
VALIDATION_MAX_INACTIVE_DAYS = int(os.getenv('VALIDATION_MAX_INACTIVE_DAYS', '60'))  # 60 дней без активности
VALIDATION_MIN_SCORE_TO_KEEP = int(os.getenv('VALIDATION_MIN_SCORE_TO_KEEP', '30'))  # минимальный скор
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

# Интервалы проверки (часы)
PERFORMANCE_CHECK_INTERVALS = [
    int(x) for x in os.getenv('PERFORMANCE_CHECK_INTERVALS', '1,6,24').split(',')
]  # [1, 6, 24] часа

# Критерии успешности
PERFORMANCE_SUCCESS_THRESHOLD_BULLISH = float(os.getenv('PERFORMANCE_SUCCESS_THRESHOLD_BULLISH', '0.02'))  # +2%
PERFORMANCE_SUCCESS_THRESHOLD_BEARISH = float(os.getenv('PERFORMANCE_SUCCESS_THRESHOLD_BEARISH', '-0.02'))  # -2%

# Размер истории
PERFORMANCE_HISTORY_SIZE = int(os.getenv('PERFORMANCE_HISTORY_SIZE', '200'))  # последние 200 сигналов

# Проверка кошельков
PERFORMANCE_UPDATE_WALLET_SCORES = int(os.getenv('PERFORMANCE_UPDATE_WALLET_SCORES', '1')) == 1
PERFORMANCE_SCORE_ADJUSTMENT = int(os.getenv('PERFORMANCE_SCORE_ADJUSTMENT', '5'))  # ±5 за успех/провал

# ============================================================================
# НОВОЕ: ADAPTIVE THRESHOLDS (Динамические пороги)
# ============================================================================

# Главный переключатель
ADAPTIVE_THRESHOLDS_ENABLED = int(os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', '1')) == 1

# Базовые пороги (будут адаптироваться)
ADAPTIVE_BASE_MIN_CONFIDENCE = int(os.getenv('ADAPTIVE_BASE_MIN_CONFIDENCE', '30'))
ADAPTIVE_BASE_MIN_SIZE_REL = float(os.getenv('ADAPTIVE_BASE_MIN_SIZE_REL', '0.10'))  # 0.1%
ADAPTIVE_BASE_MIN_VOLUME_24H = int(os.getenv('ADAPTIVE_BASE_MIN_VOLUME_24H', '1000000'))  # $1M

# Режимы рынка и модификаторы
ADAPTIVE_BULL_THRESHOLD = float(os.getenv('ADAPTIVE_BULL_THRESHOLD', '10.0'))  # +10% BTC за 7д = bull
ADAPTIVE_BEAR_THRESHOLD = float(os.getenv('ADAPTIVE_BEAR_THRESHOLD', '-10.0'))  # -10% BTC за 7д = bear

# Модификаторы для bull market
ADAPTIVE_BULL_CONFIDENCE_MODIFIER = int(os.getenv('ADAPTIVE_BULL_CONFIDENCE_MODIFIER', '+10').replace('+', ''))
ADAPTIVE_BULL_SIZE_REL_MODIFIER = float(os.getenv('ADAPTIVE_BULL_SIZE_REL_MODIFIER', '+0.05').replace('+', ''))
ADAPTIVE_BULL_VOLUME_MODIFIER = float(os.getenv('ADAPTIVE_BULL_VOLUME_MODIFIER', '1.5'))

# Модификаторы для bear market
ADAPTIVE_BEAR_CONFIDENCE_MODIFIER = int(os.getenv('ADAPTIVE_BEAR_CONFIDENCE_MODIFIER', '-5').replace('-', '').replace('+', ''))
if os.getenv('ADAPTIVE_BEAR_CONFIDENCE_MODIFIER', '-5').startswith('-'):
    ADAPTIVE_BEAR_CONFIDENCE_MODIFIER = -abs(ADAPTIVE_BEAR_CONFIDENCE_MODIFIER)

ADAPTIVE_BEAR_SIZE_REL_MODIFIER = float(os.getenv('ADAPTIVE_BEAR_SIZE_REL_MODIFIER', '-0.03').replace('+', ''))
if os.getenv('ADAPTIVE_BEAR_SIZE_REL_MODIFIER', '-0.03').startswith('-'):
    ADAPTIVE_BEAR_SIZE_REL_MODIFIER = -abs(ADAPTIVE_BEAR_SIZE_REL_MODIFIER)

ADAPTIVE_BEAR_VOLUME_MODIFIER = float(os.getenv('ADAPTIVE_BEAR_VOLUME_MODIFIER', '0.7'))

# Адаптация на основе производительности
ADAPTIVE_LOW_ACCURACY_THRESHOLD = float(os.getenv('ADAPTIVE_LOW_ACCURACY_THRESHOLD', '0.60'))  # <60%
ADAPTIVE_HIGH_ACCURACY_THRESHOLD = float(os.getenv('ADAPTIVE_HIGH_ACCURACY_THRESHOLD', '0.80'))  # >80%
ADAPTIVE_ACCURACY_ADJUSTMENT = int(os.getenv('ADAPTIVE_ACCURACY_ADJUSTMENT', '10'))  # ±10 к confidence

# Интервал обновления режима рынка (часы)
ADAPTIVE_MARKET_REGIME_UPDATE_HOURS = int(os.getenv('ADAPTIVE_MARKET_REGIME_UPDATE_HOURS', '4'))

# Минимум сигналов для адаптации
ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION = int(os.getenv('ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION', '20'))

# ============================================================================
# НОВОЕ: LEARNING SYSTEM (Система обучения)
# ============================================================================

# Главный переключатель
LEARNING_SYSTEM_ENABLED = int(os.getenv('LEARNING_SYSTEM_ENABLED', '1')) == 1

# Типы обучения
LEARNING_ENABLE_WALLET_SCORING = int(os.getenv('LEARNING_ENABLE_WALLET_SCORING', '1')) == 1
LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS = int(os.getenv('LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS', '1')) == 1
LEARNING_ENABLE_PATTERN_DETECTION = int(os.getenv('LEARNING_ENABLE_PATTERN_DETECTION', '1')) == 1

# Параметры обучения
LEARNING_RATE = float(os.getenv('LEARNING_RATE', '0.1'))  # скорость обучения
LEARNING_MIN_SAMPLES = int(os.getenv('LEARNING_MIN_SAMPLES', '50'))  # минимум данных для обучения
LEARNING_WINDOW_DAYS = int(os.getenv('LEARNING_WINDOW_DAYS', '30'))  # окно обучения

# Веса типов сигналов (начальные, будут обучаться)
LEARNING_SIGNAL_TYPE_WEIGHTS = {
    "smart_money": float(os.getenv('LEARNING_WEIGHT_SMART_MONEY', '0.40')),
    "mining": float(os.getenv('LEARNING_WEIGHT_MINING', '0.30')),
    "onchain": float(os.getenv('LEARNING_WEIGHT_ONCHAIN', '0.20')),
    "social": float(os.getenv('LEARNING_WEIGHT_SOCIAL', '0.10'))
}

# Корректировка весов
LEARNING_MAX_WEIGHT_ADJUSTMENT = float(os.getenv('LEARNING_MAX_WEIGHT_ADJUSTMENT', '0.15'))  # макс ±15%
LEARNING_WEIGHT_UPDATE_INTERVAL_DAYS = int(os.getenv('LEARNING_WEIGHT_UPDATE_INTERVAL_DAYS', '7'))

# ============================================================================
# НОВОЕ: WALLET DATABASE (База кошельков)
# ============================================================================

# Тип БД
WALLET_DB_TYPE = os.getenv('WALLET_DB_TYPE', 'json')  # json или sqlite

# Пути к БД
WALLET_DB_JSON_PATH = os.path.join(
    os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 
    'data', 
    'tracked_wallets.json'
)
WALLET_DB_SQLITE_PATH = os.path.join(
    os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 
    'data', 
    'tracked_wallets.db'
)

# Скоринг кошельков
WALLET_INITIAL_SCORE = int(os.getenv('WALLET_INITIAL_SCORE', '50'))  # начальный скор
WALLET_MAX_SCORE = int(os.getenv('WALLET_MAX_SCORE', '100'))
WALLET_MIN_SCORE = int(os.getenv('WALLET_MIN_SCORE', '0'))

# Обновление скоров
WALLET_SCORE_UPDATE_ON_SUCCESS = int(os.getenv('WALLET_SCORE_UPDATE_ON_SUCCESS', '+5').replace('+', ''))
WALLET_SCORE_UPDATE_ON_FAILURE = -abs(int(os.getenv('WALLET_SCORE_UPDATE_ON_FAILURE', '-3').replace('-', '').replace('+', '')))
WALLET_SCORE_DECAY_PER_DAY = float(os.getenv('WALLET_SCORE_DECAY_PER_DAY', '0.1'))  # -0.1/день неактивности

# Лимиты
WALLET_MAX_TRACKED = int(os.getenv('WALLET_MAX_TRACKED', '500'))  # максимум кошельков
WALLET_AUTO_PRUNE = int(os.getenv('WALLET_AUTO_PRUNE', '1')) == 1  # автоудаление при превышении лимита

# ============================================================================
# API КЛЮЧИ - BLOCKCHAIN
# ============================================================================
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
TRONSCAN_API_KEY = os.getenv('TRONSCAN_API_KEY')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')

# ============================================================================
# API КЛЮЧИ - НОВОСТИ И AI
# ============================================================================
CRYPTOPANIC_KEY = os.getenv('CRYPTOPANIC_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ============================================================================
# ПУТИ К ДАННЫМ
# ============================================================================
DATA_DIR = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(DATA_DIR, 'whales_state.json')
WATCHLIST_FILE = os.path.join(DATA_DIR, 'watchlist.json')
HISTORY_DIR = os.path.join(DATA_DIR, 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)

# НОВОЕ: Пути для систем обучения
LEARNING_DIR = os.path.join(DATA_DIR, 'learning')
os.makedirs(LEARNING_DIR, exist_ok=True)

PERFORMANCE_LOG_FILE = os.path.join(LEARNING_DIR, 'performance_log.json')
ADAPTIVE_STATE_FILE = os.path.join(LEARNING_DIR, 'adaptive_state.json')
LEARNING_WEIGHTS_FILE = os.path.join(LEARNING_DIR, 'learning_weights.json')

# База новостей
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')

# ============================================================================
# FALLBACK ЦЕНЫ (актуальные на 24 октября 2025)
# ============================================================================
FALLBACK_PRICES = {
    "BTC": 110000,   # ~$110,846
    "ETH": 3870,     # ~$3,876
    "BNB": 1096,     # ~$1,096
    "SOL": 189,      # ~$189
    "USDT": 1.00,
    "USDC": 1.00,
    "DAI": 1.00,
    "MATIC": 0.65,
    "AVAX": 25,
    "ARB": 0.75,
    "OP": 1.65,
    "LINK": 11,
    "UNI": 6.5,
    "AAVE": 145,
    "TRX": 0.16,
    "XRP": 2.40,
    "DOGE": 0.19,
    "WETH": 3870,
    "WBTC": 110000,
}

# ============================================================================
# HTTP SESSION SETTINGS (для bot/config.py совместимость)
# ============================================================================
SESSION_TIMEOUT_TOTAL = 30
SESSION_TIMEOUT_CONNECT = 10
COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ============================================================================
# ВАЛИДАЦИЯ И ДИАГНОСТИКА
# ============================================================================

def validate_config():
    """Проверяет конфигурацию с расширенной диагностикой"""
    errors = []
    warnings = []
    
    # Проверка Discovery
    if ASSETS == '*':
        if not COINGECKO_API_KEY:
            warnings.append("COINGECKO_API_KEY не установлен. Discovery может работать медленнее.")
        warnings.append("Discovery Mode: следите за rate limits CoinGecko (10-30 req/min без ключа)")
    
    # Проверка blockchain API
    if not ETHERSCAN_API_KEY:
        errors.append("ETHERSCAN_API_KEY обязателен для EVM мониторинга")
    if not HELIUS_API_KEY:
        errors.append("HELIUS_API_KEY обязателен для Solana мониторинга")
    if not TRONSCAN_API_KEY:
        errors.append("TRONSCAN_API_KEY обязателен для TRON мониторинга")
    
    # НОВОЕ: Проверка Trading System
    if TRADING_ENABLED:
        if TRADING_MIN_CONFIDENCE < 50 or TRADING_MIN_CONFIDENCE > 100:
            warnings.append(f"TRADING_MIN_CONFIDENCE={TRADING_MIN_CONFIDENCE} необычное значение. Рекомендуется 60-80")
        if TRADING_MAX_SIGNALS_PER_DAY < 1:
            warnings.append(f"TRADING_MAX_SIGNALS_PER_DAY={TRADING_MAX_SIGNALS_PER_DAY} слишком мало")
        if TRADING_DRY_RUN:
            warnings.append("Trading System работает в DRY RUN режиме (тестирование)")
    
    # НОВОЕ: Проверка Smart Discovery
    if SMART_DISCOVERY_ENABLED:
        if not ETHERSCAN_API_KEY:
            warnings.append("Smart Discovery требует ETHERSCAN_API_KEY для анализа кошельков")
        if SMART_DISCOVERY_INTERVAL_HOURS < 1:
            warnings.append(f"Smart Discovery интервал слишком короткий ({SMART_DISCOVERY_INTERVAL_HOURS}ч). Рекомендуется ≥6ч")
        if SMART_DISCOVERY_MIN_TRADES < 3:
            warnings.append(f"Smart Discovery: MIN_TRADES={SMART_DISCOVERY_MIN_TRADES} слишком мало. Рекомендуется ≥5")
    
    # НОВОЕ: Проверка Validation
    if VALIDATION_ENABLED:
        if VALIDATION_INTERVAL_DAYS < 1:
            warnings.append(f"Validation интервал слишком короткий ({VALIDATION_INTERVAL_DAYS} дней). Рекомендуется ≥7 дней")
        if VALIDATION_MIN_SCORE_TO_KEEP < 0 or VALIDATION_MIN_SCORE_TO_KEEP > 100:
            errors.append(f"VALIDATION_MIN_SCORE_TO_KEEP должен быть в диапазоне 0-100 (сейчас: {VALIDATION_MIN_SCORE_TO_KEEP})")
    
    # НОВОЕ: Проверка Performance Tracking
    if PERFORMANCE_TRACKING_ENABLED:
        if not COINGECKO_API_KEY:
            warnings.append("Performance Tracking будет использовать fallback цены без COINGECKO_API_KEY")
        if len(PERFORMANCE_CHECK_INTERVALS) == 0:
            errors.append("PERFORMANCE_CHECK_INTERVALS не может быть пустым")
    
    # НОВОЕ: Проверка Adaptive Thresholds
    if ADAPTIVE_THRESHOLDS_ENABLED:
        if ADAPTIVE_BASE_MIN_CONFIDENCE < 0 or ADAPTIVE_BASE_MIN_CONFIDENCE > 100:
            errors.append(f"ADAPTIVE_BASE_MIN_CONFIDENCE должен быть 0-100 (сейчас: {ADAPTIVE_BASE_MIN_CONFIDENCE})")
        if ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION < 10:
            warnings.append(f"ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION={ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION} слишком мало. Рекомендуется ≥20")
    
    # НОВОЕ: Проверка Learning System
    if LEARNING_SYSTEM_ENABLED:
        total_weight = sum(LEARNING_SIGNAL_TYPE_WEIGHTS.values())
        if abs(total_weight - 1.0) > 0.01:
            warnings.append(f"Сумма весов типов сигналов = {total_weight:.2f}, должна быть ≈1.0")
        if LEARNING_MIN_SAMPLES < 20:
            warnings.append(f"LEARNING_MIN_SAMPLES={LEARNING_MIN_SAMPLES} слишком мало. Рекомендуется ≥50")
    
    # Детальная проверка ADMIN_CHAT_ID
    if ENABLE_ALERTS:
        if ADMIN_CHAT_ID == CHAT_ID:
            warnings.append(
                f"ADMIN_CHAT_ID не установлен или равен CHAT_ID. "
                f"Алерты будут отправляться в публичный канал ({CHAT_ID})"
            )
        else:
            if ADMIN_CHAT_ID.lstrip('-').isdigit():
                print(f"✅ ADMIN_CHAT_ID настроен: {ADMIN_CHAT_ID[:4]}...{ADMIN_CHAT_ID[-4:]}")
            else:
                warnings.append(
                    f"ADMIN_CHAT_ID имеет необычный формат: {ADMIN_CHAT_ID}. "
                    f"Для личных чатов используйте числовой ID"
                )
    
    # Вывод ошибок
    if errors:
        raise ValueError(f"Ошибки конфигурации:\n" + "\n".join(f"- {e}" for e in errors))
    
    # ========================================================================
    # ОСНОВНАЯ ИНФОРМАЦИЯ
    # ========================================================================
    print("=" * 80)
    print("🧠 INTELLIGENT CRYPTO MONITOR v3.0 - Self-Learning System")
    print("=" * 80)
    print(f"Время запуска: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    print(f"\n📊 РЕЖИМ РАБОТЫ")
    if ASSETS == '*':
        print(f"  • Discovery Mode (автопоиск топ-{DISCOVERY_TOP_N_PER_CHAIN} токенов)")
        print(f"  • Обновление watchlist: каждые {DISCOVERY_REFRESH_HOURS}ч")
    else:
        print(f"  • Allowlist Mode ({len(ASSETS_LIST)} активов)")
        print(f"  • Активы: {', '.join(ASSETS_LIST[:10])}")
        if len(ASSETS_LIST) > 10:
            print(f"    ... и ещё {len(ASSETS_LIST) - 10}")
    
    print(f"\n💰 БАЗОВЫЕ ПОРОГИ")
    print(f"  • Минимальный порог: ${MIN_USD_FLOOR:,.0f}")
    print(f"  • Базовый порог: ${MIN_USD:,.0f}")
    print(f"  • Коэффициент объёма: {MIN_USD_K:.1%}")
    print(f"  • Лимит публикаций: {POSTS_PER_HOUR_CAP}/час")
    
    # ========================================================================
    # НОВЫЕ СИСТЕМЫ
    # ========================================================================
    print(f"\n🧠 СИСТЕМЫ САМООБУЧЕНИЯ")
    
    # Trading System
    print(f"\n  📈 Trading System: {'✅ Включен' if TRADING_ENABLED else '❌ Отключен'}")
    if TRADING_ENABLED:
        print(f"     • Мин. confidence: {TRADING_MIN_CONFIDENCE}/100")
        print(f"     • Макс. сигналов/день: {TRADING_MAX_SIGNALS_PER_DAY}")
        print(f"     • Cooldown: {TRADING_SIGNAL_COOLDOWN_MINUTES} мин")
        print(f"     • Макс. размер позиции: ${TRADING_MAX_POSITION_SIZE_USD:,.0f}")
        print(f"     • Макс. открытых позиций: {TRADING_MAX_OPEN_POSITIONS}")
        print(f"     • Stop Loss: {TRADING_DEFAULT_STOP_LOSS_PERCENT}%")
        print(f"     • Take Profit: {TRADING_DEFAULT_TAKE_PROFIT_PERCENT}%")
        print(f"     • Dry Run: {'да' if TRADING_DRY_RUN else 'нет'}")
    
    # Smart Money Discovery
    print(f"\n  🔍 Smart Money Discovery: {'✅ Включен' if SMART_DISCOVERY_ENABLED else '❌ Отключен'}")
    if SMART_DISCOVERY_ENABLED:
        print(f"     • Интервал: каждые {SMART_DISCOVERY_INTERVAL_HOURS}ч")
        print(f"     • Мин. рост токена: x{SMART_DISCOVERY_MIN_PRICE_CHANGE}")
        print(f"     • Мин. ROI кошелька: {SMART_DISCOVERY_MIN_WALLET_ROI * 100:.0f}%")
        print(f"     • Мин. win rate: {SMART_DISCOVERY_MIN_WIN_RATE * 100:.0f}%")
        print(f"     • Мин. сделок: {SMART_DISCOVERY_MIN_TRADES}")
        print(f"     • Анализ истории: {SMART_DISCOVERY_LOOKBACK_DAYS} дней")
        print(f"     • Макс. новых за раз: {SMART_DISCOVERY_MAX_NEW_WALLETS}")
    
    # Validation Engine
    print(f"\n  🧹 Validation Engine: {'✅ Включен' if VALIDATION_ENABLED else '❌ Отключен'}")
    if VALIDATION_ENABLED:
        print(f"     • Интервал: каждые {VALIDATION_INTERVAL_DAYS} дней")
        print(f"     • Макс. неактивность: {VALIDATION_MAX_INACTIVE_DAYS} дней")
        print(f"     • Мин. скор: {VALIDATION_MIN_SCORE_TO_KEEP}/100")
        print(f"     • Мин. ROI: {VALIDATION_MIN_ROI_TO_KEEP * 100:.0f}%")
        print(f"     • Уведомления: {'да' if VALIDATION_NOTIFY_ON_REMOVAL else 'нет'}")
    
    # Performance Tracking
    print(f"\n  📊 Performance Tracking: {'✅ Включен' if PERFORMANCE_TRACKING_ENABLED else '❌ Отключен'}")
    if PERFORMANCE_TRACKING_ENABLED:
        print(f"     • Проверка через: {', '.join(str(x)+'ч' for x in PERFORMANCE_CHECK_INTERVALS)}")
        print(f"     • Порог успеха (bullish): {PERFORMANCE_SUCCESS_THRESHOLD_BULLISH * 100:+.0f}%")
        print(f"     • Порог успеха (bearish): {PERFORMANCE_SUCCESS_THRESHOLD_BEARISH * 100:+.0f}%")
        print(f"     • Размер истории: {PERFORMANCE_HISTORY_SIZE} сигналов")
        print(f"     • Обновление скоров: {'да' if PERFORMANCE_UPDATE_WALLET_SCORES else 'нет'}")
    
    # Adaptive Thresholds
    print(f"\n  ⚙️  Adaptive Thresholds: {'✅ Включен' if ADAPTIVE_THRESHOLDS_ENABLED else '❌ Отключен'}")
    if ADAPTIVE_THRESHOLDS_ENABLED:
        print(f"     • Базовый confidence: {ADAPTIVE_BASE_MIN_CONFIDENCE}/100")
        print(f"     • Базовый size_rel: {ADAPTIVE_BASE_MIN_SIZE_REL:.2%}")
        print(f"     • Базовый volume: ${ADAPTIVE_BASE_MIN_VOLUME_24H:,.0f}")
        print(f"     • Bull порог: BTC {ADAPTIVE_BULL_THRESHOLD:+.0f}% за 7д")
        print(f"     • Bear порог: BTC {ADAPTIVE_BEAR_THRESHOLD:+.0f}% за 7д")
        print(f"     • Обновление режима: каждые {ADAPTIVE_MARKET_REGIME_UPDATE_HOURS}ч")
        print(f"     • Мин. сигналов для адаптации: {ADAPTIVE_MIN_SIGNALS_FOR_ADAPTATION}")
    
    # Learning System
    print(f"\n  🎓 Learning System: {'✅ Включен' if LEARNING_SYSTEM_ENABLED else '❌ Отключен'}")
    if LEARNING_SYSTEM_ENABLED:
        print(f"     • Wallet Scoring: {'да' if LEARNING_ENABLE_WALLET_SCORING else 'нет'}")
        print(f"     • Signal Type Weights: {'да' if LEARNING_ENABLE_SIGNAL_TYPE_WEIGHTS else 'нет'}")
        print(f"     • Pattern Detection: {'да' if LEARNING_ENABLE_PATTERN_DETECTION else 'нет'}")
        print(f"     • Learning Rate: {LEARNING_RATE}")
        print(f"     • Мин. данных: {LEARNING_MIN_SAMPLES} сигналов")
        print(f"     • Окно обучения: {LEARNING_WINDOW_DAYS} дней")
        print(f"     • Начальные веса:")
        for signal_type, weight in LEARNING_SIGNAL_TYPE_WEIGHTS.items():
            print(f"       - {signal_type}: {weight:.1%}")
    
    # Wallet Database
    print(f"\n  💾 Wallet Database:")
    print(f"     • Тип: {WALLET_DB_TYPE.upper()}")
    print(f"     • Начальный скор: {WALLET_INITIAL_SCORE}/100")
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
    }
    for name, key in api_keys.items():
        status = "✅" if key else "❌"
        print(f"  • {name}: {status}")
    
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
    }


def get_all_settings() -> Dict:
    """Возвращает все настройки в виде словаря (для экспорта/бэкапа)"""
    return {
        "version": "3.0",
        "timestamp": datetime.utcnow().isoformat(),
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
        }
    }


# Запуск валидации
validate_config()