# app/config/feeds_config.py
"""
RSS Feeds Configuration Module
Конфигурация RSS источников новостей
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeedConfig:
    """
    Конфигурация одного RSS фида
    Содержит URL, приоритет и параметры обработки
    """
    
    url: str
    priority: int
    timeout: int = 30
    enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 5
    fallback_urls: List[str] = field(default_factory=list)
    category: str = 'general'
    language: str = 'ru'
    
    def __post_init__(self):
        """Валидация после инициализации"""
        if not 1 <= self.priority <= 10:
            raise ValueError(
                f"Priority must be between 1-10, got {self.priority}"
            )
        
        if self.timeout < 5:
            logger.warning(f"⚠️ Timeout {self.timeout}s слишком мал для {self.url}")


class FeedsConfig:
    """
    Конфигурация всех RSS источников
    Управление приоритетами и категориями фидов
    """
    
    def __init__(self):
        """Инициализация конфигурации фидов"""
        
        self.feeds: Dict[str, FeedConfig] = {
            'Крипто и Блокчейн РФ/СНГ 🇷🇺': FeedConfig(
                url='https://habr.com/ru/rss/hubs/cryptocurrency/',
                priority=8,
                timeout=25,
                max_retries=3,
                category='blockchain',
                language='ru',
                fallback_urls=[
                    'https://habr.com/ru/rss/hub/cryptocurrency/',
                    'https://habr.com/ru/rss/hubs/blockchain/'
                ]
            ),
            
            'Новости Майнинга (Мир) ⚙️': FeedConfig(
                url='https://cointelegraph.com/rss/tag/mining',
                priority=7,
                timeout=50,
                max_retries=5,
                retry_delay=10,
                category='mining',
                language='en',
                fallback_urls=[
                    'https://cointelegraph.com/rss',
                    'https://cryptopotato.com/feed/'
                ]
            ),
            
            'Крипто-новости СНГ 💡': FeedConfig(
                url='https://forklog.com/feed',
                priority=9,
                timeout=20,
                max_retries=3,
                category='news',
                language='ru',
                fallback_urls=[
                    'https://forklog.com/feed/',
                    'https://bits.media/feed/'
                ]
            ),
            
            'Мировые Крипто-новости 🌍': FeedConfig(
                url='https://www.coindesk.com/arc/outboundfeeds/rss/',
                priority=6,
                timeout=25,
                max_retries=3,
                category='news',
                language='en',
                fallback_urls=[
                    'https://coindesk.com/arc/outboundfeeds/rss',
                    'https://decrypt.co/feed'
                ]
            ),
            
            'Глубокая аналитика (Eng) 🧐': FeedConfig(
                url='https://www.theblock.co/rss.xml',
                priority=7,
                timeout=50,
                max_retries=5,
                retry_delay=10,
                category='analytics',
                language='en',
                fallback_urls=[
                    'https://theblock.co/rss',
                    'https://cryptobriefing.com/feed/',
                    'https://thedefiant.io/feed'
                ]
            ),
            
            'Bitcoin Magazine 📰': FeedConfig(
                url='https://bitcoinmagazine.com/.rss/full/',
                priority=6,
                timeout=25,
                max_retries=3,
                category='bitcoin',
                language='en'
            ),
            
            'CryptoPanic News 🚨': FeedConfig(
                url='https://cryptopanic.com/api/v1/posts/?auth_token=public&kind=news',
                priority=8,
                timeout=20,
                max_retries=3,
                category='news',
                language='en',
                enabled=True
            ),
            
            'Ethereum Foundation Blog 💎': FeedConfig(
                url='https://blog.ethereum.org/feed.xml',
                priority=7,
                timeout=30,
                max_retries=3,
                category='ethereum',
                language='en',
                enabled=True
            ),
            
            'Binance Academy 📚': FeedConfig(
                url='https://academy.binance.com/en/rss.xml',
                priority=6,
                timeout=25,
                max_retries=3,
                category='education',
                language='en',
                enabled=True
            ),
            
            'Cointelegraph Ru 🇷🇺': FeedConfig(
                url='https://ru.cointelegraph.com/rss',
                priority=8,
                timeout=30,
                max_retries=3,
                category='news',
                language='ru',
                fallback_urls=[
                    'https://ru.cointelegraph.com/rss/',
                ]
            ),
        }
        
        enabled_count = len([f for f in self.feeds.values() if f.enabled])
        logger.info(f"✅ [FEEDS] Загружено {len(self.feeds)} источников ({enabled_count} активных)")
    
    def get_enabled_feeds(self) -> Dict[str, FeedConfig]:
        """Получение только активных фидов"""
        return {
            name: feed for name, feed in self.feeds.items()
            if feed.enabled
        }
    
    def get_sorted_feeds(self) -> List[Tuple[str, FeedConfig]]:
        """
        Получение фидов отсортированных по приоритету
        
        Returns:
            Список (имя, конфиг) отсортированный по приоритету
        """
        return sorted(
            [
                (name, feed) for name, feed in self.feeds.items()
                if feed.enabled
            ],
            key=lambda x: x[1].priority,
            reverse=True
        )
    
    def get_feed_by_name(self, name: str) -> Optional[FeedConfig]:
        """
        Получение фида по имени
        
        Args:
            name: Имя фида
            
        Returns:
            Конфигурация фида или None
        """
        return self.feeds.get(name)
    
    def get_feeds_by_category(self, category: str) -> Dict[str, FeedConfig]:
        """Получение фидов по категории"""
        return {
            name: feed for name, feed in self.feeds.items()
            if feed.category == category and feed.enabled
        }
    
    def get_feeds_by_language(self, language: str) -> Dict[str, FeedConfig]:
        """Получение фидов по языку"""
        return {
            name: feed for name, feed in self.feeds.items()
            if feed.language == language and feed.enabled
        }
    
    def enable_feed(self, name: str) -> bool:
        """
        Включение фида
        
        Args:
            name: Имя фида
            
        Returns:
            True если успешно
        """
        if name in self.feeds:
            self.feeds[name].enabled = True
            return True
        return False
    
    def disable_feed(self, name: str) -> bool:
        """Отключение фида"""
        if name in self.feeds:
            self.feeds[name].enabled = False
            return True
        return False
    
    def get_categories(self) -> List[str]:
        """Получение списка всех категорий"""
        return list(set(feed.category for feed in self.feeds.values()))
    
    def get_languages(self) -> List[str]:
        """Получение списка всех языков"""
        return list(set(feed.language for feed in self.feeds.values()))
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'total': len(self.feeds),
            'enabled': len(self.get_enabled_feeds()),
            'categories': self.get_categories(),
            'languages': self.get_languages(),
            'sources': list(self.get_enabled_feeds().keys())
        }