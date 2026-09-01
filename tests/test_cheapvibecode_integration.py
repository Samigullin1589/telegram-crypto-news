import asyncio
import argparse
import os
from types import SimpleNamespace

os.environ.setdefault(
    'TELEGRAM_BOT_TOKEN',
    '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi',
)
os.environ.setdefault('TELEGRAM_CHANNEL_ID', '-1001234567890')

from app.config.api_config import APIConfig
from bot import ai_handler as ai_module
from scripts import configure_cheapvibecode


def clear_ai_environment(monkeypatch):
    for name in (
        'CHEAPVIBECODE_API_KEY',
        'CHEAPVIBECODE_BASE_URL',
        'CHEAPVIBECODE_MODEL',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'GEMINI_API_KEY',
        'AI_MAX_RETRIES',
        'AI_BACKOFF_FACTOR',
        'AI_TIMEOUT',
        'AI_MAX_TOKENS',
        'AI_TRANSLATION_MAX_TOKENS',
        'AI_TEMPERATURE',
    ):
        monkeypatch.delenv(name, raising=False)


def make_runtime_config(**overrides):
    values = {
        'CHEAPVIBECODE_API_KEY': 'hidden-test-key',
        'CHEAPVIBECODE_BASE_URL': 'https://cheapvibecode.ru/v1',
        'CHEAPVIBECODE_MODEL': 'provider/model-id',
        'GEMINI_API_KEY': '',
        'GEMINI_MODEL': 'gemini-test',
        'OPENAI_API_KEY': '',
        'OPENAI_MODEL': 'openai-test',
        'AI_MAX_RETRIES': 3,
        'AI_BACKOFF_FACTOR': 0,
        'AI_TIMEOUT': 10,
        'AI_MAX_TOKENS': 420,
        'AI_TRANSLATION_MAX_TOKENS': 700,
        'AI_TEMPERATURE': 0.2,
        'MAX_ARTICLE_TEXT_LENGTH': 1000,
        'ai_prompt_template': '{emoji} **{title}**',
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_api_config_selects_complete_cheapvibecode_configuration(monkeypatch):
    clear_ai_environment(monkeypatch)
    monkeypatch.setenv('CHEAPVIBECODE_API_KEY', 'secret-value')
    monkeypatch.setenv('CHEAPVIBECODE_BASE_URL', 'https://cheapvibecode.ru/v1/')
    monkeypatch.setenv('CHEAPVIBECODE_MODEL', 'provider/model-id')
    monkeypatch.setenv('AI_MAX_TOKENS', '480')
    monkeypatch.setenv('AI_TRANSLATION_MAX_TOKENS', '760')
    monkeypatch.setenv('AI_TEMPERATURE', '0.25')

    config = APIConfig()
    ai_config = config.get_ai_config()

    assert config.get_ai_provider() == 'cheapvibecode'
    assert ai_config['base_url'] == 'https://cheapvibecode.ru/v1'
    assert ai_config['model'] == 'provider/model-id'
    assert ai_config['max_tokens'] == 480
    assert ai_config['translation_max_tokens'] == 760
    assert ai_config['temperature'] == 0.25
    assert 'secret-value' not in str(config.to_dict())


def test_api_config_does_not_activate_key_without_model(monkeypatch):
    clear_ai_environment(monkeypatch)
    monkeypatch.setenv('CHEAPVIBECODE_API_KEY', 'secret-value')
    monkeypatch.setenv('CHEAPVIBECODE_MODEL', '')

    config = APIConfig()

    assert config.has_cheapvibecode_provider() is False
    assert config.has_ai_provider() is False
    assert config.get_ai_provider() is None


def test_api_config_uses_cost_efficient_default_model(monkeypatch):
    clear_ai_environment(monkeypatch)
    monkeypatch.setenv('CHEAPVIBECODE_API_KEY', 'secret-value')

    config = APIConfig()

    assert config.cheapvibecode_model == 'qwen3.8-max'
    assert config.get_ai_provider() == 'cheapvibecode'


def test_api_config_clamps_invalid_token_and_temperature_values(monkeypatch):
    clear_ai_environment(monkeypatch)
    monkeypatch.setenv('AI_MAX_TOKENS', '0')
    monkeypatch.setenv('AI_TRANSLATION_MAX_TOKENS', 'not-a-number')
    monkeypatch.setenv('AI_TEMPERATURE', '7')

    config = APIConfig()

    assert config.ai_max_tokens == 1
    assert config.ai_translation_max_tokens == 800
    assert config.ai_temperature == 2.0


def test_handler_builds_cheapvibecode_client_without_logging_key(
    monkeypatch,
    capsys,
):
    captured = {}

    class FakeHTTPX:
        class Timeout:
            def __init__(self, *args, **kwargs):
                pass

        class Limits:
            def __init__(self, *args, **kwargs):
                pass

        @staticmethod
        def Client(**kwargs):
            return object()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    runtime_config = make_runtime_config()
    monkeypatch.setattr(ai_module, 'config', runtime_config)
    monkeypatch.setattr(ai_module, 'OPENAI_AVAILABLE', True)
    monkeypatch.setattr(ai_module, 'OpenAI', FakeOpenAI)
    monkeypatch.setattr(ai_module, 'httpx', FakeHTTPX)
    monkeypatch.setattr(ai_module, 'GEMINI_AVAILABLE', False)

    handler = ai_module.AIHandler()
    output = capsys.readouterr().out

    assert handler.cheapvibecode_client is not None
    assert captured['base_url'] == 'https://cheapvibecode.ru/v1'
    assert captured['api_key'] == 'hidden-test-key'
    assert 'hidden-test-key' not in output
    assert handler.stats.get_preferred_provider() == 'cheapvibecode'


def test_openai_compatible_summary_uses_configured_request_limits(monkeypatch):
    captured = {}

    class Completions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='📰 **Title**\n\nSummary text long enough to validate.'
                        )
                    )
                ]
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions()),
    )
    handler = ai_module.AIHandler.__new__(ai_module.AIHandler)
    runtime_config = make_runtime_config()
    monkeypatch.setattr(ai_module, 'config', runtime_config)

    result = asyncio.run(
        handler._call_openai_compatible(
            client,
            runtime_config.CHEAPVIBECODE_MODEL,
            'Title',
            'Article body ' * 20,
            '📰',
        )
    )

    assert result
    assert captured['model'] == 'provider/model-id'
    assert captured['max_tokens'] == 420
    assert captured['temperature'] == 0.2


