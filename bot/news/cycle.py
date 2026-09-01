# bot/news/cycle.py
"""
News Processing Cycle v2.0
Улучшенная логика цикла обработки новостей с правильным доступом к конфигурации
"""

import asyncio
import html
import logging
import re
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

    _EXTERNAL_REDIRECT_PATTERNS = (
        r'(?:https?://|www\.)\S+',
        r'\b(?:подробност|детал)\w*.{0,60}\b(?:ссылк|первоисточник|сайт)\w*',
        r'\b(?:перейд|переход|читай|прочитай|узнай|смотр)\w*'
        r'.{0,60}\b(?:ссылк|первоисточник|сайт)\w*',
        r'\b(?:ссылк|первоисточник|сайт)\w*'
        r'.{0,60}\b(?:подробност|детал)\w*',
    )
    _GENERIC_PLACEHOLDER_PATTERNS = (
        r'\bпоявил\w*\s+(?:нов\w+\s+)?сообщени\w*\s+о\s+событи\w*',
        r'\bважн\w+\s+новост\w+\s+крипторынк\w*',
    )
    
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
            sources = config.feeds.get_sorted_feeds()[:5]
            
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
        articles = sorted(
            articles,
            key=self._article_sort_key,
            reverse=True,
        )

        cooldown_remaining = self._cooldown_remaining_seconds()
        if cooldown_remaining > 0:
            self._mark_articles_seen(articles)
            self.state.total_filtered_cooldown += len(articles)
            self.logger.log_info(
                "News publication cooldown active: "
                f"{cooldown_remaining // 60 + 1} minutes remaining; "
                f"discarded {len(articles)} queued articles"
            )
            return 0
        
        # Безопасное получение лимитов
        try:
            posts_per_hour_cap = int(
                getattr(config.features, 'posts_per_hour_cap', 1)
            )
        except (AttributeError, TypeError, ValueError):
            posts_per_hour_cap = 1
        
        max_posts = max(0, min(
            len(articles),
            posts_per_hour_cap - self.state.posts_this_hour,
            1  # Только одна лучшая подходящая новость за цикл
        ))

        if max_posts == 0:
            self._mark_articles_seen(articles)
            self.state.total_filtered_batch_limit += len(articles)
            return 0
        
        for index, article in enumerate(articles):
            if posted >= max_posts:
                self._mark_articles_seen(articles[index:])
                self.state.total_filtered_batch_limit += len(articles[index:])
                break
            try:
                title = article.get('title', 'No title')[:50]
                self.logger.log_info(f"Processing: {title}...")

                if await self._process_article(article):
                    posted += 1
                    self.state.posts_this_hour += 1
                    self.state.total_articles_posted += 1
                    self.state.last_post_time = datetime.now(timezone.utc)
                
            except Exception as e:
                self.logger.log_warning(f"Article processing error: {e}")
                logger.debug("Article process error", exc_info=True)
                continue
        
        return posted

    def _cooldown_remaining_seconds(self) -> int:
        """Вернуть остаток строгого интервала между успешными news-постами."""
        if self.state.last_post_time is None:
            return 0
        try:
            cooldown = int(getattr(
                config.features,
                'news_publish_cooldown_seconds',
                14400
            ))
        except (AttributeError, TypeError, ValueError):
            cooldown = 14400
        elapsed = (
            datetime.now(timezone.utc) - self.state.last_post_time
        ).total_seconds()
        return max(0, int(cooldown - elapsed))

    def _mark_articles_seen(self, articles: List[Dict]) -> None:
        """Не переносить непубликуемый хвост RSS-пачки в будущие циклы."""
        for article in articles:
            self.deduplicator.mark_as_seen(article)

    @staticmethod
    def _article_sort_key(article: Dict) -> Tuple[int, float]:
        """Сначала надёжность источника, затем свежесть внутри приоритета."""
        metadata = article.get('source_metadata') or {}
        try:
            priority = int(metadata.get('priority', 0))
        except (TypeError, ValueError):
            priority = 0

        published = article.get('published')
        if isinstance(published, str):
            try:
                published = datetime.fromisoformat(
                    published.replace('Z', '+00:00')
                )
            except ValueError:
                published = None
        if isinstance(published, datetime):
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published_timestamp = published.timestamp()
        else:
            published_timestamp = 0.0
        return priority, published_timestamp

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
        if not prepared.get('image_url'):
            self.logger.log_warning(
                "Article has no validated image; publication will be retried"
            )
            return False

        message, ai_provider, ai_score = await self._build_message(prepared)
        if not self._meets_quality_threshold(ai_score):
            self.state.total_filtered_quality += 1
            self.logger.log_info(
                "Article skipped by strict quality gate: "
                f"score={ai_score!r}, required={self._news_confidence_threshold()}"
            )
            self.deduplicator.mark_as_seen(prepared)
            return False

        if not message:
            self.state.total_filtered_quality += 1
            self.logger.log_warning(
                "Article has no self-contained publication message; skipping"
            )
            self.deduplicator.mark_as_seen(prepared)
            return False

        telegram = self.components.telegram
        if telegram is None or not hasattr(telegram, 'post'):
            self.logger.log_warning("Telegram poster is not available")
            return False

        sent = await telegram.post(
            message=message,
            link=link,
            image_url=prepared.get('image_url'),
            require_image=True,
            show_source_button=False,
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

    @staticmethod
    def _news_confidence_threshold() -> int:
        try:
            return int(getattr(config.features, 'min_news_confidence', 85))
        except (AttributeError, TypeError, ValueError):
            return 85

    @classmethod
    def _meets_quality_threshold(cls, score) -> bool:
        """Fail closed: без корректной AI-оценки новость не публикуется."""
        if isinstance(score, bool):
            return False
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            return False
        return numeric_score >= cls._news_confidence_threshold()

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
        """Построить проверенный русский AI-summary либо русский source fallback."""
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

                if not self._meets_quality_threshold(ai_score):
                    return None, ai_provider, ai_score

                if hasattr(ai_handler, 'get_summary'):
                    summary = await ai_handler.get_summary(title, text, category)
                    if summary and self._is_publishable_russian_message(summary[0]):
                        message, ai_provider = summary
                        return message, ai_provider, ai_score
                    if summary:
                        logger.warning(
                            "AI returned a non-Russian or error-page response"
                        )
            except Exception as e:
                logger.warning("AI processing failed: %s", e)

        if not self._has_cyrillic(title) or not self._has_cyrillic(text):
            logger.warning(
                "Foreign-language article has no valid Russian AI summary; skipping publication"
            )
            return None, ai_provider, ai_score

        russian_title = title
        fallback_text = self._build_russian_fallback(text)
        if not fallback_text:
            logger.warning(
                "Russian source has no publishable article text; skipping publication"
            )
            return None, ai_provider, ai_score
        message = f"📰 **{russian_title}**\n\n{fallback_text}\n\n#крипто #новости"
        if not self._is_publishable_russian_message(message):
            logger.warning(
                "Russian source fallback is not self-contained; skipping publication"
            )
            return None, ai_provider, ai_score
        return message, ai_provider, ai_score

    @classmethod
    def _build_russian_fallback(cls, text: str) -> str:
        """Построить самодостаточный русский fallback без внешних CTA."""
        cleaned = html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cls._is_error_page(cleaned):
            cleaned = ''

        russian_sentences = [
            sentence.strip()
            for sentence in re.split(r'(?<=[.!?])\s+', cleaned)
            if cls._has_cyrillic(sentence)
            and not cls._contains_external_redirect(sentence)
            and not cls._is_generic_placeholder(sentence)
        ]
        fallback = ' '.join(russian_sentences[:3])[:900].strip()
        if fallback:
            return fallback
        return ''

    @classmethod
    def _is_publishable_russian_message(cls, message: str) -> bool:
        if not message or cls._is_error_page(message):
            return False
        if (
            cls._contains_external_redirect(message)
            or cls._is_generic_placeholder(message)
        ):
            return False
        first_line = next(
            (line.strip() for line in message.splitlines() if line.strip()),
            '',
        )
        if not cls._has_cyrillic(first_line):
            return False
        cyrillic_count = len(re.findall(r'[А-Яа-яЁё]', message))
        latin_count = len(re.findall(r'[A-Za-z]', message))
        body = cls._publication_body(message)
        body_words = re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', body)
        body_cyrillic_count = len(re.findall(r'[А-Яа-яЁё]', body))
        return (
            cyrillic_count >= latin_count
            and body_cyrillic_count >= 60
            and len(body_words) >= 20
        )

    @classmethod
    def _contains_external_redirect(cls, text: str) -> bool:
        normalized = cls._normalize_message_text(text)
        return any(
            re.search(pattern, normalized, flags=re.IGNORECASE)
            for pattern in cls._EXTERNAL_REDIRECT_PATTERNS
        )

    @classmethod
    def _is_generic_placeholder(cls, text: str) -> bool:
        normalized = cls._normalize_message_text(text)
        return any(
            re.search(pattern, normalized, flags=re.IGNORECASE)
            for pattern in cls._GENERIC_PLACEHOLDER_PATTERNS
        )

    @classmethod
    def _publication_body(cls, message: str) -> str:
        lines = [line.strip() for line in message.splitlines() if line.strip()]
        if lines:
            lines = lines[1:]

        body_lines = []
        for line in lines:
            plain_line = cls._normalize_message_text(line)
            words = plain_line.split()
            if words and all(word.startswith('#') for word in words):
                continue
            if plain_line.rstrip(':').lower() == 'детали':
                continue
            body_lines.append(plain_line)
        return ' '.join(body_lines).strip()

    @staticmethod
    def _normalize_message_text(text: str) -> str:
        normalized = html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))
        normalized = re.sub(r'[*_`~]+', '', normalized)
        return re.sub(r'\s+', ' ', normalized).strip()

    @staticmethod
    def _has_cyrillic(text: str) -> bool:
        return bool(re.search(r'[А-Яа-яЁё]', text or ''))

    @staticmethod
    def _is_error_page(text: str) -> bool:
        lowered = (text or '').lower()
        markers = (
            '<!doctype html', '<html', 'cloudflare ray id',
            'web server is returning an unknown error', 'error code 520',
            'bad gateway', 'service unavailable',
        )
        return any(marker in lowered for marker in markers)

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
            'filtered_quality': self.state.total_filtered_quality,
            'filtered_cooldown': self.state.total_filtered_cooldown,
            'filtered_batch_limit': self.state.total_filtered_batch_limit,
            'posts_this_hour': self.state.posts_this_hour,
            'deduplicator_stats': self.deduplicator.get_stats()
        }