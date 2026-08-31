# bot/news/cycle.py
"""
News Processing Cycle v2.0
Улучшенная логика цикла обработки новостей с правильным доступом к конфигурации
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from app.config import config
from .state import ProcessorState, ProcessorLogger
from .components import ProcessorComponents

logger = logging.getLogger(__name__)


class NewsCycleProcessor:
    """
    Процессор цикла обработки новостей
    
    Улучшения v2.0:
    - Использует config.feeds напрямую
    - Безопасный доступ к конфигурации
    - Лучшая обработка ошибок
    """
    
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
        all_articles = []
        
        # Безопасное получение источников из config.feeds
        try:
            enabled_feeds = config.feeds.get_enabled_feeds()
            sources = list(enabled_feeds.items())[:5]  # Первые 5 источников
            
            if not sources:
                self.logger.log_warning("No enabled feeds found")
                return []
            
        except Exception as e:
            self.logger.log_error(f"Cannot access feeds configuration: {e}")
            logger.debug("Feeds config access error", exc_info=True)
            return []
        
        # Параллельное получение из всех источников
        tasks = [
            self.fetcher.fetch_source(source, source_name)
            for source_name, source in sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = sources[i][0]
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
        
        return new_articles
    
    async def _process_articles(self, articles: List[Dict]) -> int:
        """
        Обработка и публикация статей
        
        Args:
            articles: Список статей для обработки
            
        Returns:
            Количество опубликованных статей
        """
        posted = 0
        
        # Безопасное получение лимитов
        try:
            posts_per_hour_cap = int(
                getattr(config.features, 'posts_per_hour_cap', 3)
            )
        except (AttributeError, TypeError, ValueError):
            posts_per_hour_cap = 3
        
        max_posts = max(0, min(
            len(articles),
            posts_per_hour_cap - self.state.posts_this_hour,
            3  # Не более 3 за один цикл
        ))
        
        for article in articles[:max_posts]:
            try:
                title = article.get('title', 'No title')[:50]
                self.logger.log_info(f"Processing: {title}...")

                if await self._process_article(article):
                    posted += 1
                    self.state.posts_this_hour += 1
                    self.state.total_articles_posted += 1
                
            except Exception as e:
                self.logger.log_warning(f"Article processing error: {e}")
                logger.debug("Article process error", exc_info=True)
                continue
        
        return posted

    async def _process_article(self, article: Dict) -> bool:
        """Обработать и опубликовать статью как одну логическую операцию."""
        link = article.get('url') or article.get('link')
        title = (article.get('title') or '').strip()

        if not link or not title:
            self.logger.log_warning("Article has no title or URL")
            return False

        prepared = article.copy()
        prepared['url'] = link
        prepared['link'] = link
        prepared['normalized_link'] = self._normalize_url(link)

        await self._enrich_content(prepared)
        message, ai_provider, ai_score = await self._build_message(prepared)
        if not message:
            self.logger.log_warning("Could not build publication message")
            return False

        telegram = self.components.telegram
        if telegram is None or not hasattr(telegram, 'post'):
            self.logger.log_warning("Telegram poster is not available")
            return False

        sent = await telegram.post(
            message=message,
            link=link,
            image_url=prepared.get('image_url')
        )
        if not sent:
            self.logger.log_warning("Telegram publication failed; article will be retried")
            return False

        # Только успешная Telegram-отправка делает статью обработанной.
        self.deduplicator.mark_as_seen(prepared)

        prepared['ai_provider'] = ai_provider
        prepared['ai_score'] = ai_score
        prepared['has_image'] = bool(prepared.get('image_url'))

        if self.components.has_database():
            saved = await self.components.database.save_article(
                article=prepared,
                status='success'
            )
            if not saved:
                self.logger.log_warning(
                    "Article was sent, but could not be recorded in the news database"
                )

        return True

    async def _enrich_content(self, article: Dict) -> None:
        """Дополнить RSS-данные полным текстом и изображением, если возможно."""
        parser = self.components.content_parser
        if parser is None:
            return

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                if hasattr(parser, 'get_article_content'):
                    parsed = await parser.get_article_content(
                        article['url'], article, session
                    )
                    if parsed:
                        if parsed.get('text'):
                            article['content'] = parsed['text']
                        if parsed.get('image_url'):
                            article['image_url'] = parsed['image_url']
                        if parsed.get('final_url'):
                            article['normalized_link'] = self._normalize_url(
                                parsed['final_url']
                            )
                elif hasattr(parser, 'parse_article'):
                    content = await parser.parse_article(article['url'], session)
                    if content:
                        article['content'] = content

            if not article.get('image_url') and hasattr(parser, 'find_best_image'):
                article['image_url'] = parser.find_best_image(article)
        except Exception as e:
            # RSS description остается безопасным fallback.
            logger.debug("Article enrichment failed: %s", e, exc_info=True)

    async def _build_message(
        self,
        article: Dict
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """Построить AI-summary либо локальный fallback-текст."""
        title = article['title'].strip()
        text = (
            article.get('content')
            or article.get('summary')
            or article.get('description')
            or ''
        ).strip()
        category = article.get('category') or 'news 📰'
        ai_handler = self.components.ai_handler
        ai_provider = None
        ai_score = None

        if ai_handler is not None:
            try:
                if hasattr(ai_handler, 'analyze_article'):
                    analysis = await ai_handler.analyze_article(article)
                    if analysis:
                        ai_score = analysis.get('score')

                if hasattr(ai_handler, 'get_summary'):
                    summary = await ai_handler.get_summary(title, text, category)
                    if summary:
                        message, ai_provider = summary
                        return message, ai_provider, ai_score
            except Exception as e:
                logger.warning("AI processing failed, using fallback: %s", e)

        fallback_text = text or "Подробности доступны в первоисточнике."
        fallback_text = fallback_text[:900].strip()
        message = f"📰 **{title}**\n\n{fallback_text}\n\n#crypto #news"
        return message, ai_provider, ai_score

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Удалить query/fragment, обычно содержащие tracking-параметры."""
        try:
            parsed = urlsplit(url)
            path = parsed.path.rstrip('/') or '/'
            return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, '', ''))
        except Exception:
            return url
    
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