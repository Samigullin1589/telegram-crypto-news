# app/settings.py (ФИНАЛЬНАЯ ВЕРСИЯ - Октябрь 2025)
import os
from dotenv import load_dotenv
from typing import List, Optional

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

# НОВОЕ: Rate Limiting (защита от бана)
RATE_LIMIT_ENABLED = int(os.getenv('RATE_LIMIT_ENABLED', '1')) == 1
RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '5'))  # запросов
RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '60'))  # за 60 секунд

# НОВОЕ: Retry настройки
RETRY_MAX_ATTEMPTS = int(os.getenv('RETRY_MAX_ATTEMPTS', '3'))
RETRY_BACKOFF_FACTOR = int(os.getenv('RETRY_BACKOFF_FACTOR', '2'))
RETRY_TIMEOUT = int(os.getenv('RETRY_TIMEOUT', '30'))

# НОВОЕ: Health Check
HEALTH_CHECK_ENABLED = int(os.getenv('HEALTH_CHECK_ENABLED', '1')) == 1
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))  # 5 минут
HEALTH_CHECK_MAX_SILENCE = int(os.getenv('HEALTH_CHECK_MAX_SILENCE', '600'))  # 10 минут

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
# API КЛЮЧИ - НОВОСТИ
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

# База новостей
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')

# НОВОЕ: Актуальные fallback цены (24 октября 2025 - проверено через web search)
FALLBACK_PRICES = {
    "BTC": 110000,   # ~$110,846 на 24.10.2025
    "ETH": 3870,     # ~$3,876 на 24.10.2025
    "BNB": 1096,     # ~$1,096 на 24.10.2025
    "SOL": 189,      # ~$189 на 24.10.2025
    "USDT": 1.00,    # Stablecoin
    "USDC": 1.00,    # Stablecoin
    "MATIC": 0.65,   # Оценка
    "AVAX": 25,      # Оценка
    "ARB": 0.75,     # Оценка
    "OP": 1.65,      # Оценка
    "LINK": 11,      # Оценка
    "UNI": 6.5,      # Оценка
    "AAVE": 145,     # Оценка
    "TRX": 0.16,     # Оценка
    "XRP": 2.40,     # Видел в результатах
    "DOGE": 0.19,    # Видел в результатах
    "WETH": 3870,    # = ETH
    "WBTC": 110000,  # = BTC
}

# ============================================================================
# ВАЛИДАЦИЯ И ДИАГНОСТИКА
# ============================================================================
def validate_config():
    """Проверяет конфигурацию и выводит детальную информацию"""
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
    
    # Основная информация
    print("=" * 80)
    print("⚙️  КОНФИГУРАЦИЯ СИСТЕМЫ v2.0 (Октябрь 2025)")
    print("=" * 80)
    
    print(f"\n📊 РЕЖИМ РАБОТЫ")
    if ASSETS == '*':
        print(f"  • Discovery Mode (автопоиск топ-{DISCOVERY_TOP_N_PER_CHAIN} токенов)")
        print(f"  • Обновление watchlist: каждые {DISCOVERY_REFRESH_HOURS}ч")
    else:
        print(f"  • Allowlist Mode ({len(ASSETS_LIST)} активов)")
        print(f"  • Активы: {', '.join(ASSETS_LIST[:10])}")
        if len(ASSETS_LIST) > 10:
            print(f"    ... и ещё {len(ASSETS_LIST) - 10}")
    
    print(f"\n💰 ПОРОГИ USD")
    print(f"  • Минимальный порог: ${MIN_USD_FLOOR:,.0f}")
    print(f"  • Базовый порог: ${MIN_USD:,.0f}")
    print(f"  • Коэффициент объёма: {MIN_USD_K:.1%}")
    
    print(f"\n📡 МОНИТОРИНГ")
    print(f"  • Интервал опроса: {POLL_SECONDS}с")
    print(f"  • Начать с: {START_FROM_MINUTES_AGO} минут назад")
    print(f"  • Лимит публикаций: {POSTS_PER_HOUR_CAP}/час")
    
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

def get_environment_info():
    """Возвращает информацию об окружении для отладки"""
    return {
        "render": bool(os.environ.get('RENDER')),
        "render_service": os.environ.get('RENDER_SERVICE_NAME', 'N/A'),
        "python_version": os.environ.get('PYTHON_VERSION', 'N/A'),
        "has_disk": bool(os.environ.get('RENDER_DISK_MOUNT_PATH')),
        "disk_path": os.environ.get('RENDER_DISK_MOUNT_PATH', 'N/A'),
    }

# Запуск валидации
validate_config()