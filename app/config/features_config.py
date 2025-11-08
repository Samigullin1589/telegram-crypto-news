# app/config/features_config.py
"""
Features Configuration Module
Конфигурация функциональных возможностей бота
"""

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FeaturesConfig:
    """
    Конфигурация функций и возможностей бота
    Управление включением/отключением модулей
    """
    
    def __init__(self):
        """Инициализация конфигурации функций"""
        
        self.whale_enabled = self._get_bool_env('WHALE_ENABLED', True)
        self.news_enabled = self._get_bool_env('NEWS_ENABLED', True)
        self.analytics_enabled = self._get_bool_env('ANALYTICS_ENABLED', True)
        self.trading_enabled = self._get_bool_env('TRADING_ENABLED', False)
        self.hyperliquid_enabled = self._get_bool_env('HYPERLIQUID_ENABLED', False)
        
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', '300'))
        self.news_check_interval = self.fetch_interval
        
        self.posts_per_hour_cap = int(os.getenv('POSTS_PER_HOUR_CAP', '3'))
        self.min_confidence_score = int(os.getenv('MIN_CONFIDENCE_SCORE', '70'))
        
        self.post_delay_seconds = int(os.getenv('POST_DELAY_SECONDS', '900'))
        self.idle_delay_seconds = int(os.getenv('IDLE_DELAY_SECONDS', '300'))
        self.feed_fetch_timeout = 30
        self.rate_limit_delay_seconds = 60
        
        self.max_article_text_length = 12000
        self.max_summary_length = 500
        self.max_summary_retries = 2
        self.summary_enabled = True
        
        self.min_image_width = int(os.getenv('MIN_IMAGE_WIDTH', '400'))
        self.min_image_height = int(os.getenv('MIN_IMAGE_HEIGHT', '200'))
        self.max_image_size_mb = int(os.getenv('MAX_IMAGE_SIZE_MB', '10'))
        self.image_check_timeout = 10
        self.image_partial_read_bytes = 8192
        self.image_quality = 85
        self.image_compression_enabled = True
        
        self._log_enabled_features()
    
    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Получение boolean переменной"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _log_enabled_features(self):
        """Логирование включенных функций"""
        features = {
            'Whale Alerts': self.whale_enabled,
            'News': self.news_enabled,
            'Analytics': self.analytics_enabled,
            'Trading': self.trading_enabled,
            'Hyperliquid': self.hyperliquid_enabled
        }
        
        enabled = [name for name, status in features.items() if status]
        
        logger.info(f"✅ [FEATURES] Включено: {', '.join(enabled)}")
        
        if not any(features.values()):
            logger.warning("⚠️ [FEATURES] Все функции отключены!")
    
    def get_enabled_features(self) -> Dict[str, bool]:
        """Получение статуса всех функций"""
        return {
            'whale_alerts': self.whale_enabled,
            'news': self.news_enabled,
            'analytics': self.analytics_enabled,
            'trading': self.trading_enabled,
            'hyperliquid': self.hyperliquid_enabled
        }
    
    def is_any_feature_enabled(self) -> bool:
        """Проверка включена ли хотя бы одна функция"""
        return any(self.get_enabled_features().values())
    
    def get_content_limits(self) -> Dict[str, int]:
        """Получение лимитов контента"""
        return {
            'posts_per_hour': self.posts_per_hour_cap,
            'min_confidence': self.min_confidence_score,
            'article_length': self.max_article_text_length,
            'summary_length': self.max_summary_length
        }
    
    def get_image_config(self) -> Dict[str, any]:
        """Получение конфигурации изображений"""
        return {
            'min_width': self.min_image_width,
            'min_height': self.min_image_height,
            'max_size_mb': self.max_image_size_mb,
            'quality': self.image_quality,
            'compression_enabled': self.image_compression_enabled
        }
    
    def get_timing_config(self) -> Dict[str, int]:
        """Получение конфигурации таймингов"""
        return {
            'fetch_interval': self.fetch_interval,
            'news_check_interval': self.news_check_interval,
            'post_delay': self.post_delay_seconds,
            'idle_delay': self.idle_delay_seconds,
            'rate_limit_delay': self.rate_limit_delay_seconds
        }
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'enabled_features': self.get_enabled_features(),
            'content_limits': self.get_content_limits(),
            'image_config': self.get_image_config(),
            'timing': self.get_timing_config()
        }