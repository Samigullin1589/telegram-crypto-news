# bot/news/cycle.py
"""
News Processing Cycle
Логика цикла обработки новостей
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

from .state import ProcessorState, ProcessorLogger
from .components import ProcessorComponents

logger = logging.getLogger(__name__)


class NewsCycleProcessor:
    """Процессор цикла обработки новостей"""
    
    def __init__(
        self,
        state: ProcessorState,
        components: ProcessorComponents,
        fetcher,
        deduplicator
    ):
        """
        Инициализация
        
        Args:
            state: Состояние процессора
            components: Компоненты процессора
            fetcher: NewsFetcher для получения новостей
            deduplicator: ArticleDeduplicator для фильтрации дубликатов
        """
        self.state = state
        self.components = components
        self.fetcher = fetcher
        self.deduplicator = deduplicator
        self.logger = ProcessorLogger()
    
    async def run_cycle(self):
        """Выполнение одного цикла обработки новостей"""
        
        # Проверка готовности
        if not self.state.is_ready():
            self.logger.log_warning("Processor not ready for cycle")
            return
        
        # Проверка и сброс почасовых счетчиков
        if self.state.check_hour_reset():
            self.logger.log_info("Hourly stats reset")
        
        # Вывод информации о цикле
        cycle_time = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
        print(f"\n{'='*80}")
        print(f"📰 NEWS CYCLE #{self.state.total_cycles + 1} at {cycle_time}")
        print(f"{'='*80}")
        
        try:
            # Этап 1: Получение новостей
            articles = await self._fetch_articles()
            
            if not articles:
                self.logger.log_success("No new articles found")
                self.state.increment_cycle()
                return
            
            self.logger.log_info(f"Fetched {len(articles)} articles")
            self.state.total_articles_fetched += len(articles)
            
            # Этап 2: Фильтрация дубликатов
            new_articles = self._filter_duplicates(articles)
            
            if not new_articles:
                self.logger.log_success("All articles are duplicates")
                self.state.increment_cycle()
                return
            
            self.logger.log_info(f"Found {len(new_articles)} unique articles")
            
            # Этап 3: Обработка и публикация
            posted = await self._process_articles(new_articles)
            
            self.logger.log_success(f"Cycle completed: {posted} articles posted")
            self.state.increment_cycle()
            
        except Exception as e:
            self.logger.log_error(f"Cycle error: {e}")
            logger.error("Cycle processing error", exc_info=True)
            self.state.increment_error()
            raise
    
    async def _fetch_articles(self) -> List[Dict]:
        """
        Получение статей из всех источников
        
        Returns:
            Список статей
        """
        from app.config import config
        
        all_articles = []
        sources = config.news.sources[:5]  # Первые 5 источников
        
        # Параллельное получение из всех источников
        tasks = [self.fetcher.fetch_source(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = sources[i].get('name', 'Unknown')
                self.logger.log_warning(f"Source {source_name} failed: {result}")
            elif result:
                all_articles.extend(result)
        
        return all_articles
    
    def _filter_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """
        Фильтрация дубликатов
        
        Args:
            articles: Список статей
            
        Returns:
            Список уникальных статей
        """
        new_articles = [
            article for article in articles
            if not self.deduplicator.is_duplicate(article)
        ]
        
        # Отмечаем новые статьи как просмотренные
        for article in new_articles:
            self.deduplicator.mark_as_seen(article)
        
        return new_articles
    
    async def _process_articles(self, articles: List[Dict]) -> int:
        """
        Обработка и публикация статей
        
        Args:
            articles: Список статей для обработки
            
        Returns:
            Количество опубликованных статей
        """
        from app.config import config
        
        posted = 0
        max_posts = min(
            len(articles),
            config.news.posts_per_hour_cap - self.state.posts_this_hour,
            3  # Не более 3 за один цикл
        )
        
        for article in articles[:max_posts]:
            try:
                # Здесь может быть AI обработка, парсинг, публикация
                # Пока просто логируем
                title = article.get('title', 'No title')[:50]
                self.logger.log_info(f"Processing: {title}...")
                
                # Имитация обработки
                await asyncio.sleep(0.5)
                
                posted += 1
                self.state.posts_this_hour += 1
                self.state.total_articles_posted += 1
                
            except Exception as e:
                self.logger.log_warning(f"Article processing error: {e}")
                logger.debug("Article process error", exc_info=True)
                continue
        
        return posted
    
    def get_statistics(self) -> Dict:
        """
        Получение статистики обработки
        
        Returns:
            Словарь со статистикой
        """
        return {
            'total_cycles': self.state.total_cycles,
            'total_fetched': self.state.total_articles_fetched,
            'total_posted': self.state.total_articles_posted,
            'posts_this_hour': self.state.posts_this_hour,
            'deduplicator_stats': self.deduplicator.get_stats()
        }