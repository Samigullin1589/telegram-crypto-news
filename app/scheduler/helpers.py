# app/scheduler/helpers.py
"""
Helper functions and utilities for the scheduler
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Set

from app.config import config

logger = logging.getLogger(__name__)


def load_state() -> Set[str]:
    """Загрузка состояния из файла"""
    try:
        # ИСПРАВЛЕНО: Безопасный доступ к config.paths.state_file
        _paths = getattr(config, 'paths', None)
        state_file_path = getattr(_paths, 'state_file', 'data/state.json') if _paths else 'data/state.json'
        state_file = Path(state_file_path)

        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                seen_keys = set(state.get("seen_keys", []))
            logger.info(f"📂 [STATE] Загружено {len(seen_keys)} ключей")
            return seen_keys
        else:
            return set()
    except Exception as e:
        logger.error(f"⚠️ [STATE] Ошибка загрузки: {e}")
        return set()


def save_state(seen_keys: Set[str]):
    """Сохранение состояния в файл"""
    try:
        state = {
            "last_seen_timestamp": datetime.utcnow().isoformat(),
            "seen_keys": list(seen_keys)[-10000:]
        }

        # ИСПРАВЛЕНО: Безопасный доступ к config.paths.state_file
        _paths = getattr(config, 'paths', None)
        state_file_path = getattr(_paths, 'state_file', 'data/state.json') if _paths else 'data/state.json'
        state_file = Path(state_file_path)
        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"💾 [STATE] Сохранено")
    except Exception as e:
        logger.error(f"⚠️ [STATE] Ошибка: {e}")


def print_startup_banner(components: Dict):
    """Вывод баннера при запуске"""
    print("\n" + "="*80)
    print("🐋 INTEGRATED SCHEDULER v4.4 - PRODUCTION READY")
    print("="*80)

    # ИСПРАВЛЕНО: Безопасный доступ к config
    _telegram = getattr(config, 'telegram', None)
    _features = getattr(config, 'features', None)
    _whale = getattr(_features, 'whale', None) if _features else None
    _news = getattr(config, 'news', None) or getattr(config, 'feeds', None)
    _trading = getattr(_features, 'trading', None) if _features else None
    _blockchain = getattr(config, 'blockchain', None)

    if _telegram:
        print(f"Канал: {getattr(_telegram, 'channel_id', 'N/A')}")

    if _whale:
        print(f"Лимит: {getattr(_whale, 'posts_per_hour_cap', 10)}/час")

    print(f"\n🐋 WHALE MONITORING:")
    print(f"  Status: {'✅ Enabled' if config.is_feature_enabled('whale') else '❌ Disabled'}")
    if _whale:
        print(f"  Min USD: ${getattr(_whale, 'min_usd_threshold', 100000):,.0f}")
        print(f"  Confidence: ≥{getattr(_whale, 'min_confidence_score', 70)}")

    print(f"\n📰 NEWS INTEGRATION:")
    print(f"  Status: {'✅ Enabled' if config.is_feature_enabled('news') else '❌ Disabled'}")
    if _news:
        print(f"  Interval: {getattr(_news, 'fetch_interval', 300)}s")

    print(f"\n📈 TRADING SYSTEM:")
    print(f"  Status: {'✅ Enabled' if config.is_feature_enabled('trading') else '❌ Disabled'}")
    if config.is_feature_enabled('trading') and _trading:
        monitored = getattr(_trading, 'monitored_assets', [])
        print(f"  Assets: {len(monitored)}")

    print(f"\n🌊 HYPERLIQUID DEX:")
    hyperliquid_enabled = config.is_feature_enabled('hyperliquid') if hasattr(config, 'is_feature_enabled') else False
    print(f"  Status: {'✅ Enabled' if hyperliquid_enabled else '❌ Disabled'}")

    print(f"\n🌐 CHAINS:")
    if _blockchain:
        chains = getattr(_blockchain, 'enabled_chains', [])
        print(f"  Enabled: {', '.join(chains) if chains else 'N/A'}")

    if components.get('wallet_db'):
        active = len(components['wallet_db'].get_active_wallets())
        print(f"\n💾 Tracked Wallets: {active}")

    print("="*80 + "\n")


def print_shutdown_summary(stats: Dict):
    """Вывод итоговой статистики при остановке"""
    print("\n" + "="*80)
    print("📊 ФИНАЛЬНАЯ СТАТИСТИКА")
    print("="*80)
    
    print(f"\n🐋 WHALE MONITORING:")
    print(f"  События собрано: {stats.get('events_collected', 0)}")
    print(f"  Прошло фильтры: {stats.get('events_qualified', 0)}")
    print(f"  Опубликовано: {stats.get('events_published', 0)}")
    
    total = stats.get('events_successful', 0) + stats.get('events_failed', 0)
    if total > 0:
        accuracy = (stats.get('events_successful', 0) / total) * 100
        print(f"  Успешных: {stats.get('events_successful', 0)}/{total} ({accuracy:.1f}%)")
    
    print(f"\n📰 NEWS SYSTEM:")
    print(f"  Cycles: {stats.get('news_cycles', 0)}")
    print(f"  Articles Processed: {stats.get('news_articles_processed', 0)}")
    print(f"  Articles Published: {stats.get('news_articles_published', 0)}")
    
    if stats.get('trading_signals_generated', 0) > 0:
        print(f"\n📈 TRADING SYSTEM:")
        print(f"  Сигналов сгенерировано: {stats.get('trading_signals_generated', 0)}")
        print(f"  Сигналов отправлено: {stats.get('trading_signals_sent', 0)}")
    
    if stats.get('start_time'):
        uptime_hours = (datetime.utcnow() - stats['start_time']).total_seconds() / 3600
        print(f"\n⏱️ Uptime: {uptime_hours:.1f}h")
    
    print("\n" + "="*80)
    print("✅ SHUTDOWN COMPLETE")
    print("="*80 + "\n")


async def fetch_current_price(asset: str, session) -> Optional[float]:
    """Получение текущей цены актива"""
    try:
        symbol = f"{asset}USDT"
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {'symbol': symbol}
        
        async with session.get(url, params=params, timeout=5) as resp:
            if resp.status != 200:
                return None
            
            data = await resp.json()
            return float(data.get('price', 0))
            
    except Exception as e:
        logger.debug(f"⚠️ [PRICE] Ошибка для {asset}: {e}")
        return None


async def get_price_change_24h(asset: str, session) -> Optional[float]:
    """Получает изменение цены за 24ч"""
    try:
        symbol_to_id = {
            "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
            "SOL": "solana", "MATIC": "matic-network", "AVAX": "avalanche-2",
            "ARB": "arbitrum", "OP": "optimism", "DOT": "polkadot",
            "LINK": "chainlink", "UNI": "uniswap", "AAVE": "aave",
            "XRP": "ripple", "ADA": "cardano"
        }
        
        coin_id = symbol_to_id.get(asset)
        if not coin_id:
            return None
        
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                if coin_id in data and "usd_24h_change" in data[coin_id]:
                    return data[coin_id]["usd_24h_change"] / 100
    
    except Exception as e:
        logger.debug(f"⚠️ Ошибка получения price change для {asset}: {e}")
    
    return None