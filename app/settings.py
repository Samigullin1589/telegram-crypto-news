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
✅ Bot Commands - интерактивные команды (/stats, /positions, /help)
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
# BOT COMMANDS - НОВОЕ!
# ============================================================================
# Используем тот же токен для команд (или отдельный если указан)
BOT_TOKEN = os.getenv('BOT_TOKEN', TELEGRAM_BOT_TOKEN)

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

# Интервалы проверки (в минутах)
PERFORMANCE_CHECK_INTERVALS = [int(x) for x in os.getenv('PERFORMANCE_CHECK_INTERVALS', '60,240,1440').split(',')]  # 1ч, 4ч, 24ч

# История
PERFORMANCE_HISTORY_SIZE = int(os.getenv('PERFORMANCE_HISTORY_SIZE', '1000'))  # макс сигналов в истории
PERFORMANCE_LOOKBACK_DAYS = int(os.getenv('PERFORMANCE_LOOKBACK_DAYS', '90'))  # период анализа

# Критерии успеха
PERFORMANCE_SUCCESS_THRESHOLD = float(os.getenv('PERFORMANCE_SUCCESS_THRESHOLD', '0.05'))  # +5% минимум
PERFORMANCE_MIN_CONFIDENCE_FOR_TRACKING = int(os.getenv('PERFORMANCE_MIN_CONFIDENCE_FOR_TRACKING', '50'))  # минимальная confidence для трекинга

# Уведомления
PERFORMANCE_NOTIFY_ON_MILESTONES = int(os.getenv('PERFORMANCE_NOTIFY_ON_MILESTONES', '1')) == 1
PERFORMANCE_MILESTONE_SIGNALS = [int(x) for x in os.getenv('PERFORMANCE_MILESTONE_SIGNALS', '10,50,100,500').split(',')]

# ============================================================================
# НОВОЕ: ADAPTIVE THRESHOLDS (Динамические пороги)
# ============================================================================

