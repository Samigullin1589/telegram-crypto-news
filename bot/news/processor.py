# bot/news/processor.py
"""
News Processor v6.1 - Fixed Configuration Access
Исправленный процессор с правильным доступом к конфигурации
"""

import logging
from typing import Dict, Any

from app.config import config
from bot.news.fetcher import NewsFetcher
from bot.news.deduplicator import ArticleDeduplicator
from bot.news.state import ProcessorState, ProcessorLogger
from bot.news.components import ComponentsLoader, ProcessorComponents
from bot.news.lifecycle import ProcessorLifecycle
from bot.news.cycle import NewsCycleProcessor

logger = logging.getLogger(__name__)


class NewsProcessor:
    """
    Главный процессор новостей
    
    Исправления v6.1:
    - Использует config.feeds напрямую (не зависит от алиаса config.news)
    - Безопасная проверка наличия модулей конфигурации
    - Улучшенная обработка ошибок инициализации
    """
    
    def __init__(self):
        """Инициализация процессора"""
        
        self.logger = ProcessorLogger()
        self.logger.log_header("NEWS PROCESSOR v6.1 - INITIALIZATION")
        
        # Проверка предварительных условий
        if not self._check_prerequisites():
            self.state = ProcessorState(core_initialized=False)
            return
        
        try:
            # Инициализация состояния
            self.state = ProcessorState()
            
            # Загрузка основных компонентов
            self.fetcher = NewsFetcher()
            self.deduplicator = ArticleDeduplicator()
            
            self.logger.log_success("Core components loaded")
            self._log_configuration()
            
            # Загрузка опциональных компонентов
            self.components = ComponentsLoader.load_all()
            
            # Инициализация менеджеров
            self.lifecycle = ProcessorLifecycle(self.state, self.components)
            self.cycle_processor = NewsCycleProcessor(
                self.state,
                self.components,
                self.fetcher,
                self.deduplicator
            )
            
            # Установка флага инициализации
            self.state.core_initialized = True
            
            self.logger.log_success("Processor initialized successfully")
            self.logger.log_section_end()
            
        except Exception as e:
            self.logger.log_error(f"Initialization failed: {e}")
            logger.error("Processor init error", exc_info=True)
            self.state = ProcessorState(core_initialized=False)
    
    def _check_prerequisites(self) -> bool:
        """
        Проверка предварительных условий
        
        Проверяет:
        1. Включен ли модуль news в features
        2. Существует ли config.feeds (основной модуль)
        3. Есть ли настроенные источники новостей
        
        Returns:
            True если все условия выполнены
        """
        # Проверка 1: Включен ли модуль news
        try:
            if not config.is_feature_enabled('news'):
                self.logger.log_warning("News processing disabled in config.features")
                return False
        except Exception as e:
            self.logger.log_error(f"Cannot check feature status: {e}")
            return False
        
        # Проверка 2: Существует ли config.feeds
        if not hasattr(config, 'feeds'):
            self.logger.log_error("config.feeds not found")
            self.logger.log_info("Configuration module is not properly initialized")
            return False
        
        # Проверка 3: Есть ли настроенные источники
        try:
            # Проверяем через feeds модуль
            enabled_feeds = config.feeds.get_enabled_feeds()
            
            if not enabled_feeds:
                self.logger.log_error("No news sources configured")
                self.logger.log_info("Check config.feeds or ENABLED_FEEDS environment variable")
                return False
            
            self.logger.log_info(f"Found {len(enabled_feeds)} enabled news sources")
            return True
            
        except Exception as e:
            self.logger.log_error(f"Cannot access news sources: {e}")
            logger.debug("Feeds access error", exc_info=True)
            return False
    
    def _log_configuration(self):
        """Вывод информации о конфигурации"""
        try:
            # Получаем конфигурацию из feeds
            enabled_feeds = config.feeds.get_enabled_feeds()
            
            self.logger.log_info(f"Sources: {len(enabled_feeds)}")
            
            # Пытаемся получить дополнительные параметры
            if hasattr(config.feeds, 'fetch_interval'):
                self.logger.log_info(f"Fetch interval: {config.feeds.fetch_interval}s")
            
            if hasattr(config.feeds, 'posts_per_hour_cap'):
                self.logger.log_info(f"Posts per hour cap: {config.feeds.posts_per_hour_cap}")
            
        except Exception as e:
            self.logger.log_warning(f"Cannot log full configuration: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """
        Проверка инициализации процессора
        
        Returns:
            True если процессор инициализирован
        """
        return self.state.core_initialized if hasattr(self, 'state') else False
    
    async def initialize_database(self):
        """Инициализация базы данных (если есть)"""
        if not self.is_initialized:
            return
        
        await self.lifecycle.initialize_database()
    
    async def load_baseline(self):
        """Загрузка базового состояния"""
        if not self.is_initialized:
            return
        
        await self.lifecycle.load_baseline(self.fetcher, self.deduplicator)
    
    async def run_cycle(self):
        """
        Выполнение одного цикла обработки новостей

        Этапы:
        1. Инициализация БД (если не инициализирована)
        2. Загрузка baseline (если не загружен)
        3. Выполнение цикла обработки
        """

        if not self.is_initialized:
            self.logger.log_warning("Processor not initialized, skipping cycle")
            return

        # Инициализация БД при первом запуске
        if not self.state.database_initialized:
            await self.initialize_database()

        # Загрузка baseline при первом запуске
        if not self.state.baseline_loaded:
            await self.load_baseline()
            return  # Первый запуск только для baseline

        # Выполнение цикла
        await self.cycle_processor.run_cycle()

    async def process(self):
        """
        Алиас для run_cycle() для обратной совместимости

        Этот метод требуется для валидации в NewsLoader
        """
        await self.run_cycle()

    async def run(self):
        """
        Алиас для run_cycle() для обратной совместимости

        Этот метод требуется для валидации в NewsLoader
        """
        await self.run_cycle()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса процессора
        
        Returns:
            Словарь со статусом и статистикой
        """
        status = {
            'initialized': self.is_initialized,
            'state': self.state.to_dict() if self.is_initialized else {},
        }
        
        if self.is_initialized:
            status['statistics'] = self.cycle_processor.get_statistics()
        
        return status
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if not self.is_initialized:
            return
        
        await self.lifecycle.cleanup()


__all__ = ['NewsProcessor']