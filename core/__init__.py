# core/__init__.py
"""
Core system components
"""

# ИСПРАВЛЕНО: Убран импорт IntegratedCryptoMonitor
# для избежания циклических зависимостей при инициализации модуля.
# 
# IntegratedCryptoMonitor импортируется только там, где используется:
# - В core.initialization.monitor.MonitorInitializer (с lazy import)
# 
# Прямой импорт на уровне пакета создавал цикл:
# core.__init__ → core.monitor → core.components → ... → core
#
# Такая архитектура обеспечивает:
# - Отсутствие циклических зависимостей
# - Правильный порядок инициализации компонентов
# - Возможность использовать IntegratedCryptoMonitor через MonitorInitializer

from core.startup import StartupValidator
from core.rate_limiter import ChainRateLimiter
from core.resource_monitor import ResourceMonitor
from core.health_monitor import SystemHealthMonitor

__all__ = [
    'StartupValidator',
    'ChainRateLimiter',
    'ResourceMonitor',
    'SystemHealthMonitor'
]