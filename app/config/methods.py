# app/config/methods.py
"""
Config Methods
API методы класса Config
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Config, FeedConfig

logger = logging.getLogger(__name__)


class ConfigMethods:
    """
    API методы конфигурации
    
    Содержит все публичные методы Config для удобного доступа
    к функционалу различных модулей
    """
    
    def __init__(self, config_instance: 'Config'):
        """
        Инициализация
        
        Args:
            config_instance: Экземпляр Config
        """
        self.config = config_instance
    
    # ========================================================================
    # API МЕТОДЫ
    # ========================================================================
    
    def has_scanner_api_key(self, chain: str) -> bool:
        """Проверка наличия API ключа для blockchain scanner"""
        return self.config.api.has_scanner_key(chain)
    
    def get_scanner_api_key(self, chain: str) -> str:
        """Получение API ключа для blockchain scanner"""
        return self.config.api.get_scanner_key(chain)
    
    def get_missing_scanner_keys(self) -> List[str]:
        """Получение списка блокчейнов без API ключей"""
        return self.config.api.get_missing_scanner_keys(
            self.config.blockchain.enabled_chains
        )
    
    def has_coingecko(self) -> bool:
        """Проверка наличия CoinGecko API ключа"""
        return bool(self.config.api.coingecko_api_key)
    
    def has_alchemy(self) -> bool:
        """Проверка наличия Alchemy API ключа"""
        return bool(self.config.api.alchemy_api_key)
    
    def has_coinmarketcap(self) -> bool:
        """Проверка наличия CoinMarketCap API ключа"""
        return bool(self.config.api.coinmarketcap_api_key)
    
    def has_ai_provider(self) -> bool:
        """Проверка наличия AI провайдера"""
        return self.config.api.has_ai_provider()
    
    def get_ai_provider(self) -> str:
        """Получение названия активного AI провайдера"""
        return self.config.api.get_ai_provider()
    
    # ========================================================================
    # BLOCKCHAIN МЕТОДЫ
    # ========================================================================
    
    def get_chain_explorer_url(
        self,
        chain: str,
        address: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> str:
        """Получение URL blockchain explorer"""
        return self.config.blockchain.get_explorer_url(chain, address, tx_hash)
    
    def get_chain_symbol(self, chain: str) -> str:
        """Получение символа нативной валюты"""
        return self.config.blockchain.get_chain_symbol(chain)
    
    def get_chain_name(self, chain: str) -> str:
        """Получение полного имени блокчейна"""
        return self.config.blockchain.get_chain_name(chain)
    
    def get_chain_emoji(self, chain: str) -> str:
        """Получение emoji для блокчейна"""
        return self.config.blockchain.get_chain_emoji(chain)
    
    def get_chain_color(self, chain: str) -> str:
        """Получение цвета блокчейна"""
        return self.config.blockchain.get_chain_color(chain)
    
    def is_chain_enabled(self, chain: str) -> bool:
        """Проверка включен ли блокчейн"""
        return self.config.blockchain.is_chain_enabled(chain)
    
    def get_whale_threshold(self, chain: str) -> Dict[str, float]:
        """Получение порогов для whale транзакций"""
        return self.config.blockchain.get_whale_threshold(chain)
    
    def is_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция whale"""
        return self.config.blockchain.is_whale_transaction(chain, usd_value)
    
    def is_mega_whale_transaction(self, chain: str, usd_value: float) -> bool:
        """Проверка является ли транзакция mega whale"""
        return self.config.blockchain.is_mega_whale_transaction(chain, usd_value)
    
    # ========================================================================
    # RSS FEEDS МЕТОДЫ
    # ========================================================================
    
    def get_sorted_feeds(self) -> List[tuple]:
        """Получение отсортированных по приоритету фидов"""
        return self.config.feeds.get_sorted_feeds()
    
    def get_feed_by_name(self, name: str) -> Optional['FeedConfig']:
        """Получение конфигурации фида по имени"""
        return self.config.feeds.get_feed_by_name(name)
    
    def get_feed_config(self, name: str) -> Optional['FeedConfig']:
        """Алиас для get_feed_by_name"""
        return self.config.feeds.get_feed_by_name(name)
    
    def get_all_feeds(self) -> Dict[str, 'FeedConfig']:
        """Получение всех фидов"""
        return self.config.feeds.feeds
    
    def get_enabled_feeds(self) -> Dict[str, 'FeedConfig']:
        """Получение только активных фидов"""
        return self.config.feeds.get_enabled_feeds()
    
    def enable_feed(self, name: str) -> None:
        """Включение фида"""
        self.config.feeds.enable_feed(name)
    
    def disable_feed(self, name: str) -> None:
        """Отключение фида"""
        self.config.feeds.disable_feed(name)
    
    # ========================================================================
    # FEATURES МЕТОДЫ
    # ========================================================================
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Проверка включен ли функциональный модуль
        
        Args:
            feature_name: Название модуля
            
        Returns:
            True если модуль включен
        """
        feature_map = {
            'whale': self.config.features.whale_enabled,
            'news': self.config.features.news_enabled,
            'analytics': self.config.features.analytics_enabled,
            'trading': self.config.features.trading_enabled,
            'hyperliquid': self.config.features.hyperliquid_enabled,
        }
        return feature_map.get(feature_name.lower(), False)
    
    # ========================================================================
    # AI TEMPLATE
    # ========================================================================
    
    @property
    def ai_prompt_template(self) -> str:
        """Шаблон промпта для AI обработки новостей"""
        return """
Ты — ведущий аналитик издания 'Bloomberg Crypto'. Твоя задача — проанализировать текст новости и подготовить профессиональный, структурированный пост для Telegram-канала 'Crypto Compass'.

Твой ответ должен быть исключительно на русском языке и строго следовать формату Markdown ниже.

{emoji} **{title}**

*Главная суть новости в 2-3 предложениях.*

**Детали:**
- Ключевой факт или цифра.
- Контекст или причина.
- Возможные последствия.

*(3 релевантных хэштега на русском)*
"""
    
    # ========================================================================
    # СЕРИАЛИЗАЦИЯ
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация конфигурации в словарь"""
        try:
            return {
                'base': self.config.base.to_dict(),
                'paths': self.config.paths.to_dict(),
                'api': self.config.api.to_dict(),
                'telegram': self.config.telegram.to_dict(),
                'feeds': self.config.feeds.to_dict(),
                'blockchain': self.config.blockchain.to_dict(),
                'features': self.config.features.to_dict(),
                'database': self.config.database.to_dict(),
                'rate_limiting': self.config.rate_limiting.to_dict()
            }
        except Exception as e:
            logger.error(f"Ошибка сериализации: {e}")
            return {}
    
    def __repr__(self) -> str:
        """Строковое представление"""
        try:
            return (
                f"Config("
                f"env={self.config.base.ENVIRONMENT}, "
                f"chains={len(self.config.blockchain.enabled_chains)}, "
                f"feeds={len(self.config.feeds.get_enabled_feeds())}, "
                f"features={sum(1 for v in self.config.features_enabled.values() if v)}"
                f")"
            )
        except:
            return "Config()"