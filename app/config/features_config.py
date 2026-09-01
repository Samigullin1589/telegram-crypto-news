"""
Features Configuration Module v3.0
Модульная система конфигурации функциональности
"""

import logging
from typing import Dict, Any

from .features import (
    FeatureFlags,
    ContentLimits,
    TimingConfig,
    ImageConfig,
    TradingFeatures,
    WhaleFeatures
)

logger = logging.getLogger(__name__)


class FeaturesConfig:
    """
    Главный класс конфигурации функций
    
    Объединяет все модули конфигурации:
    - Флаги включения модулей
    - Лимиты контента
    - Настройки таймингов
    - Конфигурация изображений
    - Настройки торговли
    - Настройки whale мониторинга
    
    Версия 3.0:
    - Модульная архитектура
    - Метод is_enabled() для проверки модулей
    - Единая точка доступа ко всем настройкам
    - Полная обратная совместимость
    """
    
    def __init__(self):
        """Инициализация конфигурации"""
        
        logger.info("="*80)
        logger.info("⚙️  INITIALIZING FEATURES CONFIG v3.0")
        logger.info("="*80)
        
        # Инициализация модулей
        self.flags = FeatureFlags()
        self.content = ContentLimits()
        self.timing = TimingConfig()
        self.image = ImageConfig()
        self.trading = TradingFeatures()
        self.whale = WhaleFeatures()
        
        # Обратная совместимость: копирование атрибутов
        self._setup_legacy_attributes()
        
        # Финальная валидация
        self._validate_configuration()
        
        logger.info("="*80)
        logger.info("✅ FEATURES CONFIG INITIALIZED")
        logger.info("="*80)
        logger.info("")
    
    def _setup_legacy_attributes(self):
        """Установка атрибутов для обратной совместимости"""
        
        # Флаги модулей
        self.whale_enabled = self.flags.whale_enabled
        self.news_enabled = self.flags.news_enabled
        self.analytics_enabled = self.flags.analytics_enabled
        self.trading_enabled = self.flags.trading_enabled
        self.hyperliquid_enabled = self.flags.hyperliquid_enabled
        
        # Лимиты контента
        self.posts_per_hour_cap = self.content.posts_per_hour_cap
        self.whale_posts_per_hour = self.content.whale_posts_per_hour
        self.trading_signals_per_hour = self.content.trading_signals_per_hour
        self.min_confidence_score = self.content.min_confidence_score
        self.min_news_confidence = self.content.min_news_confidence
        self.news_publish_cooldown_seconds = (
            self.content.news_publish_cooldown_seconds
        )
        self.min_trading_confidence = self.content.min_trading_confidence
        self.min_whale_confidence = self.content.min_whale_confidence
        self.max_article_text_length = self.content.max_article_text_length
        self.max_summary_length = self.content.max_summary_length
        self.max_summary_retries = self.content.max_summary_retries
        self.summary_enabled = self.content.summary_enabled
        
        # Таймаут
        self.fetch_interval = self.timing.fetch_interval
        self.news_check_interval = self.timing.news_check_interval
        self.whale_check_interval = self.timing.whale_check_interval
        self.trading_check_interval = self.timing.trading_check_interval
        self.post_delay_seconds = self.timing.post_delay_seconds
        self.idle_delay_seconds = self.timing.idle_delay_seconds
        self.rate_limit_delay_seconds = self.timing.rate_limit_delay_seconds
        self.feed_fetch_timeout = self.timing.feed_fetch_timeout
        self.blockchain_request_timeout = self.timing.blockchain_request_timeout
        self.trading_analysis_timeout = self.timing.trading_analysis_timeout
        
        # Изображения
        self.min_image_width = self.image.min_image_width
        self.min_image_height = self.image.min_image_height
        self.max_image_size_mb = self.image.max_image_size_mb
        self.image_quality = self.image.image_quality
        self.image_compression_enabled = self.image.image_compression_enabled
        self.image_check_timeout = self.image.image_check_timeout
        self.image_partial_read_bytes = self.image.image_partial_read_bytes
        
        # Trading
        self.trading_dry_run = self.trading.dry_run
        self.trading_max_signals_per_day = self.trading.max_signals_per_day
        self.trading_max_open_positions = self.trading.max_open_positions
        self.trading_default_stop_loss = self.trading.default_stop_loss
        self.trading_default_take_profit = self.trading.default_take_profit
        
        # Whale
        self.whale_min_usd_threshold = self.whale.min_usd_threshold
        self.whale_mega_threshold = self.whale.mega_threshold
    
    def _validate_configuration(self):
        """Валидация конфигурации"""
        
        # Проверка что хотя бы один модуль включен
        if not self.flags.is_any_enabled():
            logger.warning("⚠️  WARNING: All modules are disabled!")
        
        # Проверка критичных зависимостей
        if self.trading_enabled and not self.whale_enabled:
            logger.warning("⚠️  Trading enabled without whale monitoring")
        
        # Проверка разумности лимитов
        if self.posts_per_hour_cap > 100:
            logger.warning(f"⚠️  Very high post limit: {self.posts_per_hour_cap}/hour")
        
        if self.min_confidence_score < 50:
            logger.warning(f"⚠️  Low confidence threshold: {self.min_confidence_score}")
        
        logger.info(f"✅ Configuration validated: {self.flags.get_enabled_count()}/5 modules active")
    
    def is_enabled(self, feature_name: str) -> bool:
        """
        Проверка включен ли модуль
        
        Args:
            feature_name: Название модуля
            
        Returns:
            bool: True если модуль включен
            
        Examples:
            >>> config.is_enabled('news')
            True
            >>> config.is_enabled('trading')
            True
        """
        return self.flags.is_enabled(feature_name)
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """
        Получение всех модулей и их статусов
        
        Returns:
            Dict[str, bool]: Словарь модулей
        """
        return self.flags.get_enabled_features()
    
    def is_any_feature_enabled(self) -> bool:
        """
        Проверка включен ли хотя бы один модуль
        
        Returns:
            bool: True если есть активные модули
        """
        return self.flags.is_any_enabled()
    
    def get_content_limits(self) -> Dict[str, Any]:
        """Получение лимитов контента"""
        return self.content.get_all_limits()
    
    def get_image_config(self) -> Dict[str, Any]:
        """Получение конфигурации изображений"""
        return self.image.to_dict()
    
    def get_timing_config(self) -> Dict[str, int]:
        """Получение конфигурации таймингов"""
        return self.timing.get_all_timings()
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Получение конфигурации торговли"""
        return self.trading.to_dict()
    
    def get_whale_config(self) -> Dict[str, Any]:
        """Получение конфигурации whale мониторинга"""
        return self.whale.to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Полная конфигурация в виде словаря
        
        Returns:
            Dict: Вся конфигурация
        """
        return {
            'enabled_features': self.get_enabled_features(),
            'content_limits': self.get_content_limits(),
            'image_config': self.get_image_config(),
            'timing': self.get_timing_config(),
            'trading': self.get_trading_config(),
            'whale': self.get_whale_config()
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        enabled = self.flags.get_enabled_names()
        return f"FeaturesConfig(enabled={enabled})"


__all__ = ['FeaturesConfig']