# Главный переключатель
ADAPTIVE_THRESHOLDS_ENABLED = int(os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', '1')) == 1

# Базовые значения (отправная точка)
ADAPTIVE_BASE_MIN_CONFIDENCE = int(os.getenv('ADAPTIVE_BASE_MIN_CONFIDENCE', '30'))
ADAPTIVE_BASE_MIN_SIZE_REL = float(os.getenv('ADAPTIVE_BASE_MIN_SIZE_REL', '0.10'))  # 10%
ADAPTIVE_BASE_MIN_VOLUME_24H = int(os.getenv('ADAPTIVE_BASE_MIN_VOLUME_24H', '1000000'))  # $1M

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
WALLET_INITIAL_SCORE = int(os.getenv('WALLET_INITIAL_SCORE', '50'))  # начальный скор
WALLET_MIN_SCORE = int(os.getenv('WALLET_MIN_SCORE', '0'))
WALLET_MAX_SCORE = int(os.getenv('WALLET_MAX_SCORE', '100'))

# Обновление скора
WALLET_SCORE_UPDATE_ON_SUCCESS = int(os.getenv('WALLET_SCORE_UPDATE_ON_SUCCESS', '+5'))
WALLET_SCORE_UPDATE_ON_FAILURE = int(os.getenv('WALLET_SCORE_UPDATE_ON_FAILURE', '-3'))
WALLET_SCORE_DECAY_PER_DAY = int(os.getenv('WALLET_SCORE_DECAY_PER_DAY', '1'))  # естественная деградация

# Лимиты
WALLET_MAX_TRACKED = int(os.getenv('WALLET_MAX_TRACKED', '500'))  # максимум кошельков
WALLET_AUTO_PRUNE = int(os.getenv('WALLET_AUTO_PRUNE', '1')) == 1  # автоудаление худших

# ============================================================================
# API КЛЮЧИ И ДОСТУПЫ
# ============================================================================

# Blockchain explorers
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', ETHERSCAN_API_KEY)
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
TRONSCAN_API_KEY = os.getenv('TRONSCAN_API_KEY')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY')

# Multi-chain API keys
BASE_API_KEY = os.getenv('BASE_API_KEY', ETHERSCAN_API_KEY)
ARBITRUM_API_KEY = os.getenv('ARBITRUM_API_KEY', ETHERSCAN_API_KEY)
OPTIMISM_API_KEY = os.getenv('OPTIMISM_API_KEY', ETHERSCAN_API_KEY)
AVALANCHE_API_KEY = os.getenv('AVALANCHE_API_KEY')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

# RPC endpoints
SOLANA_RPC_URLS = os.getenv('SOLANA_RPC_URLS', 'https://api.mainnet-beta.solana.com').split(',')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')

# Рыночные данные
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')

# AI сервисы
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Новости
CRYPTOPANIC_KEY = os.getenv('CRYPTOPANIC_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# ============================================================================
# ФАЙЛОВАЯ СИСТЕМА
# ============================================================================

# Базовые директории
DATA_DIR = os.getenv('DATA_DIR', 'data')
STATE_FILE = os.path.join(DATA_DIR, 'state.json')

# Learning System директории
LEARNING_DIR = os.path.join(DATA_DIR, 'learning')
LEARNING_MODELS_DIR = os.path.join(LEARNING_DIR, 'models')
LEARNING_HISTORY_DIR = os.path.join(LEARNING_DIR, 'history')

# Создание директорий
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LEARNING_DIR, exist_ok=True)
os.makedirs(LEARNING_MODELS_DIR, exist_ok=True)
os.makedirs(LEARNING_HISTORY_DIR, exist_ok=True)

# ============================================================================
# ВАЛИДАЦИЯ КОНФИГУРАЦИИ
# ============================================================================

def validate_config():
    """Проверяет корректность настроек и выводит предупреждения"""
    
    warnings = []
    
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
        if PERFORMANCE_SUCCESS_THRESHOLD < 0.02:
            warnings.append(f"PERFORMANCE_SUCCESS_THRESHOLD очень низкий ({PERFORMANCE_SUCCESS_THRESHOLD}) - почти всё будет 'успехом'")
    
    return warnings


def print_config_summary():
    """Выводит сводку по конфигурации (для отладки)"""
    
    warnings = validate_config()
    
    print("=" * 80)
    print("⚙️  CONFIGURATION SUMMARY")
    print("=" * 80)
    
    # ========================================================================
    # НОВЫЕ ИНТЕЛЛЕКТУАЛЬНЫЕ СИСТЕМЫ
    # ========================================================================
    print(f"\n🧠 ИНТЕЛЛЕКТУАЛЬНЫЕ СИСТЕМЫ:")
    
    # Trading System
    print(f"\n  📈 Trading System: {'✅ Включен' if TRADING_ENABLED else '❌ Отключен'}")
    if TRADING_ENABLED:
        print(f"     • Режим: {'🧪 DRY RUN (безопасный)' if TRADING_DRY_RUN else '💰 LIVE (боевой)'}")
        print(f"     • Min confidence: {TRADING_MIN_CONFIDENCE}/100")
        print(f"     • Max signals/day: {TRADING_MAX_SIGNALS_PER_DAY}")
        print(f"     • Signal cooldown: {TRADING_SIGNAL_COOLDOWN_MINUTES} минут")
        print(f"     • Signal interval: каждые {TRADING_SIGNAL_INTERVAL_HOURS} час(а)")
        print(f"     • Max position size: ${TRADING_MAX_POSITION_SIZE_USD:,.0f}")
        print(f"     • Max open positions: {TRADING_MAX_OPEN_POSITIONS}")
        print(f"     • Stop-Loss: {TRADING_DEFAULT_STOP_LOSS_PERCENT}%")
        print(f"     • Take-Profit: {TRADING_DEFAULT_TAKE_PROFIT_PERCENT}%")
        print(f"     • Фильтры:")
        print(f"       - Technical score: ≥{TRADING_MIN_TECHNICAL_SCORE}/100")
        print(f"       - Fundamental score: ≥{TRADING_MIN_FUNDAMENTAL_SCORE}/100")
        print(f"       - ML confidence: ≥{TRADING_MIN_ML_CONFIDENCE}%")
    
    # Smart Discovery
    print(f"\n  🔍 Smart Discovery: {'✅ Включен' if SMART_DISCOVERY_ENABLED else '❌ Отключен'}")
    if SMART_DISCOVERY_ENABLED:
        print(f"     • Интервал: каждые {SMART_DISCOVERY_INTERVAL_HOURS}ч")
        print(f"     • Min price change: {SMART_DISCOVERY_MIN_PRICE_CHANGE}x")
        print(f"     • Max токенов для анализа: {SMART_DISCOVERY_MAX_TOKENS_TO_ANALYZE}")
        print(f"     • Критерии кошельков:")
        print(f"       - Min ROI: {SMART_DISCOVERY_MIN_WALLET_ROI:.0%}")
        print(f"       - Min win rate: {SMART_DISCOVERY_MIN_WIN_RATE:.0%}")
        print(f"       - Min trades: {SMART_DISCOVERY_MIN_TRADES}")
        print(f"     • Lookback: {SMART_DISCOVERY_LOOKBACK_DAYS} дней")
        print(f"     • Max новых кошельков: {SMART_DISCOVERY_MAX_NEW_WALLETS} за раз")
        print(f"     • Источники: {', '.join(SMART_DISCOVERY_SOURCES)}")
    
    # Validation
    print(f"\n  🧹 Validation Engine: {'✅ Включен' if VALIDATION_ENABLED else '❌ Отключен'}")
    if VALIDATION_ENABLED:
        print(f"     • Интервал: каждые {VALIDATION_INTERVAL_DAYS}д")
        print(f"     • Max неактивность: {VALIDATION_MAX_INACTIVE_DAYS} дней")
        print(f"     • Min score для сохранения: {VALIDATION_MIN_SCORE_TO_KEEP}/100")
        print(f"     • Min ROI для сохранения: {VALIDATION_MIN_ROI_TO_KEEP:.0%}")
        print(f"     • Проверки:")
        print(f"       - Last trade: {'да' if VALIDATION_CHECK_LAST_TRADE else 'нет'}")
        print(f"       - Performance: {'да' if VALIDATION_CHECK_PERFORMANCE else 'нет'}")
        print(f"     • Уведомления: {'да' if VALIDATION_NOTIFY_ON_REMOVAL else 'нет'} (порог: {VALIDATION_NOTIFY_THRESHOLD})")
    
    # Performance Tracking
    print(f"\n  📊 Performance Tracking: {'✅ Включен' if PERFORMANCE_TRACKING_ENABLED else '❌ Отключен'}")
    if PERFORMANCE_TRACKING_ENABLED:
        intervals_str = ', '.join([f"{i//60}ч" if i >= 60 else f"{i}м" for i in PERFORMANCE_CHECK_INTERVALS])
        print(f"     • Интервалы проверки: {intervals_str}")
        print(f"     • История: {PERFORMANCE_HISTORY_SIZE} сигналов")
        print(f"     • Lookback: {PERFORMANCE_LOOKBACK_DAYS} дней")
        print(f"     • Success threshold: {PERFORMANCE_SUCCESS_THRESHOLD:+.1%}")
        print(f"     • Min confidence для трекинга: {PERFORMANCE_MIN_CONFIDENCE_FOR_TRACKING}/100")
        if PERFORMANCE_NOTIFY_ON_MILESTONES:
            print(f"     • Milestones: {', '.join(map(str, PERFORMANCE_MILESTONE_SIGNALS))} сигналов")
    
    # Adaptive Thresholds
    print(f"\n  ⚙️ Adaptive Thresholds: {'✅ Включен' if ADAPTIVE_THRESHOLDS_ENABLED else '❌ Отключен'}")
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
        },
        "bot_commands": {
            "enabled": bool(BOT_TOKEN),
        }
    }


# Запуск валидации
validate_config()