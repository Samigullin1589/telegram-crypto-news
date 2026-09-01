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
        'signals_actionable': 1,
        'signals_filtered': 0,
        'filter_reasons': {},
        'signals_sent': 1,
        'errors': 0,
    }
    system.generate_signal.assert_awaited_once()
    system._publish_signal.assert_awaited_once_with(signal)
    assert 'BTC' in system._published_at


def test_facade_delegates_single_signal_to_internal_generator():
    signal = make_signal()
    internal_generator = SimpleNamespace(
        generate_signal=AsyncMock(return_value=signal)
    )
    system = TradingSystem.__new__(TradingSystem)
    system.enabled = True
    system._initialized = True
    system.signal_generator = internal_generator
    price_data = object()
    session = object()

    result = asyncio.run(
        system.generate_signal('BTC', price_data, session)
    )

    assert result is signal
    internal_generator.generate_signal.assert_awaited_once_with(
        asset='BTC',
        price_data=price_data,
        session=session,
    )


def test_unconfirmed_trading_publication_is_not_counted():
    system = make_system(make_signal())
    system._publish_signal.return_value = False

    result = asyncio.run(system.run_signal_cycle())

    assert result['signals_generated'] == 1
    assert result['signals_sent'] == 0
    assert result['errors'] == 1
    assert result['success'] is False
    assert system._published_at == {}


def test_missing_generated_signal_marks_cycle_failed():
    system = make_system(None)

    result = asyncio.run(system.run_signal_cycle())

    assert result['signals_generated'] == 0
    assert result['signals_sent'] == 0
    assert result['errors'] == 1
    assert result['success'] is False


def test_non_actionable_analysis_is_reported_as_filtered_not_failed():
    system = make_system(make_signal(signal='HOLD', confidence=92.0))

    result = asyncio.run(system.run_signal_cycle())

    assert result['signals_generated'] == 1
    assert result['signals_actionable'] == 0
    assert result['signals_filtered'] == 1
    assert result['filter_reasons'] == {'non_actionable_direction': 1}
    assert result['signals_sent'] == 0
    assert result['errors'] == 0
    assert result['success'] is True
    system._publish_signal.assert_not_awaited()


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

    assert 'BTC — сигнал на рост' in message
    assert 'ПОКУПКА / LONG' in message
    assert 'Простыми словами' in message
    assert 'Оценка модели' in message
    assert 'не вероятность прибыли' in message
    assert 'инвестиционной рекомендацией' in message
    assert 'TRADING SIGNAL' not in message


def test_english_internal_reasons_are_not_published():
    system = make_system(make_signal())

    message = system.format_signal_for_telegram(
        make_signal(reasons=['Component weights: Tech 30%, ML 25%'])
    )

    assert 'Component weights' not in message
    assert 'Сигнал подтверждён совокупностью' in message


def test_sell_signal_message_explains_trade_to_a_beginner():
    system = make_system(make_signal())

    message = system.format_signal_for_telegram(make_signal(
        asset='LINK',
        signal='STRONG_SELL',
        confidence=81.2,
        entry_price=11.3390,
        stop_loss=11.5658,
        take_profit=10.9308,
        risk_reward_ratio=1.8,
        reasons=['[TECH] MACD медвежий кроссовер'],
    ))

    assert 'LINK — сильный сигнал на снижение' in message
    assert '<b>Сценарий:</b> ПРОДАЖА / SHORT' in message
    assert 'SHORT — сделка с расчётом на снижение цены' in message
    assert '<b>Оценка модели:</b> 81 из 100' in message
    assert '🛑 <b>Стоп:</b> $11.5658 <i>(2.0% от входа)</i>' in message
    assert '🏁 <b>Цель:</b> $10.9308 <i>(3.6% от входа)</i>' in message
    assert 'На каждый $1 риска — до $1.80 потенциальной прибыли' in message
    assert 'MACD развернулся вниз — признак возможного снижения' in message
    assert '[TECH]' not in message