# app/settings.py (МАКСИМАЛЬНО УЛУЧШЕННАЯ ВЕРСИЯ)
import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

# ============================================================================
# ОБЩИЕ НАСТРОЙКИ
# ============================================================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID') or os.getenv('TELEGRAM_CHANNEL_ID')

# НОВОЕ: ID админа для уведомлений об ошибках (по умолчанию = канал)
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', CHAT_ID)

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID обязательны")

# Старые настройки (совместимость)
TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN
TELEGRAM_CHANNEL_ID = CHAT_ID

# ============================================================================
# WHALE MONITOR - ОСНОВНЫЕ ПАРАМЕТРЫ
# ============================================================================
ASSETS = os.getenv('ASSETS', '*')
ASSETS_LIST = [] if ASSETS == '*' else [a.strip() for a in ASSETS.split(',')]

# Базовые пороги (УЛУЧШЕНО)
MIN_USD = float(os.getenv('MIN_USD', '500000'))
MIN_USD_FLOOR = float(os.getenv('MIN_USD_FLOOR', '50000'))  # БЫЛО 300000
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

# Логирование (УЛУЧШЕНО)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DEBUG_FILTERS = int(os.getenv('DEBUG_FILTERS', '1')) == 1

# НОВОЕ: Настройки алертов
ENABLE_ALERTS = int(os.getenv('ENABLE_ALERTS', '1')) == 1  # Уведомления об ошибках
ALERT_COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', '300'))  # 5 минут между повторами
SEND_STARTUP_NOTIFICATION = int(os.getenv('SEND_STARTUP_NOTIFICATION', '1')) == 1
SEND_DAILY_STATS = int(os.getenv('SEND_DAILY_STATS', '1')) == 1

# ============================================================================
# API КЛЮЧИ - BLOCKCHAIN
# ============================================================================
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
TRONSCAN_API_KEY = os.getenv('TRONSCAN_API_KEY')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

# НОВОЕ: Дополнительные источники цен (fallback)
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')  # Опционально

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

# Старая база новостей
DB_PATH = os.path.join(os.environ.get('RENDER_DISK_MOUNT_PATH', '.'), 'news_database.sqlite')

# ============================================================================
# ВАЛИДАЦИЯ
# ============================================================================
def validate_config():
    errors = []
    warnings = []
    
    if ASSETS == '*':
        if not COINGECKO_API_KEY:
            warnings.append("COINGECKO_API_KEY не установлен. Discovery может работать медленнее.")
    
    # Проверка blockchain API
    if not ETHERSCAN_API_KEY:
        errors.append("ETHERSCAN_API_KEY обязателен для EVM мониторинга")
    if not HELIUS_API_KEY:
        errors.append("HELIUS_API_KEY обязателен для Solana мониторинга")
    if not TRONSCAN_API_KEY:
        errors.append("TRONSCAN_API_KEY обязателен для TRON мониторинга")
    
    # НОВОЕ: Проверка настроек алертов
    if ENABLE_ALERTS:
        if ADMIN_CHAT_ID == CHAT_ID:
            warnings.append("ADMIN_CHAT_ID не установлен - уведомления пойдут в публичный канал")
    
    if errors:
        raise ValueError(f"Ошибки конфигурации:\n" + "\n".join(f"- {e}" for e in errors))
    
    print(f"✅ Конфигурация валидна")
    print(f"📊 Режим: {'DISCOVERY' if ASSETS == '*' else f'ALLOWLIST ({len(ASSETS_LIST)} активов)'}")
    print(f"💰 Порог: ${MIN_USD_FLOOR:,.0f}")
    print(f"🔔 Алерты: {'включены' if ENABLE_ALERTS else 'выключены'}")
    print(f"📈 Логирование фильтров: {'включено' if DEBUG_FILTERS else 'выключено'}")
    
    if warnings:
        print(f"\n⚠️  Предупреждения:")
        for w in warnings:
            print(f"  - {w}")

# Запуск валидации
validate_config()