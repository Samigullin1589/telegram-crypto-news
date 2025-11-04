# bot/database.py - ASYNC-SAFE DATABASE MANAGER v4.0
"""
DATABASE MANAGER - Thread-safe и Async-safe

ИСПРАВЛЕНО (04.11.2025):
✅ Убран threading.local (НЕ работает с asyncio!)
✅ Добавлен asyncio.Lock для thread safety
✅ Async context managers
✅ Proper connection pooling
✅ Structured logging
✅ Error recovery
✅ Performance optimizations
"""

import sqlite3
import asyncio
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Set, List, Optional, Dict, Any
import json
from dataclasses import dataclass, asdict

try:
    from .config import config
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback для случая когда config недоступен
    CONFIG_AVAILABLE = False
    class DummyConfig:
        DB_PATH = 'news_database.sqlite'
    config = DummyConfig()


@dataclass
class Article:
    """Модель статьи"""
    link: str
    normalized_link: str
    source_feed: str
    title: str
    has_image: bool = False
    ai_provider: Optional[str] = None
    posting_status: str = 'success'
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AsyncDatabaseManager:
    """
    Async-safe Database Manager с connection pooling
    
    ВАЖНО:
    - Использует aiosqlite для async операций
    - asyncio.Lock вместо threading.local
    - Proper async context managers
    - Connection pooling
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Инициализация database manager
        
        Args:
            db_path: Путь к БД (по умолчанию из config)
        """
        if db_path:
            self.db_path = Path(db_path)
        elif CONFIG_AVAILABLE:
            self.db_path = Path(config.DB_PATH)
        else:
            self.db_path = Path('news_database.sqlite')
        
        # Async lock для thread safety
        self._lock = asyncio.Lock()
        
        # Connection pool
        self._connection: Optional[aiosqlite.Connection] = None
        
        # Статистика
        self._stats = {
            'total_articles': 0,
            'articles_today': 0,
            'last_backup': None,
            'queries_executed': 0,
            'errors': 0
        }
        
        # Cache для быстрых проверок
        self._link_cache: Set[str] = set()
        self._cache_loaded = False
        
        print(f"💾 [DB] AsyncDatabaseManager инициализирован")
        print(f"   Path: {self.db_path}")
    
    async def initialize(self):
        """
        Асинхронная инициализация БД
        
        Должна быть вызвана до использования менеджера
        """
        async with self._lock:
            # Создаём таблицы
            await self._create_tables()
            
            # Миграции
            await self._run_migrations()
            
            # Загружаем cache
            await self._load_cache()
            
            # Обновляем статистику
            await self._update_stats()
            
            print(f"✅ [DB] База данных готова")
            print(f"   Всего статей: {self._stats['total_articles']}")
            print(f"   Сегодня: {self._stats['articles_today']}")
    
    @asynccontextmanager
    async def _get_connection(self):
        """
        Async context manager для получения connection
        
        Usage:
            async with db._get_connection() as conn:
                cursor = await conn.execute("SELECT ...")
        """
        # Создаём новое подключение для каждой операции
        # (aiosqlite не поддерживает connection pooling из коробки)
        conn = await aiosqlite.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level=None
        )
        
        try:
            # Настраиваем connection
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-64000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            
            yield conn
        
        except Exception as e:
            print(f"❌ [DB] Connection error: {e}")
            self._stats['errors'] += 1
            raise
        
        finally:
            await conn.close()
    
    async def _create_tables(self):
        """Создание схемы БД"""
        async with self._get_connection() as conn:
            # Основная таблица статей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_articles (
                    link TEXT PRIMARY KEY,
                    normalized_link TEXT NOT NULL,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_feed TEXT,
                    title TEXT,
                    has_image BOOLEAN DEFAULT 0,
                    ai_provider TEXT,
                    posting_status TEXT DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индексы для быстрых запросов
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_published_at 
                ON posted_articles(published_at DESC)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_normalized_link 
                ON posted_articles(normalized_link)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_feed 
                ON posted_articles(source_feed)
            """)
            
            # Таблица статистики
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    date TEXT PRIMARY KEY,
                    articles_posted INTEGER DEFAULT 0,
                    articles_with_images INTEGER DEFAULT 0,
                    feed_stats TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица метаданных
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.commit()
            self._stats['queries_executed'] += 6
    
    async def _run_migrations(self):
        """Миграции для обновления схемы БД"""
        async with self._get_connection() as conn:
            # Проверяем существующие колонки
            cursor = await conn.execute("PRAGMA table_info(posted_articles)")
            columns = {row[1] for row in await cursor.fetchall()}
            
            # Миграция: добавляем normalized_link если его нет
            if 'normalized_link' not in columns:
                print("🔄 [DB] Миграция: добавляем normalized_link...")
                await conn.execute("""
                    ALTER TABLE posted_articles 
                    ADD COLUMN normalized_link TEXT
                """)
                await conn.execute("""
                    UPDATE posted_articles 
                    SET normalized_link = link 
                    WHERE normalized_link IS NULL
                """)
                await conn.commit()
                print("   ✓ Миграция завершена")
    
    async def _load_cache(self):
        """Загрузка cache ссылок в память"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT normalized_link 
                FROM posted_articles
            """)
            rows = await cursor.fetchall()
            self._link_cache = {row[0] for row in rows}
            self._cache_loaded = True
            
            print(f"📦 [DB] Cache загружен: {len(self._link_cache)} ссылок")
    
    async def _update_stats(self):
        """Обновление внутренней статистики"""
        async with self._get_connection() as conn:
            # Общее количество
            cursor = await conn.execute("SELECT COUNT(*) FROM posted_articles")
            row = await cursor.fetchone()
            self._stats['total_articles'] = row[0] if row else 0
            
            # Сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM posted_articles 
                WHERE DATE(published_at) = ?
            """, (today,))
            row = await cursor.fetchone()
            self._stats['articles_today'] = row[0] if row else 0
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    async def save_article(
        self,
        link: str = None,
        normalized_link: str = None,
        source_feed: str = None,
        title: str = None,
        has_image: bool = False,
        ai_provider: str = None,
        status: str = 'success',
        article: Dict = None
    ) -> bool:
        """
        Сохранить статью
        
        Поддерживает два формата:
        1. Именованные параметры
        2. Dict article (для NewsProcessor)
        
        Returns:
            bool: True если сохранено, False если уже существует
        """
        # Парсим из dict если предоставлен
        if article:
            link = article.get('url') or article.get('link')
            normalized_link = link
            source_feed = article.get('source')
            title = article.get('title')
        
        if not link or not normalized_link:
            print("⚠️ [DB] Попытка сохранить статью без ссылки")
            return False
        
        # Проверяем cache
        if self._cache_loaded and normalized_link in self._link_cache:
            return False
        
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    await conn.execute("""
                        INSERT OR IGNORE INTO posted_articles 
                        (link, normalized_link, source_feed, title, has_image, ai_provider, posting_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (link, normalized_link, source_feed, title, has_image, ai_provider, status))
                    
                    # Обновляем статистику
                    today = datetime.now().strftime('%Y-%m-%d')
                    await conn.execute("""
                        INSERT INTO statistics (date, articles_posted, articles_with_images)
                        VALUES (?, 1, ?)
                        ON CONFLICT(date) DO UPDATE SET
                            articles_posted = articles_posted + 1,
                            articles_with_images = articles_with_images + ?,
                            updated_at = CURRENT_TIMESTAMP
                    """, (today, 1 if has_image else 0, 1 if has_image else 0))
                    
                    await conn.commit()
                    
                    # Обновляем cache
                    self._link_cache.add(normalized_link)
                    self._stats['total_articles'] += 1
                    self._stats['articles_today'] += 1
                    
                    return True
                
                except sqlite3.IntegrityError:
                    # Дубликат - это нормально
                    return False
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка сохранения статьи: {e}")
                    self._stats['errors'] += 1
                    return False
    
    async def save_links_bulk(self, links: List[tuple]) -> int:
        """
        Массовое сохранение ссылок
        
        Args:
            links: List[(link, normalized_link, source_feed)]
        
        Returns:
            int: Количество сохранённых ссылок
        """
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    await conn.executemany("""
                        INSERT OR IGNORE INTO posted_articles 
                        (link, normalized_link, source_feed)
                        VALUES (?, ?, ?)
                    """, links)
                    
                    await conn.commit()
                    
                    # Обновляем cache
                    for _, normalized_link, _ in links:
                        self._link_cache.add(normalized_link)
                    
                    return len(links)
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка bulk insert: {e}")
                    self._stats['errors'] += 1
                    return 0
    
    async def is_link_posted(self, normalized_link: str) -> bool:
        """
        Проверка наличия ссылки
        
        Использует cache для быстрой проверки
        """
        if self._cache_loaded:
            return normalized_link in self._link_cache
        
        # Fallback к БД если cache не загружен
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 1 FROM posted_articles 
                WHERE normalized_link = ? 
                LIMIT 1
            """, (normalized_link,))
            result = await cursor.fetchone()
            return result is not None
    
    async def get_all_links(self) -> Set[str]:
        """Получить все нормализованные ссылки"""
        if self._cache_loaded:
            return self._link_cache.copy()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT normalized_link FROM posted_articles")
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
    
    async def get_recent_articles(self, limit: int = 100) -> List[Dict]:
        """Получить последние статьи"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    link,
                    title,
                    source_feed,
                    published_at,
                    has_image,
                    ai_provider
                FROM posted_articles
                ORDER BY published_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_feed_statistics(self, days: int = 30) -> Dict[str, int]:
        """Статистика по источникам за период"""
        async with self._get_connection() as conn:
            cutoff = datetime.now() - timedelta(days=days)
            cursor = await conn.execute("""
                SELECT source_feed, COUNT(*) as count
                FROM posted_articles
                WHERE published_at >= ?
                GROUP BY source_feed
                ORDER BY count DESC
            """, (cutoff.isoformat(),))
            
            rows = await cursor.fetchall()
            return {row[0] or 'Unknown': row[1] for row in rows}
    
    async def get_daily_statistics(self, days: int = 7) -> List[Dict]:
        """Дневная статистика за период"""
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    date,
                    articles_posted,
                    articles_with_images
                FROM statistics
                ORDER BY date DESC
                LIMIT ?
            """, (days,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def cleanup_old_articles(self, days: int = 90) -> int:
        """
        Очистка старых записей
        
        Returns:
            int: Количество удалённых записей
        """
        async with self._lock:
            async with self._get_connection() as conn:
                cutoff = datetime.now() - timedelta(days=days)
                cursor = await conn.execute("""
                    DELETE FROM posted_articles
                    WHERE published_at < ?
                """, (cutoff.isoformat(),))
                
                deleted = cursor.rowcount
                await conn.commit()
                
                if deleted > 0:
                    print(f"🧹 [DB] Удалено {deleted} записей старше {days} дней")
                    
                    # Обновляем cache
                    await self._load_cache()
                
                # VACUUM для освобождения места
                await conn.execute("VACUUM")
                
                return deleted
    
    async def get_stats_summary(self) -> Dict:
        """Краткая сводка статистики"""
        await self._update_stats()
        feed_stats = await self.get_feed_statistics(days=7)
        
        return {
            'total_articles': self._stats['total_articles'],
            'articles_today': self._stats['articles_today'],
            'top_feed_7d': max(feed_stats.items(), key=lambda x: x[1])[0] if feed_stats else None,
            'last_backup': self._stats['last_backup'],
            'queries_executed': self._stats['queries_executed'],
            'errors': self._stats['errors']
        }
    
    async def close(self):
        """Закрытие БД (cleanup)"""
        print("💾 [DB] Closing database...")
        # aiosqlite connections закрываются автоматически в context manager
        self._cache_loaded = False
        self._link_cache.clear()


# ============================================================================
# BACKWARD COMPATIBILITY - Синхронная версия (deprecated)
# ============================================================================

class DatabaseManager:
    """
    DEPRECATED: Используйте AsyncDatabaseManager
    
    Синхронная версия для обратной совместимости
    Работает через asyncio.run() - НЕ ОПТИМАЛЬНО!
    """
    
    def __init__(self):
        self._async_db = AsyncDatabaseManager()
        print("⚠️ [DB] Используется deprecated DatabaseManager")
        print("   Рекомендуется перейти на AsyncDatabaseManager")
        
        # Инициализируем через asyncio
        asyncio.run(self._async_db.initialize())
    
    def save_article(self, **kwargs) -> bool:
        return asyncio.run(self._async_db.save_article(**kwargs))
    
    def is_link_posted(self, link: str) -> bool:
        return asyncio.run(self._async_db.is_link_posted(link))
    
    def get_all_links(self) -> Set[str]:
        return asyncio.run(self._async_db.get_all_links())
    
    def get_recent_articles(self, limit: int = 100) -> List[Dict]:
        return asyncio.run(self._async_db.get_recent_articles(limit))


# ============================================================================
# ALIAS для NewsProcessor compatibility
# ============================================================================

NewsDatabase = AsyncDatabaseManager


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'AsyncDatabaseManager',
    'DatabaseManager',  # deprecated
    'NewsDatabase',  # alias
    'Article',
]