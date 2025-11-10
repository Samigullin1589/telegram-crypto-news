"""
Content limits module
Лимиты контента и публикаций
"""

import logging
from typing import Dict
from .base import BaseFeatureConfig

logger = logging.getLogger(__name__)


class ContentLimits(BaseFeatureConfig):
    """
    Лимиты контента, публикаций и качества
    
    Управляет:
    - Лимитами публикаций в час
    - Порогами уверенности
    - Ограничениями текста
    - Настройками резюмирования
    """
    
    def __init__(self):
        """Инициализация лимитов контента"""
        
        # Лимиты публикаций (в час)
        self.posts_per_hour_cap = self.get_int_env('POSTS_PER_HOUR_CAP', 10)
        self.whale_posts_per_hour = self.get_int_env('WHALE_POSTS_PER_HOUR', 20)
        self.news_posts_per_hour = self.get_int_env('NEWS_POSTS_PER_HOUR', 15)
        self.trading_signals_per_hour = self.get_int_env('TRADING_SIGNALS_PER_HOUR', 5)
        self.analytics_posts_per_hour = self.get_int_env('ANALYTICS_POSTS_PER_HOUR', 8)
        
        # Пороги уверенности (0-100)
        self.min_confidence_score = self.get_int_env('MIN_CONFIDENCE_SCORE', 70)
        self.min_trading_confidence = self.get_int_env('MIN_TRADING_CONFIDENCE', 75)
        self.min_whale_confidence = self.get_int_env('MIN_WHALE_CONFIDENCE', 60)
        self.min_news_confidence = self.get_int_env('MIN_NEWS_CONFIDENCE', 65)
        self.min_analytics_confidence = self.get_int_env('MIN_ANALYTICS_CONFIDENCE', 70)
        
        # Ограничения текста
        self.max_article_text_length = self.get_int_env('MAX_ARTICLE_TEXT_LENGTH', 12000)
        self.max_summary_length = self.get_int_env('MAX_SUMMARY_LENGTH', 500)
        self.min_article_length = self.get_int_env('MIN_ARTICLE_LENGTH', 100)
        self.max_title_length = self.get_int_env('MAX_TITLE_LENGTH', 300)
        
        # Настройки резюмирования
        self.summary_enabled = self.get_bool_env('SUMMARY_ENABLED', True)
        self.max_summary_retries = self.get_int_env('MAX_SUMMARY_RETRIES', 2)
        self.summary_style = self.get_str_env('SUMMARY_STYLE', 'concise')
        self.summary_language = self.get_str_env('SUMMARY_LANGUAGE', 'ru')
        
        # Качество контента
        self.duplicate_check_enabled = self.get_bool_env('DUPLICATE_CHECK_ENABLED', True)
        self.content_quality_check = self.get_bool_env('CONTENT_QUALITY_CHECK', True)
        self.spam_filter_enabled = self.get_bool_env('SPAM_FILTER_ENABLED', True)
        
        # Логирование конфигурации
        self._log_configuration()
    
    def _log_configuration(self):
        """Логирование конфигурации"""
        logger.debug(f"[CONTENT] Post limits: news={self.news_posts_per_hour}/h, "
                    f"whale={self.whale_posts_per_hour}/h, "
                    f"trading={self.trading_signals_per_hour}/h")
        logger.debug(f"[CONTENT] Confidence thresholds: general={self.min_confidence_score}, "
                    f"trading={self.min_trading_confidence}, "
                    f"whale={self.min_whale_confidence}")
    
    def get_posts_limit(self, feature: str) -> int:
        """
        Получение лимита публикаций для конкретного модуля
        
        Args:
            feature: Название модуля
            
        Returns:
            int: Лимит публикаций в час
        """
        limits_map = {
            'whale': self.whale_posts_per_hour,
            'whale_alerts': self.whale_posts_per_hour,
            'news': self.news_posts_per_hour,
            'trading': self.trading_signals_per_hour,
            'analytics': self.analytics_posts_per_hour
        }
        
        return limits_map.get(feature.lower(), self.posts_per_hour_cap)
    
    def get_confidence_threshold(self, feature: str) -> int:
        """
        Получение порога уверенности для конкретного модуля
        
        Args:
            feature: Название модуля
            
        Returns:
            int: Минимальный порог уверенности (0-100)
        """
        thresholds_map = {
            'whale': self.min_whale_confidence,
            'whale_alerts': self.min_whale_confidence,
            'news': self.min_news_confidence,
            'trading': self.min_trading_confidence,
            'analytics': self.min_analytics_confidence
        }
        
        return thresholds_map.get(feature.lower(), self.min_confidence_score)
    
    def validate_confidence(self, score: float, feature: str = 'general') -> bool:
        """
        Проверка соответствия уверенности порогу
        
        Args:
            score: Оценка уверенности
            feature: Название модуля
            
        Returns:
            bool: True если оценка выше порога
        """
        threshold = self.get_confidence_threshold(feature)
        return score >= threshold
    
    def get_all_limits(self) -> Dict[str, int]:
        """
        Получение всех лимитов
        
        Returns:
            Dict: Словарь всех лимитов
        """
        return {
            'posts_per_hour': self.posts_per_hour_cap,
            'whale_posts_per_hour': self.whale_posts_per_hour,
            'news_posts_per_hour': self.news_posts_per_hour,
            'trading_signals_per_hour': self.trading_signals_per_hour,
            'analytics_posts_per_hour': self.analytics_posts_per_hour,
            'min_confidence': self.min_confidence_score,
            'min_trading_confidence': self.min_trading_confidence,
            'min_whale_confidence': self.min_whale_confidence,
            'min_news_confidence': self.min_news_confidence,
            'min_analytics_confidence': self.min_analytics_confidence,
            'article_length': self.max_article_text_length,
            'summary_length': self.max_summary_length,
            'min_article_length': self.min_article_length,
            'max_title_length': self.max_title_length
        }


__all__ = ['ContentLimits']