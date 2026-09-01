import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from core.components.shutdown import ComponentShutdownManager
from core.monitor import MonitorInfrastructure


class StatisticsStub:
    def __init__(self):
        self.errors = 0

    def increment_errors(self):
        self.errors += 1


def make_infrastructure():
    core = SimpleNamespace(
        health_monitor=object(),
        resource_monitor=object(),
        statistics=StatisticsStub(),
    )
    return MonitorInfrastructure(core, SimpleNamespace(component_manager=None))


def test_bot_uses_async_polling_lifecycle_until_shutdown():
    async def scenario():
        infrastructure = make_infrastructure()
        events = []

        class Updater:
            async def start_polling(self):
                events.append('polling_started')

            async def stop(self):
                events.append('polling_stopped')

        class Application:
            updater = Updater()
            running = False

            async def post_init(self, application):
                assert application is self
                events.append('post_init')

            async def post_stop(self, application):
                assert application is self
                events.append('post_stop')

            async def post_shutdown(self, application):
                assert application is self
                events.append('post_shutdown')

            async def initialize(self):
                events.append('initialized')

            async def start(self):
                self.running = True
                events.append('started')

            async def stop(self):
                self.running = False
                events.append('stopped')

            async def shutdown(self):
                events.append('shutdown')

        task = asyncio.create_task(
            infrastructure._run_bot_application(Application())
        )
        await asyncio.sleep(0)

        assert task.done() is False
        assert events == [
            'initialized',
            'post_init',
            'polling_started',
            'started',
        ]

        infrastructure.shutdown_event.set()
        await task

        assert events == [
            'initialized',
            'post_init',
            'polling_started',
            'started',
            'polling_stopped',
            'stopped',
            'post_stop',
            'shutdown',
            'post_shutdown',
        ]

    asyncio.run(scenario())


def test_trading_system_uses_periodic_runner(monkeypatch):
    captured = {}

    class FakeRunner:
        def __init__(self, *args):
            captured['args'] = args

        async def run(self):
            captured['ran'] = True

    monkeypatch.setattr(
        'core.tasks.trading_runner.TradingSystemRunner',
        FakeRunner,
    )
    infrastructure = make_infrastructure()
    trading_system = object()

    asyncio.run(infrastructure._run_trading_system(trading_system))

    assert captured['args'] == (
        trading_system,
        infrastructure.core.health_monitor,
        infrastructure.core.resource_monitor,
        infrastructure.core.statistics,
        infrastructure.shutdown_event,
    )
    assert captured['ran'] is True


def test_supervisor_keeps_running_after_one_task_completes():
    async def scenario():
        infrastructure = make_infrastructure()

        async def completes_immediately():
            return None

        async def waits_for_shutdown():
            await infrastructure.shutdown_event.wait()

        infrastructure._running_tasks = [
            asyncio.create_task(completes_immediately(), name='OptionalTask'),
            asyncio.create_task(waits_for_shutdown(), name='LongRunningTask'),
        ]
        supervisor = asyncio.create_task(infrastructure.wait_for_completion())
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert supervisor.done() is False
        assert infrastructure.shutdown_event.is_set() is False

        infrastructure.shutdown_event.set()
        await supervisor
        await asyncio.gather(*infrastructure._running_tasks)

    asyncio.run(scenario())


def test_supervisor_requests_shutdown_when_task_fails():
    async def scenario():
        infrastructure = make_infrastructure()

        async def fails():
            raise RuntimeError('task failure')

        infrastructure._running_tasks = [
            asyncio.create_task(fails(), name='FailingTask')
        ]

        await infrastructure.wait_for_completion()

        assert infrastructure.shutdown_event.is_set() is True

    asyncio.run(scenario())


def test_component_cleanup_skips_stopped_bot_application():
    application = SimpleNamespace(running=False, stop=AsyncMock())
    manager = ComponentShutdownManager()

    asyncio.run(
        manager._stop_component(application, 'Bot Application', 'stop')
    )

    application.stop.assert_not_awaited()