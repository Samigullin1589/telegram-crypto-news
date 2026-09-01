import asyncio
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

os.environ.setdefault(
    'TELEGRAM_BOT_TOKEN',
    '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi',
)
os.environ.setdefault('TELEGRAM_CHANNEL_ID', '-1001234567890')

from app.config.features.trading import TradingFeatures
from app.trading_system import TradingSystem
from core.tasks.trading_runner import TradingCycleExecutor


def make_signal(**overrides):
    values = {
        'asset': 'BTC',
        'signal': 'BUY',
        'confidence': 88.0,
        'entry_price': 100_000.0,
        'stop_loss': 97_000.0,
        'take_profit': 106_000.0,
        'risk_reward_ratio': 2.0,
        'reasons': ['Рост объёма', 'Положительный импульс'],
        'timestamp': datetime.now(timezone.utc),
        'is_tradeable': lambda: True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_system(signal):
    system = TradingSystem.__new__(TradingSystem)
    system.enabled = True
    system._initialized = True
    system.signal_generator = object()
    system.trading_config = {
        'monitored_assets': ['BTC'],
        'min_confidence': 75,
        'max_signals_per_day': 10,
        'max_signals_per_hour': 5,
        'signal_interval_hours': 1,
        'asset_timeout': 5,
    }
    system._published_at = {}
    system._daily_publications = []
    system._fetch_ohlcv = AsyncMock(
        return_value=pd.DataFrame({'close': range(50)})
    )
    system.generate_signal = AsyncMock(return_value=signal)
    system._publish_signal = AsyncMock(return_value=True)
    return system


def test_trading_features_parse_monitored_assets(monkeypatch):
    monkeypatch.setenv('TRADING_MONITORED_ASSETS', 'btc, ETH,btc,invalid-pair')

    trading = TradingFeatures()

    assert trading.monitored_assets == ['BTC', 'ETH']
    assert trading.to_dict()['monitored_assets'] == ['BTC', 'ETH']


def test_active_trading_cycle_generates_and_confirms_publication():
    signal = make_signal()
    system = make_system(signal)

    result = asyncio.run(system.run_signal_cycle())

    assert result == {
        'success': True,
        'assets_checked': 1,
        'signals_generated': 1,
        'signals_sent': 1,
        'errors': 0,
    }
    system.generate_signal.assert_awaited_once()
    system._publish_signal.assert_awaited_once_with(signal)
    assert 'BTC' in system._published_at


def test_unconfirmed_trading_publication_is_not_counted():
    system = make_system(make_signal())
    system._publish_signal.return_value = False

    result = asyncio.run(system.run_signal_cycle())

    assert result['signals_generated'] == 1
    assert result['signals_sent'] == 0
    assert result['errors'] == 1
    assert result['success'] is False
    assert system._published_at == {}


def test_runner_rejects_legacy_noop_contract():
    executor = TradingCycleExecutor(SimpleNamespace(enabled=True))

    with pytest.raises(RuntimeError, match='run_signal_cycle'):
        asyncio.run(executor.execute_cycle())


def test_runner_returns_measurable_signal_cycle_result():
    trading_system = SimpleNamespace(
        run_signal_cycle=AsyncMock(return_value={
            'signals_generated': 2,
            'signals_sent': 1,
            'errors': 0,
        })
    )
    executor = TradingCycleExecutor(trading_system)

    result = asyncio.run(executor.execute_cycle())

    assert result['signals_sent'] == 1
    trading_system.run_signal_cycle.assert_awaited_once_with()


def test_signal_message_is_russian_and_contains_disclaimer():
    system = make_system(make_signal())

    message = system.format_signal_for_telegram(make_signal())

    assert 'Торговый сигнал' in message
    assert 'ПОКУПКА' in message
    assert 'инвестиционной рекомендацией' in message
    assert 'TRADING SIGNAL' not in message


def test_english_internal_reasons_are_not_published():
    system = make_system(make_signal())

    message = system.format_signal_for_telegram(
        make_signal(reasons=['Component weights: Tech 30%, ML 25%'])
    )

    assert 'Component weights' not in message
    assert 'Сигнал подтверждён совокупностью' in message