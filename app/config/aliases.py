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
        self._setup_whale_alias()
        self._setup_chains_alias()
        self._setup_telegram_token_alias()
        self._setup_feeds_sources_alias()
        self._setup_production_alias()
        self._setup_rate_limit_alias()

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

    def _setup_whale_alias(self):
        """
        Настройка алиаса config.whale -> config.features.whale

        Для обратной совместимости со старым кодом,
        который использует config.whale напрямую
        """
        try:
            # Создаем ссылку whale -> features.whale
            self.config.whale = self.config.features.whale
            logger.debug("Алиас config.whale -> config.features.whale создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас whale: {e}")

    def _setup_chains_alias(self):
        """
        Настройка алиаса config.chains -> config.blockchain

        Для обратной совместимости со старым кодом,
        который использует config.chains
        """
        try:
            # Создаем ссылку chains -> blockchain
            self.config.chains = self.config.blockchain
            logger.debug("Алиас config.chains -> config.blockchain создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас chains: {e}")
    
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
                if hasattr(self.config.feeds, 'get_enabled_feeds'):
                    self.config.feeds.sources = list(self.config.feeds.get_enabled_feeds().values())
                    logger.debug("Алиас feeds.sources создан")
                else:
                    logger.debug("FeedsConfig не имеет метода get_enabled_feeds(), пропускаем")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас feeds.sources: {e}")

    def _setup_production_alias(self):
        """
        Настройка алиаса config.production -> config.base

        Для обратной совместимости с кодом, который использует config.production
        для доступа к настройкам (port, http_timeout, max_memory_mb, etc.)
        """
        try:
            # Создаем алиас production -> base (содержит все production настройки)
            self.config.production = self.config.base
            logger.debug(f"Алиас config.production -> config.base создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас production: {e}")

    def _setup_rate_limit_alias(self):
        """
        Настройка алиаса config.rate_limit -> config.rate_limiting

        Для обратной совместимости с кодом, который использует config.rate_limit
        для доступа к настройкам лимитирования (enabled, calls_per_minute, etc.)
        """
        try:
            # Создаем алиас rate_limit -> rate_limiting
            self.config.rate_limit = self.config.rate_limiting
            logger.debug(f"Алиас config.rate_limit -> config.rate_limiting создан")
        except Exception as e:
            logger.warning(f"Не удалось создать алиас rate_limit: {e}")