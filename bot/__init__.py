# bot/__init__.py
"""
Crypto Compass Bot - Intelligent News Aggregator
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Crypto Compass Team"

# Экспорты для удобного импорта
from .ai_handler import AIHandler
from .config import Config
from .content_parser import ContentParser
from .database import DatabaseManager
from .processor import NewsProcessor
from .telegram_poster import TelegramPoster

__all__ = [
    "AIHandler",
    "Config",
    "ContentParser",
    "DatabaseManager",
    "NewsProcessor",
    "TelegramPoster",
]