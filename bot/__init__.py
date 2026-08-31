# bot/__init__.py
"""
Crypto Compass Bot - Intelligent News Aggregator
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Crypto Compass Team"

__all__ = [
    "AIHandler",
    "Config",
    "ContentParser",
    "DatabaseManager",
    "NewsProcessor",
    "TelegramPoster",
]


def __getattr__(name):
    """Загружать тяжёлые/опциональные компоненты только по запросу."""
    modules = {
        'AIHandler': ('.ai_handler', 'AIHandler'),
        'Config': ('.config', 'Config'),
        'ContentParser': ('.content_parser', 'ContentParser'),
        'DatabaseManager': ('.database', 'DatabaseManager'),
        'NewsProcessor': ('.processor', 'NewsProcessor'),
        'TelegramPoster': ('.telegram_poster', 'TelegramPoster'),
    }
    if name not in modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module_name, attribute_name = modules[name]
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value