def test_openai_compatible_translation_uses_separate_token_limit(monkeypatch):
    captured = {}

    class Completions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='Переведенный текст')
                    )
                ]
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=Completions()),
    )
    handler = ai_module.AIHandler.__new__(ai_module.AIHandler)
    runtime_config = make_runtime_config()
    monkeypatch.setattr(ai_module, 'config', runtime_config)

    result = asyncio.run(
        handler._translate_with_openai_compatible(
            client,
            runtime_config.CHEAPVIBECODE_MODEL,
            'English text',
            'en',
            'ru',
        )
    )

    assert result == 'Переведенный текст'
    assert captured['max_tokens'] == 700
    assert captured['temperature'] == 0.1


def test_retry_policy_retries_only_transient_errors(monkeypatch):
    runtime_config = make_runtime_config(AI_MAX_RETRIES=3, AI_BACKOFF_FACTOR=0)
    monkeypatch.setattr(ai_module, 'config', runtime_config)
    handler = ai_module.AIHandler.__new__(ai_module.AIHandler)

    class CompletionSequence:
        def __init__(self, errors):
            self.errors = list(errors)
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.errors:
                raise self.errors.pop(0)
            return SimpleNamespace(choices=[])

    transient = CompletionSequence([RuntimeError('429 rate limit')])
    transient_client = SimpleNamespace(
        chat=SimpleNamespace(completions=transient),
    )
    asyncio.run(
        handler._create_openai_chat_completion(
            transient_client,
            'model',
            [],
            0.1,
            10,
        )
    )
    assert transient.calls == 2

    permanent = CompletionSequence([RuntimeError('invalid model')])
    permanent_client = SimpleNamespace(
        chat=SimpleNamespace(completions=permanent),
    )
    try:
        asyncio.run(
            handler._create_openai_chat_completion(
                permanent_client,
                'model',
                [],
                0.1,
                10,
            )
        )
    except RuntimeError as error:
        assert str(error) == 'invalid model'
    else:
        raise AssertionError('Permanent error was not propagated')
    assert permanent.calls == 1


def test_secure_helper_transfers_key_only_through_stdin(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured['command'] = command
        captured['input'] = kwargs['input']
        return SimpleNamespace(returncode=0, stdout='[]\n', stderr='')

    monkeypatch.setattr(configure_cheapvibecode.subprocess, 'run', fake_run)
    args = argparse.Namespace(
        identity_file=tmp_path / 'identity',
        host='root@example.test',
    )

    output = configure_cheapvibecode.run_remote_python(
        args,
        'import sys; print(sys.stdin.read())',
        {'api_key': 'stdin-only-secret'},
    )

    assert output == '[]'
    assert 'stdin-only-secret' in captured['input']
    assert all('stdin-only-secret' not in argument for argument in captured['command'])


def test_secure_helper_preserves_environment_ownership(monkeypatch):
    captured = {}

    def fake_run_remote_python(args, source, payload):
        captured['source'] = source
        captured['payload'] = payload
        return '{"status": "ENV_UPDATED", "backup_path": "/safe/backup"}'

    monkeypatch.setattr(
        configure_cheapvibecode,
        'run_remote_python',
        fake_run_remote_python,
    )
    args = argparse.Namespace(
        app_path='/opt/example',
        base_url='https://cheapvibecode.ru/v1',
    )

    backup_path = configure_cheapvibecode.update_remote_environment(
        args,
        'stdin-only-secret',
        'qwen3.8-max',
    )

    source = captured['source']
    assert backup_path == '/safe/backup'
    assert 'os.stat(env_path, follow_symlinks=False)' in source
    assert 'os.chown(backup_path, original_stat.st_uid, original_stat.st_gid)' in source
    assert 'os.fchown(fd, original_stat.st_uid, original_stat.st_gid)' in source
    assert 'os.chown(env_path, original_stat.st_uid, original_stat.st_gid)' in source
    assert 'stdin-only-secret' not in source
    assert captured['payload']['api_key'] == 'stdin-only-secret'


def test_trading_system_uses_async_performance_metrics():
    from app.trading_system import TradingSystem

    metrics = SimpleNamespace(
        total_trades=7,
        win_rate=60.0,
        avg_pnl_per_trade_pct=1.25,
        total_pnl_usd=125.0,
    )

    class Performance:
        async def calculate_metrics(self):
            return metrics

    system = TradingSystem.__new__(TradingSystem)
    system.enabled = True
    system._initialized = True
    system.signal_generator = object()
    system.performance = Performance()

    result = asyncio.run(system.get_performance_stats())

    assert result == {
        'total_signals': 0,
        'total_trades': 7,
        'win_rate': 60.0,
        'avg_profit': 1.25,
        'total_pnl': 125.0,
    }