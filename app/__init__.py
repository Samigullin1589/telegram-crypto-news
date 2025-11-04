"""
One-Channel Whale Monitor + Crypto News Bot
Интегрированная система мониторинга криптовалютного рынка
"""

__version__ = "2.0.0"
__author__ = "Crypto Compass Team"

# Импортируем config и экспортируем его как settings для обратной совместимости
from app.config import config, config as settings

__all__ = ['config', 'settings']