import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from core.health_server import HealthServer
from core.monitor import MonitorInfrastructure


def test_health_server_accepts_application_dependencies_and_runtime_port(monkeypatch):
    created = {}

    class FakeSite:
        def __init__(self, runner, host, port):
            created['args'] = (runner, host, port)
            self.start = AsyncMock()

    monkeypatch.setattr('core.health_server.web.TCPSite', FakeSite)
    monitor = object()
    config = object()
    server = HealthServer(monitor=monitor, config=config)

    asyncio.run(server.start(port='9123'))

    assert server.monitor is monitor
    assert server.config is config
    assert server.port == 9123
    assert created['args'][1:] == ('0.0.0.0', 9123)
    server.site.start.assert_awaited_once_with()
    asyncio.run(server.stop())


def test_monitor_http_server_uses_metrics_port(monkeypatch):
    captured = {}

    class FakeHTTPServer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv('PORT', '8123')
    monkeypatch.setenv('METRICS_PORT', '9191')
    monkeypatch.setattr('core.monitor.HTTPServer', FakeHTTPServer)
    core = SimpleNamespace(
        health_monitor=object(),
        resource_monitor=object(),
        rate_limiter=object(),
    )
    infrastructure = MonitorInfrastructure(core, SimpleNamespace(component_manager=None))

    result = asyncio.run(infrastructure.initialize_http_server())

    assert result is True
    assert captured['port'] == 9191
    assert captured['port'] != int('8123')