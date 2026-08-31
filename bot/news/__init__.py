# bot/news/__init__.py
"""
News Processing System v6.0
Модульная система обработки новостей
"""

__all__ = ['NewsProcessor']

__version__ = '6.0.0'


def __getattr__(name):
    if name != 'NewsProcessor':
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .processor import NewsProcessor

    globals()['NewsProcessor'] = NewsProcessor
    return NewsProcessor