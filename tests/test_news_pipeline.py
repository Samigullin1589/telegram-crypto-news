import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault(
    'TELEGRAM_BOT_TOKEN',
    '123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi'
)
os.environ.setdefault('TELEGRAM_CHANNEL_ID', '-1001234567890')

from bot.news.components import ProcessorComponents
from bot.news.cycle import NewsCycleProcessor
from bot.news.deduplicator import ArticleDeduplicator
from bot.news.state import ProcessorState
from core.app_lifecycle.lifecycle import ApplicationLifecycle
from core.components.news_loader import NewsLoader
from core.monitor import MonitorInfrastructure
from core.tasks.manager import TaskManager


class TrackingDeduplicator(ArticleDeduplicator):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def mark_as_seen(self, article):
        self.events.append('seen')
        super().mark_as_seen(article)


class FakeAIHandler:
    def __init__(self, events):
        self.events = events

    async def analyze_article(self, article):
        self.events.append('analyze')
        return {'score': 91}

    async def get_summary(self, title, text, category):
        self.events.append('summary')
        return "📰 **Важная новость**\n\nКраткий разбор события на крипторынке.\n\n#крипто #новости", 'openai'


class FakeTelegramPoster:
    is_initialized = True

    def __init__(self, events, outcomes):
        self.events = events
        self.outcomes = list(outcomes)

    async def post(self, **kwargs):
        self.events.append('post')
        return self.outcomes.pop(0)


class FakeDatabase:
    def __init__(self, events):
        self.events = events
        self.saved = []

    async def save_article(self, **kwargs):
        self.events.append('save')
        self.saved.append(kwargs)
        return True


def make_cycle(post_outcomes):
    events = []
    database = FakeDatabase(events)
    components = ProcessorComponents(
        ai_handler=FakeAIHandler(events),
        database=database,
        telegram=FakeTelegramPoster(events, post_outcomes),
    )
    state = ProcessorState(
        core_initialized=True,
        database_initialized=True,
        baseline_loaded=True,
    )
    deduplicator = TrackingDeduplicator(events)
    cycle = NewsCycleProcessor(
        state=state,
        components=components,
        fetcher=SimpleNamespace(),
        deduplicator=deduplicator,
    )
    article = {
        'title': 'Bitcoin adoption reaches a new milestone',
        'url': 'https://example.com/news?id=tracking',
        'source': 'Example Feed',
        'category': 'bitcoin 🟠',
        'description': 'Bitcoin adoption continues to grow. ' * 10,
    }
    return cycle, state, deduplicator, database, events, article


def test_news_loader_accepts_run_cycle_contract():
    class Processor:
        is_initialized = True

        async def run_cycle(self):
            return None

    class LegacyProcessor:
        async def process(self):
            return None

        async def run(self):
            return None

    loader = NewsLoader(utils=None)

    assert loader._validate_processor(Processor()) is True
    assert loader._validate_processor(LegacyProcessor()) is False


def test_successful_publication_is_marked_and_saved_after_telegram():
    cycle, state, deduplicator, database, events, article = make_cycle([True])

    posted = asyncio.run(cycle._process_articles([article]))

    assert posted == 1
    assert state.posts_this_hour == 1
    assert state.total_articles_posted == 1
    assert deduplicator.is_duplicate(article) is True
    assert events == ['analyze', 'summary', 'post', 'seen', 'save']
    assert database.saved[0]['status'] == 'success'
    saved_article = database.saved[0]['article']
    assert saved_article['ai_provider'] == 'openai'
    assert saved_article['ai_score'] == 91
    assert saved_article['normalized_link'] == 'https://example.com/news'


def test_failed_telegram_post_is_not_marked_or_saved_and_can_retry():
    cycle, state, deduplicator, database, events, article = make_cycle([False, True])

    first_result = asyncio.run(cycle._process_articles([article]))

    assert first_result == 0
    assert state.posts_this_hour == 0
    assert deduplicator.is_duplicate(article) is False
    assert database.saved == []
    assert 'seen' not in events
    assert 'save' not in events

    events.clear()
    second_result = asyncio.run(cycle._process_articles([article]))

    assert second_result == 1
    assert deduplicator.is_duplicate(article) is True
    assert events == ['analyze', 'summary', 'post', 'seen', 'save']


def test_english_ai_failure_uses_fully_russian_local_fallback():
    cycle, _, _, _, _, article = make_cycle([True])

    class EnglishOnlyAI:
        async def analyze_article(self, article):
            return {'score': 80}

        async def get_summary(self, title, text, category):
            return (
                "📰 **English headline**\n\n"
                "Web server is returning an unknown error. Error code 520.",
                'cheapvibecode',
            )

    cycle.components.ai_handler = EnglishOnlyAI()
    article['description'] = (
        '<!DOCTYPE html><html>Cloudflare Ray ID: test. '
        'Web server is returning an unknown error.</html>'
    )

    message, provider, score = asyncio.run(cycle._build_message(article))

    assert 'English headline' not in message
    assert 'Bitcoin adoption' not in message
    assert 'Cloudflare' not in message
    assert 'Подробности доступны в первоисточнике' not in message
    assert 'Важная новость крипторынка' in message
    assert 'Проверенные подробности' in message
    assert provider is None
    assert score == 80


def test_monitor_runs_news_processor_through_periodic_runner(monkeypatch):
    captured = {}

    class FakeRunner:
        def __init__(self, *args):
            captured['args'] = args

        async def run(self):
            captured['ran'] = True

    monkeypatch.setattr('core.tasks.news_runner.NewsSystemRunner', FakeRunner)

    core = SimpleNamespace(
        health_monitor=object(),
        resource_monitor=object(),
        statistics=SimpleNamespace(increment_errors=lambda: None),
    )
    infrastructure = MonitorInfrastructure(core, SimpleNamespace())
    processor = object()

    asyncio.run(infrastructure._run_news_processor(processor))

    assert captured['args'] == (
        processor,
        core.health_monitor,
        core.resource_monitor,
        core.statistics,
        infrastructure.shutdown_event,
    )
    assert captured['ran'] is True


def test_task_manager_passes_complete_news_runner_dependencies(monkeypatch):
    processor = object()
    core = SimpleNamespace(
        health_monitor=object(),
        resource_monitor=object(),
        statistics=object(),
    )
    infrastructure = SimpleNamespace(shutdown_event=asyncio.Event())
    monitor = SimpleNamespace(
        component_manager=SimpleNamespace(news_processor=processor),
        core=core,
        infrastructure=infrastructure,
    )
    started_task = object()
    starter = AsyncMock(return_value=started_task)
    monkeypatch.setattr('core.tasks.manager.start_news_task', starter)
    manager = TaskManager(config=SimpleNamespace(), monitor=monitor)
    results = {}

    asyncio.run(manager._start_news_task(results))

    starter.assert_awaited_once_with(
        processor,
        core.health_monitor,
        core.resource_monitor,
        core.statistics,
        infrastructure.shutdown_event,
    )
    assert manager.news_task is started_task
    assert results['news']['status'] == 'started'


def test_lifecycle_uses_configured_uppercase_port():
    health_server = SimpleNamespace(start=AsyncMock())
    lifecycle = ApplicationLifecycle(
        config=SimpleNamespace(base=SimpleNamespace(PORT=9123)),
        monitor=SimpleNamespace(),
        db_manager=SimpleNamespace(),
        shutdown_manager=SimpleNamespace(),
        health_server=health_server,
    )

    asyncio.run(lifecycle._start_health_server())

    health_server.start.assert_awaited_once_with(port=9123)