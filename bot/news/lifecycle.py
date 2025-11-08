# bot/news/lifecycle.py
"""
News Processor Lifecycle Management
Управление жизненным циклом процессора
"""

import asyncio
import logging
from typing import Optional

from .state import ProcessorState, ProcessorLogger
from .components import ProcessorComponents

logger = logging.getLogger(__name__)


class ProcessorLifecycle:
    """Управление жизненным циклом процессора"""
    
    def __init__(
        self,
        state: ProcessorState,
        components: ProcessorComponents
    ):
        """
        Инициализация
        
        Args:
            state: Состояние процессора
            components: Компоненты процессора
        """
        self.state = state
        self.components = components
        self.logger = ProcessorLogger()
    
    async def initialize_database(self) -> bool:
        """
        Инициализация базы данных
        
        Returns:
            True если инициализация успешна или БД отсутствует
        """
        if self.state.database_initialized:
            return True
        
        if not self.components.has_database():
            self.logger.log_info("Database not available, skipping initialization")
            self.state.database_initialized = True
            return True
        
        try:
            await self.components.database.initialize()
            self.logger.log_success("Database initialized")
            self.state.database_initialized = True
            return True
            
        except Exception as e:
            self.logger.log_warning(f"Database initialization failed: {e}")
            logger.debug("Database init error", exc_info=True)
            # Не критичная ошибка, продолжаем работу
            self.state.database_initialized = True
            return True
    
    async def load_baseline(self, fetcher, deduplicator) -> bool:
        """
        Загрузка базового состояния
        
        Args:
            fetcher: Fetcher для получения статей
            deduplicator: Deduplicator для отслеживания дубликатов
            
        Returns:
            True если загрузка успешна
        """
        if self.state.baseline_loaded:
            return True
        
        self.logger.log_header("LOADING INITIAL BASELINE")
        
        try:
            from app.config import config
            
            # Получаем статьи из всех источников
            all_articles = []
            sources = config.news.sources[:5]  # Первые 5 источников
            
            tasks = [fetcher.fetch_source(source) for source in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    source_name = sources[i].get('name', 'Unknown')
                    self.logger.log_warning(f"Source {source_name}: {result}")
                elif result:
                    all_articles.extend(result)
            
            # Отмечаем все как просмотренные
            for article in all_articles:
                deduplicator.mark_as_seen(article)
            
            stats = deduplicator.get_stats()
            self.logger.log_success(
                f"Baseline created: {stats['seen_urls']} URLs, "
                f"{stats['seen_hashes']} hashes"
            )
            
            self.state.baseline_loaded = True
            return True
            
        except Exception as e:
            self.logger.log_error(f"Baseline loading failed: {e}")
            logger.error("Baseline error", exc_info=True)
            # Критичная ошибка
            return False
    
    async def cleanup(self):
        """Очистка ресурсов"""
        self.logger.log_header("CLEANUP PROCESSOR")
        
        self.state.shutdown_requested = True
        
        # Закрытие БД
        if self.components.has_database():
            try:
                if hasattr(self.components.database, 'close'):
                    await self.components.database.close()
                    self.logger.log_success("Database closed")
            except Exception as e:
                self.logger.log_warning(f"Database close error: {e}")
        
        # Закрытие других компонентов
        for component_name in ['ai_handler', 'content_parser', 'telegram']:
            component = getattr(self.components, component_name, None)
            if component and hasattr(component, 'cleanup'):
                try:
                    if asyncio.iscoroutinefunction(component.cleanup):
                        await component.cleanup()
                    else:
                        component.cleanup()
                    self.logger.log_success(f"{component_name} cleaned up")
                except Exception as e:
                    self.logger.log_warning(f"{component_name} cleanup error: {e}")
        
        self.logger.log_success("Cleanup completed")