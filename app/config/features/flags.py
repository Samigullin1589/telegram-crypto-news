"""
Feature flags module
Флаги включения/отключения модулей
"""

import logging
from typing import Dict
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class FeatureFlags(BaseFeatureConfig):
    """
    Флаги включения модулей системы
    
    Управляет включением/отключением основных компонентов:
    - Whale alerts (мониторинг крупных транзакций)
    - News (агрегация новостей)
    - Analytics (аналитика)
    - Trading (торговые сигналы)
    - Hyperliquid (интеграция с биржей)
    """
    
    # Имена модулей
    WHALE = 'whale'
    NEWS = 'news'
    ANALYTICS = 'analytics'
    TRADING = 'trading'
    HYPERLIQUID = 'hyperliquid'
    
    # Альтернативные имена (для обратной совместимости)
    WHALE_ALERTS = 'whale_alerts'
    
    def __init__(self):
        """Инициализация флагов модулей"""
        
        # Основные модули
        self.whale_enabled = self.get_bool_env('WHALE_ENABLED', True)
        self.news_enabled = self.get_bool_env('NEWS_ENABLED', True)
        self.analytics_enabled = self.get_bool_env('ANALYTICS_ENABLED', True)
        self.trading_enabled = self.get_bool_env('TRADING_ENABLED', True)
        self.hyperliquid_enabled = self.get_bool_env('HYPERLIQUID_ENABLED', False)
        
        # Логирование статуса
        self._log_status()
    
    def _log_status(self):
        """Логирование статуса модулей"""
        modules = {
            'Whale Alerts': self.whale_enabled,
            'News Bot': self.news_enabled,
            'Analytics': self.analytics_enabled,
            'Trading System': self.trading_enabled,
            'Hyperliquid': self.hyperliquid_enabled
        }
        
        enabled = [name for name, status in modules.items() if status]
        disabled = [name for name, status in modules.items() if not status]
        
        if enabled:
            logger.info(f"✅ [FEATURES] Enabled modules: {', '.join(enabled)}")
        
        if disabled:
            logger.info(f"⚠️  [FEATURES] Disabled modules: {', '.join(disabled)}")
        
        if not any(modules.values()):
            logger.warning("⚠️  [FEATURES] WARNING: All modules are disabled!")
    
    def is_enabled(self, feature_name: str) -> bool:
        """
        Проверка включен ли указанный модуль
        
        Args:
            feature_name: Название модуля
            
        Returns:
            bool: True если модуль включен
            
        Raises:
            ValueError: Если модуль не существует
        """
        # Нормализация имени
        feature_name = feature_name.lower().strip()
        
        # Маппинг альтернативных имен
        feature_map = {
            self.WHALE: 'whale_enabled',
            self.WHALE_ALERTS: 'whale_enabled',
            'whale_alerts': 'whale_enabled',
            'whales': 'whale_enabled',
            
            self.NEWS: 'news_enabled',
            'news_bot': 'news_enabled',
            
            self.ANALYTICS: 'analytics_enabled',
            'analytic': 'analytics_enabled',
            
            self.TRADING: 'trading_enabled',
            'trade': 'trading_enabled',
            'trading_system': 'trading_enabled',
            
            self.HYPERLIQUID: 'hyperliquid_enabled',
            'hyper_liquid': 'hyperliquid_enabled',
            'hl': 'hyperliquid_enabled'
        }
        
        # Получение атрибута
        attr_name = feature_map.get(feature_name)
        if attr_name is None:
            logger.warning(f"Unknown feature: {feature_name}")
            return False
        
        return getattr(self, attr_name, False)
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """
        Получение словаря всех модулей и их статусов
        
        Returns:
            Dict[str, bool]: Словарь {модуль: статус}
        """
        return {
            self.WHALE_ALERTS: self.whale_enabled,
            self.NEWS: self.news_enabled,
            self.ANALYTICS: self.analytics_enabled,
            self.TRADING: self.trading_enabled,
            self.HYPERLIQUID: self.hyperliquid_enabled
        }
    
    def is_any_enabled(self) -> bool:
        """
        Проверка включен ли хотя бы один модуль
        
        Returns:
            bool: True если есть хотя бы один активный модуль
        """
        return any(self.get_enabled_features().values())
    
    def get_enabled_count(self) -> int:
        """
        Получение количества включенных модулей
        
        Returns:
            int: Количество активных модулей
        """
        return sum(1 for enabled in self.get_enabled_features().values() if enabled)
    
    def get_enabled_names(self) -> list:
        """
        Получение списка имен включенных модулей
        
        Returns:
            list: Список имен активных модулей
        """
        return [
            name for name, enabled in self.get_enabled_features().items()
            if enabled
        ]


__all__ = ['FeatureFlags']