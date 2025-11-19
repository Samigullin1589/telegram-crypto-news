# app/config/aliases.py
"""
Config Aliases Setup
Настройка алиасов для обратной совместимости
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config

logger = logging.getLogger(__name__)


class ConfigAliases:
    """
    Настройка алиасов конфигурации
    
    Создает алиасы для обеспечения обратной совместимости
    со старым кодом
    """
    
    def __init__(self, config_instance: 'Config'):
        """
        Инициализация
        
        Args:
            config_instance: Экземпляр Config
        """
        self.config = config_instance
    
    def setup_all(self):
        """Настройка всех алиасов"""
        self._setup_news_alias()
        self._setup_trading_alias()
        self._setup_telegram_token_alias()
        self._setup_feeds_sources_alias()

        logger.debug("Все алиасы настроены")
    
    def _setup_news_alias(self):
        """
        Настройка алиаса config.news -> config.feeds

        Для обратной совместимости со старым кодом,
        который использует config.news
        """
        try:
            # Создаем ссылку news -> feeds
            self.config.news = self.config.feeds
            logger.debug("Алиас config.news -> config.feeds создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас news: {e}")

    def _setup_trading_alias(self):
        """
        Настройка алиаса config.trading -> config.features.trading

        Для обратной совместимости со старым кодом,
        который использует config.trading напрямую
        """
        try:
            # Создаем ссылку trading -> features.trading
            self.config.trading = self.config.features.trading
            logger.debug("Алиас config.trading -> config.features.trading создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас trading: {e}")
    
    def _setup_telegram_token_alias(self):
        """
        Настройка алиаса telegram.token -> telegram.bot_token
        
        Для обратной совместимости
        """
        try:
            if not hasattr(self.config.telegram, 'token'):
                self.config.telegram.token = self.config.telegram.bot_token
                logger.debug("Алиас telegram.token -> telegram.bot_token создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас telegram.token: {e}")
    
    def _setup_feeds_sources_alias(self):
        """
        Настройка алиаса feeds.sources для легкого доступа
        
        Позволяет использовать config.news.sources вместо
        config.news.get_enabled_feeds()
        """
        try:
            if not hasattr(self.config.feeds, 'sources'):
                # Создаем property-like доступ
                self.config.feeds.sources = list(self.config.feeds.get_enabled_feeds().values())
                logger.debug("Алиас feeds.sources создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас feeds.sources: {e}")