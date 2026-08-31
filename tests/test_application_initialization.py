import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.config.database_config import DatabaseConfig
from core.application import ApplicationComponents, ComponentInitializer
from core.shutdown import ShutdownManager


def test_application_wires_existing_database_manager_into_shutdown(monkeypatch):
    captured = {}

    class FakeShutdownManager:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr('core.application.ShutdownManager', FakeShutdownManager)
    components = ApplicationComponents()
    components.db_manager = object()
    components.monitor = object()
    initializer = ComponentInitializer(components)

    result = asyncio.run(initializer._init_shutdown_manager())

    assert result is True
    assert captured == {'db_manager': components.db_manager}


def test_shutdown_manager_closes_direct_database_manager():
    db_manager = SimpleNamespace(
        is_initialized=True,
        shutdown=AsyncMock(return_value={'status': 'shutdown_complete'}),
    )
    manager = ShutdownManager(db_manager=db_manager)

    result = asyncio.run(manager._close_database())

    assert result is True
    db_manager.shutdown.assert_awaited_once_with()


def test_database_config_loads_from_environment_without_fallback_import(monkeypatch):
    monkeypatch.setenv('DATABASE_ENGINE', 'sqlite')
    monkeypatch.setenv('DATABASE_NAME', 'data/test.db')

    config = DatabaseConfig.from_env()

    assert isinstance(config, DatabaseConfig)
    assert config.database == 'data/test.db'
    assert config.port == 0