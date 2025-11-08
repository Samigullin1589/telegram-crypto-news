# app/config/features_config.py
"""
Features Configuration Module v2.0
Улучшенная конфигурация функциональных возможностей
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FeaturesConfig:
    """
    Конфигурация функций и возможностей бота
    
    Улучшения v2.0:
    - Trading включен по умолчанию
    - Лучшая структура настроек
    - Группировка связанных параметров
    """
    
    def __init__(self):
        """Инициализация конфигурации функций"""
        
        # Основные модули (все включены по умолчанию)
        self.whale_enabled = self._get_bool_env('WHALE_ENABLED', True)
        self.news_enabled = self._get_bool_env('NEWS_ENABLED', True)
        self.analytics_enabled = self._get_bool_env('ANALYTICS_ENABLED', True)
        self.trading_enabled = self._get_bool_env('TRADING_ENABLED', True)
        self.hyperliquid_enabled = self._get_bool_env('HYPERLIQUID_ENABLED', False)
        
        # Интервалы обновления
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', '300'))
        self.news_check_interval = self.fetch_interval
        self.whale_check_interval = int(os.getenv('WHALE_CHECK_INTERVAL', '60'))
        self.trading_check_interval = int(os.getenv('TRADING_CHECK_INTERVAL', '300'))
        
        # Лимиты публикаций
        self.posts_per_hour_cap = int(os.getenv('POSTS_PER_HOUR_CAP', '10'))
        self.whale_posts_per_hour = int(os.getenv('WHALE_POSTS_PER_HOUR', '20'))
        self.trading_signals_per_hour = int(os.getenv('TRADING_SIGNALS_PER_HOUR', '5'))
        
        # Пороги уверенности
        self.min_confidence_score = int(os.getenv('MIN_CONFIDENCE_SCORE', '70'))
        self.min_trading_confidence = int(os.getenv('MIN_TRADING_CONFIDENCE', '75'))
        self.min_whale_confidence = int(os.getenv('MIN_WHALE_CONFIDENCE', '60'))
        
        # Задержки
        self.post_delay_seconds = int(os.getenv('POST_DELAY_SECONDS', '900'))
        self.idle_delay_seconds = int(os.getenv('IDLE_DELAY_SECONDS', '300'))
        self.rate_limit_delay_seconds = 60
        
        # Контент
        self.max_article_text_length = 12000
        self.max_summary_length = 500
        self.max_summary_retries = 2
        self.summary_enabled = True
        
        # Изображения
        self.min_image_width = int(os.getenv('MIN_IMAGE_WIDTH', '400'))
        self.min_image_height = int(os.getenv('MIN_IMAGE_HEIGHT', '200'))
        self.max_image_size_mb = int(os.getenv('MAX_IMAGE_SIZE_MB', '10'))
        self.image_quality = 85
        self.image_compression_enabled = True
        self.image_check_timeout = 10
        self.image_partial_read_bytes = 8192
        
        # Trading специфичные настройки
        self.trading_dry_run = self._get_bool_env('TRADING_DRY_RUN', True)
        self.trading_max_signals_per_day = int(os.getenv('TRADING_MAX_SIGNALS_PER_DAY', '10'))
        self.trading_max_open_positions = int(os.getenv('TRADING_MAX_OPEN_POSITIONS', '5'))
        self.trading_default_stop_loss = float(os.getenv('TRADING_DEFAULT_STOP_LOSS', '3.0'))
        self.trading_default_take_profit = float(os.getenv('TRADING_DEFAULT_TAKE_PROFIT', '5.0'))
        
        # Whale специфичные настройки
        self.whale_min_usd_threshold = float(os.getenv('WHALE_MIN_USD_THRESHOLD', '100000'))
        self.whale_mega_threshold = float(os.getenv('WHALE_MEGA_THRESHOLD', '1000000'))
        
        # Timeout настройки
        self.feed_fetch_timeout = 30
        self.blockchain_request_timeout = 30
        self.trading_analysis_timeout = 60
        
        # Логирование конфигурации
        self._log_configuration()
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """
        Получение boolean переменной из окружения
        
        Args:
            key: Название переменной
            default: Значение по умолчанию
            
        Returns:
            Boolean значение
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    def _log_configuration(self):
        """Логирование включенных функций"""
        features = {
            'Whale Alerts': self.whale_enabled,
            'News': self.news_enabled,
            'Analytics': self.analytics_enabled,
            'Trading': self.trading_enabled,
            'Hyperliquid': self.hyperliquid_enabled
        }
        
        enabled = [name for name, status in features.items() if status]
        disabled = [name for name, status in features.items() if not status]
        
        if enabled:
            logger.info(f"✅ [FEATURES] Enabled: {', '.join(enabled)}")
        
        if disabled:
            logger.debug(f"⚠️  [FEATURES] Disabled: {', '.join(disabled)}")
        
        if not any(features.values()):
            logger.warning("⚠️  [FEATURES] All features are disabled!")
        
        # Специальные режимы
        if self.trading_enabled and self.trading_dry_run:
            logger.info("🧪 [TRADING] Running in DRY RUN mode")
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """
        Получение статуса всех функций
        
        Returns:
            Dict с флагами включения
        """
        return {
            'whale_alerts': self.whale_enabled,
            'news': self.news_enabled,
            'analytics': self.analytics_enabled,
            'trading': self.trading_enabled,
            'hyperliquid': self.hyperliquid_enabled
        }
    
    def is_any_feature_enabled(self) -> bool:
        """
        Проверка включена ли хотя бы одна функция
        
        Returns:
            True если есть хотя бы одна активная функция
        """
        return any(self.get_enabled_features().values())
    
    def get_content_limits(self) -> Dict[str, int]:
        """Получение лимитов контента"""
        return {
            'posts_per_hour': self.posts_per_hour_cap,
            'whale_posts_per_hour': self.whale_posts_per_hour,
            'trading_signals_per_hour': self.trading_signals_per_hour,
            'min_confidence': self.min_confidence_score,
            'min_trading_confidence': self.min_trading_confidence,
            'min_whale_confidence': self.min_whale_confidence,
            'article_length': self.max_article_text_length,
            'summary_length': self.max_summary_length
        }
    
    def get_image_config(self) -> Dict[str, Any]:
        """Получение конфигурации изображений"""
        return {
            'min_width': self.min_image_width,
            'min_height': self.min_image_height,
            'max_size_mb': self.max_image_size_mb,
            'quality': self.image_quality,
            'compression_enabled': self.image_compression_enabled,
            'check_timeout': self.image_check_timeout
        }
    
    def get_timing_config(self) -> Dict[str, int]:
        """Получение конфигурации таймингов"""
        return {
            'fetch_interval': self.fetch_interval,
            'news_check_interval': self.news_check_interval,
            'whale_check_interval': self.whale_check_interval,
            'trading_check_interval': self.trading_check_interval,
            'post_delay': self.post_delay_seconds,
            'idle_delay': self.idle_delay_seconds,
            'rate_limit_delay': self.rate_limit_delay_seconds
        }
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Получение конфигурации trading"""
        return {
            'enabled': self.trading_enabled,
            'dry_run': self.trading_dry_run,
            'max_signals_per_day': self.trading_max_signals_per_day,
            'max_open_positions': self.trading_max_open_positions,
            'default_stop_loss': self.trading_default_stop_loss,
            'default_take_profit': self.trading_default_take_profit,
            'min_confidence': self.min_trading_confidence,
            'check_interval': self.trading_check_interval,
            'signals_per_hour': self.trading_signals_per_hour
        }
    
    def get_whale_config(self) -> Dict[str, Any]:
        """Получение конфигурации whale monitoring"""
        return {
            'enabled': self.whale_enabled,
            'min_usd_threshold': self.whale_min_usd_threshold,
            'mega_threshold': self.whale_mega_threshold,
            'posts_per_hour': self.whale_posts_per_hour,
            'min_confidence': self.min_whale_confidence,
            'check_interval': self.whale_check_interval
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация в словарь
        
        Returns:
            Полная конфигурация в виде словаря
        """
        return {
            'enabled_features': self.get_enabled_features(),
            'content_limits': self.get_content_limits(),
            'image_config': self.get_image_config(),
            'timing': self.get_timing_config(),
            'trading': self.get_trading_config(),
            'whale': self.get_whale_config()
        }


__all__ = ['FeaturesConfig']