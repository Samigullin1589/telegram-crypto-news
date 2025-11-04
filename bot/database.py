# bot/database.py - ASYNC-SAFE DATABASE MANAGER v5.0

import sqlite3
import asyncio
import aiosqlite
import json
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Set, List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

try:
    from .config import config
    CONFIG_AVAILABLE = True
except ImportError:
    try:
        from bot.config import config
        CONFIG_AVAILABLE = True
    except ImportError:
        CONFIG_AVAILABLE = False
        class DummyConfig:
            DB_PATH = 'news_database.sqlite'
            NEWS_DB_PATH = 'news_database.sqlite'
        config = DummyConfig()


class PostingStatus(str, Enum):
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'
    SKIPPED = 'skipped'


@dataclass
class Article:
    link: str
    normalized_link: str
    source_feed: str
    title: str
    has_image: bool = False
    ai_provider: Optional[str] = None
    posting_status: str = 'success'
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'link': self.link,
            'normalized_link': self.normalized_link,
            'source_feed': self.source_feed,
            'title': self.title,
            'has_image': self.has_image,
            'ai_provider': self.ai_provider,
            'posting_status': self.posting_status,
            'published_at': self.published_at.isoformat() if isinstance(self.published_at, datetime) else self.published_at,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        if isinstance(data.get('published_at'), str):
            data['published_at'] = datetime.fromisoformat(data['published_at'])
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class DatabaseStats:
    total_articles: int = 0
    articles_today: int = 0
    articles_this_week: int = 0
    articles_this_month: int = 0
    total_sources: int = 0
    articles_with_images: int = 0
    average_articles_per_day: float = 0.0
    most_active_source: Optional[str] = None
    last_article_time: Optional[datetime] = None
    cache_size: int = 0
    queries_executed: int = 0
    errors: int = 0
    last_backup: Optional[datetime] = None
    database_size_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_articles': self.total_articles,
            'articles_today': self.articles_today,
            'articles_this_week': self.articles_this_week,
            'articles_this_month': self.articles_this_month,
            'total_sources': self.total_sources,
            'articles_with_images': self.articles_with_images,
            'average_articles_per_day': self.average_articles_per_day,
            'most_active_source': self.most_active_source,
            'last_article_time': self.last_article_time.isoformat() if self.last_article_time else None,
            'cache_size': self.cache_size,
            'queries_executed': self.queries_executed,
            'errors': self.errors,
            'last_backup': self.last_backup.isoformat() if self.last_backup else None,
            'database_size_mb': self.database_size_mb,
        }


class AsyncDatabaseManager:
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = Path(db_path)
        elif CONFIG_AVAILABLE:
            if hasattr(config, 'NEWS_DB_PATH'):
                self.db_path = Path(config.NEWS_DB_PATH)
            elif hasattr(config, 'DB_PATH'):
                self.db_path = Path(config.DB_PATH)
            else:
                self.db_path = Path('news_database.sqlite')
        else:
            self.db_path = Path('news_database.sqlite')
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = asyncio.Lock()
        self._connection: Optional[aiosqlite.Connection] = None
        
        self._stats = DatabaseStats()
        
        self._link_cache: Set[str] = set()
        self._source_cache: Set[str] = set()
        self._cache_loaded = False
        
        self._max_cache_size = 100000
        self._cache_ttl_hours = 24
        self._last_cache_refresh: Optional[datetime] = None
        
        print(f"💾 [DB] AsyncDatabaseManager v5.0 инициализирован")
        print(f"   Path: {self.db_path}")
    
    async def initialize(self):
        async with self._lock:
            await self._create_tables()
            await self._run_migrations()
            await self._create_indexes()
            await self._load_cache()
            await self._update_stats()
            await self._optimize_database()
            
            print(f"✅ [DB] База данных готова")
            print(f"   Всего статей: {self._stats.total_articles}")
            print(f"   Сегодня: {self._stats.articles_today}")
            print(f"   Размер: {self._stats.database_size_mb:.2f}MB")
    
    @asynccontextmanager
    async def _get_connection(self):
        conn = await aiosqlite.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level=None
        )
        
        try:
            conn.row_factory = aiosqlite.Row
            
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-64000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            await conn.execute("PRAGMA mmap_size=268435456")
            await conn.execute("PRAGMA page_size=4096")
            await conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
            
            yield conn
        
        except Exception as e:
            print(f"❌ [DB] Connection error: {e}")
            self._stats.errors += 1
            raise
        
        finally:
            await conn.close()
    
    async def _create_tables(self):
        async with self._get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT UNIQUE NOT NULL,
                    normalized_link TEXT NOT NULL,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_feed TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT,
                    has_image BOOLEAN DEFAULT 0,
                    image_url TEXT,
                    ai_provider TEXT,
                    ai_score INTEGER,
                    posting_status TEXT DEFAULT 'success',
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    date TEXT PRIMARY KEY,
                    articles_posted INTEGER DEFAULT 0,
                    articles_with_images INTEGER DEFAULT 0,
                    articles_by_source TEXT,
                    articles_by_status TEXT,
                    total_ai_score INTEGER DEFAULT 0,
                    average_ai_score REAL DEFAULT 0.0,
                    errors_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    last_fetch_at TIMESTAMP,
                    total_articles INTEGER DEFAULT 0,
                    successful_articles INTEGER DEFAULT 0,
                    failed_articles INTEGER DEFAULT 0,
                    average_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_path TEXT NOT NULL,
                    backup_size_mb REAL,
                    articles_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_type TEXT NOT NULL,
                    execution_time_ms REAL,
                    rows_affected INTEGER,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.commit()
            self._stats.queries_executed += 6
    
    async def _create_indexes(self):
        async with self._get_connection() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_published_at ON posted_articles(published_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_normalized_link ON posted_articles(normalized_link)",
                "CREATE INDEX IF NOT EXISTS idx_source_feed ON posted_articles(source_feed)",
                "CREATE INDEX IF NOT EXISTS idx_posting_status ON posted_articles(posting_status)",
                "CREATE INDEX IF NOT EXISTS idx_has_image ON posted_articles(has_image)",
                "CREATE INDEX IF NOT EXISTS idx_ai_provider ON posted_articles(ai_provider)",
                "CREATE INDEX IF NOT EXISTS idx_created_at ON posted_articles(created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_source_name ON sources(name)",
                "CREATE INDEX IF NOT EXISTS idx_source_enabled ON sources(enabled)",
                "CREATE INDEX IF NOT EXISTS idx_stats_date ON statistics(date DESC)",
            ]
            
            for index_sql in indexes:
                await conn.execute(index_sql)
            
            await conn.commit()
            self._stats.queries_executed += len(indexes)
    
    async def _run_migrations(self):
        async with self._get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(posted_articles)")
            columns = {row[1] for row in await cursor.fetchall()}
            
            migrations_applied = 0
            
            if 'normalized_link' not in columns:
                print("🔄 [DB] Миграция: добавляем normalized_link...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN normalized_link TEXT")
                await conn.execute("UPDATE posted_articles SET normalized_link = link WHERE normalized_link IS NULL")
                migrations_applied += 1
            
            if 'description' not in columns:
                print("🔄 [DB] Миграция: добавляем description...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN description TEXT")
                migrations_applied += 1
            
            if 'content' not in columns:
                print("🔄 [DB] Миграция: добавляем content...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN content TEXT")
                migrations_applied += 1
            
            if 'image_url' not in columns:
                print("🔄 [DB] Миграция: добавляем image_url...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN image_url TEXT")
                migrations_applied += 1
            
            if 'ai_score' not in columns:
                print("🔄 [DB] Миграция: добавляем ai_score...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN ai_score INTEGER")
                migrations_applied += 1
            
            if 'error_message' not in columns:
                print("🔄 [DB] Миграция: добавляем error_message...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN error_message TEXT")
                migrations_applied += 1
            
            if 'retry_count' not in columns:
                print("🔄 [DB] Миграция: добавляем retry_count...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN retry_count INTEGER DEFAULT 0")
                migrations_applied += 1
            
            if 'updated_at' not in columns:
                print("🔄 [DB] Миграция: добавляем updated_at...")
                await conn.execute("ALTER TABLE posted_articles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                migrations_applied += 1
            
            if migrations_applied > 0:
                await conn.commit()
                print(f"   ✓ Применено миграций: {migrations_applied}")
    
    async def _load_cache(self):
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT normalized_link FROM posted_articles")
            rows = await cursor.fetchall()
            self._link_cache = {row[0] for row in rows if row[0]}
            
            cursor = await conn.execute("SELECT DISTINCT source_feed FROM posted_articles WHERE source_feed IS NOT NULL")
            rows = await cursor.fetchall()
            self._source_cache = {row[0] for row in rows}
            
            self._cache_loaded = True
            self._last_cache_refresh = datetime.now(timezone.utc)
            self._stats.cache_size = len(self._link_cache)
            
            print(f"📦 [DB] Cache загружен: {len(self._link_cache)} ссылок, {len(self._source_cache)} источников")
    
    async def _refresh_cache_if_needed(self):
        if not self._last_cache_refresh:
            return
        
        hours_since_refresh = (datetime.now(timezone.utc) - self._last_cache_refresh).total_seconds() / 3600
        
        if hours_since_refresh >= self._cache_ttl_hours or len(self._link_cache) > self._max_cache_size:
            print("🔄 [DB] Обновление cache...")
            await self._load_cache()
    
    async def _update_stats(self):
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM posted_articles")
            row = await cursor.fetchone()
            self._stats.total_articles = row[0] if row else 0
            
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM posted_articles 
                WHERE DATE(published_at) = ?
            """, (today,))
            row = await cursor.fetchone()
            self._stats.articles_today = row[0] if row else 0
            
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM posted_articles 
                WHERE published_at >= ?
            """, (week_ago,))
            row = await cursor.fetchone()
            self._stats.articles_this_week = row[0] if row else 0
            
            month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM posted_articles 
                WHERE published_at >= ?
            """, (month_ago,))
            row = await cursor.fetchone()
            self._stats.articles_this_month = row[0] if row else 0
            
            cursor = await conn.execute("SELECT COUNT(DISTINCT source_feed) FROM posted_articles")
            row = await cursor.fetchone()
            self._stats.total_sources = row[0] if row else 0
            
            cursor = await conn.execute("SELECT COUNT(*) FROM posted_articles WHERE has_image = 1")
            row = await cursor.fetchone()
            self._stats.articles_with_images = row[0] if row else 0
            
            cursor = await conn.execute("""
                SELECT source_feed, COUNT(*) as cnt 
                FROM posted_articles 
                GROUP BY source_feed 
                ORDER BY cnt DESC 
                LIMIT 1
            """)
            row = await cursor.fetchone()
            if row:
                self._stats.most_active_source = row[0]
            
            cursor = await conn.execute("""
                SELECT MAX(published_at) FROM posted_articles
            """)
            row = await cursor.fetchone()
            if row and row[0]:
                try:
                    self._stats.last_article_time = datetime.fromisoformat(row[0])
                except:
                    self._stats.last_article_time = None
            
            if self._stats.total_articles > 0:
                cursor = await conn.execute("""
                    SELECT 
                        JULIANDAY('now') - JULIANDAY(MIN(created_at)) as days
                    FROM posted_articles
                """)
                row = await cursor.fetchone()
                if row and row[0] and row[0] > 0:
                    self._stats.average_articles_per_day = self._stats.total_articles / row[0]
            
            try:
                db_size_bytes = self.db_path.stat().st_size
                self._stats.database_size_mb = db_size_bytes / (1024 * 1024)
            except:
                self._stats.database_size_mb = 0.0
    
    async def _optimize_database(self):
        async with self._get_connection() as conn:
            await conn.execute("PRAGMA optimize")
            await conn.execute("PRAGMA incremental_vacuum")
    
    async def save_article(
        self,
        link: str = None,
        normalized_link: str = None,
        source_feed: str = None,
        title: str = None,
        description: str = None,
        content: str = None,
        has_image: bool = False,
        image_url: str = None,
        ai_provider: str = None,
        ai_score: int = None,
        status: str = 'success',
        error_message: str = None,
        article: Dict = None
    ) -> bool:
        if article:
            link = article.get('url') or article.get('link')
            normalized_link = article.get('normalized_link') or link
            source_feed = article.get('source') or article.get('source_feed')
            title = article.get('title')
            description = article.get('description')
            content = article.get('content')
            has_image = article.get('has_image', False)
            image_url = article.get('image_url')
            ai_provider = article.get('ai_provider')
            ai_score = article.get('ai_score')
        
        if not link or not normalized_link or not source_feed or not title:
            print("⚠️ [DB] Попытка сохранить статью без обязательных полей")
            return False
        
        if self._cache_loaded and normalized_link in self._link_cache:
            return False
        
        await self._refresh_cache_if_needed()
        
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    await conn.execute("""
                        INSERT OR IGNORE INTO posted_articles 
                        (link, normalized_link, source_feed, title, description, content, 
                         has_image, image_url, ai_provider, ai_score, posting_status, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (link, normalized_link, source_feed, title, description, content,
                          has_image, image_url, ai_provider, ai_score, status, error_message))
                    
                    if conn.total_changes == 0:
                        return False
                    
                    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    await conn.execute("""
                        INSERT INTO statistics (date, articles_posted, articles_with_images)
                        VALUES (?, 1, ?)
                        ON CONFLICT(date) DO UPDATE SET
                            articles_posted = articles_posted + 1,
                            articles_with_images = articles_with_images + ?,
                            updated_at = CURRENT_TIMESTAMP
                    """, (today, 1 if has_image else 0, 1 if has_image else 0))
                    
                    await conn.execute("""
                        INSERT INTO sources (name, url, total_articles, successful_articles, failed_articles)
                        VALUES (?, ?, 1, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            total_articles = total_articles + 1,
                            successful_articles = successful_articles + ?,
                            failed_articles = failed_articles + ?,
                            last_fetch_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                    """, (source_feed, '', 1 if status == 'success' else 0, 1 if status == 'failed' else 0,
                          1 if status == 'success' else 0, 1 if status == 'failed' else 0))
                    
                    await conn.commit()
                    
                    self._link_cache.add(normalized_link)
                    self._source_cache.add(source_feed)
                    self._stats.total_articles += 1
                    self._stats.articles_today += 1
                    self._stats.cache_size = len(self._link_cache)
                    
                    return True
                
                except sqlite3.IntegrityError:
                    return False
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка сохранения статьи: {e}")
                    self._stats.errors += 1
                    return False
    
    async def update_article(
        self,
        link: str,
        updates: Dict[str, Any]
    ) -> bool:
        if not link or not updates:
            return False
        
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
                    set_clause += ", updated_at = CURRENT_TIMESTAMP"
                    values = list(updates.values()) + [link]
                    
                    await conn.execute(f"""
                        UPDATE posted_articles 
                        SET {set_clause}
                        WHERE link = ?
                    """, values)
                    
                    await conn.commit()
                    
                    return conn.total_changes > 0
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка обновления статьи: {e}")
                    self._stats.errors += 1
                    return False
    
    async def save_links_bulk(self, articles: List[Dict[str, Any]]) -> int:
        if not articles:
            return 0
        
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    saved_count = 0
                    
                    for article in articles:
                        link = article.get('link')
                        normalized_link = article.get('normalized_link') or link
                        source_feed = article.get('source_feed')
                        title = article.get('title')
                        
                        if not all([link, normalized_link, source_feed, title]):
                            continue
                        
                        if normalized_link in self._link_cache:
                            continue
                        
                        await conn.execute("""
                            INSERT OR IGNORE INTO posted_articles 
                            (link, normalized_link, source_feed, title, has_image)
                            VALUES (?, ?, ?, ?, ?)
                        """, (link, normalized_link, source_feed, title, article.get('has_image', False)))
                        
                        if conn.total_changes > 0:
                            self._link_cache.add(normalized_link)
                            saved_count += 1
                    
                    await conn.commit()
                    
                    return saved_count
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка bulk insert: {e}")
                    self._stats.errors += 1
                    return 0
    
    async def is_link_posted(self, normalized_link: str) -> bool:
        if not normalized_link:
            return False
        
        if self._cache_loaded:
            return normalized_link in self._link_cache
        
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 1 FROM posted_articles 
                WHERE normalized_link = ? 
                LIMIT 1
            """, (normalized_link,))
            result = await cursor.fetchone()
            return result is not None
    
    async def get_article_by_link(self, link: str) -> Optional[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT * FROM posted_articles 
                WHERE link = ? OR normalized_link = ?
                LIMIT 1
            """, (link, link))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_all_links(self) -> Set[str]:
        if self._cache_loaded:
            return self._link_cache.copy()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute("SELECT normalized_link FROM posted_articles")
            rows = await cursor.fetchall()
            return {row[0] for row in rows if row[0]}
    
    async def get_recent_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        source_feed: Optional[str] = None,
        has_image: Optional[bool] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conditions = []
        params = []
        
        if source_feed:
            conditions.append("source_feed = ?")
            params.append(source_feed)
        
        if has_image is not None:
            conditions.append("has_image = ?")
            params.append(1 if has_image else 0)
        
        if status:
            conditions.append("posting_status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        params.extend([limit, offset])
        
        async with self._get_connection() as conn:
            cursor = await conn.execute(f"""
                SELECT * FROM posted_articles
                WHERE {where_clause}
                ORDER BY published_at DESC
                LIMIT ? OFFSET ?
            """, params)
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def search_articles(
        self,
        search_term: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        search_pattern = f"%{search_term}%"
        
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT * FROM posted_articles
                WHERE title LIKE ? OR description LIKE ? OR content LIKE ?
                ORDER BY published_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_articles_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT * FROM posted_articles
                WHERE published_at BETWEEN ? AND ?
                ORDER BY published_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_feed_statistics(self, days: int = 30) -> Dict[str, int]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT source_feed, COUNT(*) as count
                FROM posted_articles
                WHERE published_at >= ?
                GROUP BY source_feed
                ORDER BY count DESC
            """, (cutoff,))
            
            rows = await cursor.fetchall()
            return {row[0] or 'Unknown': row[1] for row in rows}
    
    async def get_daily_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    date,
                    articles_posted,
                    articles_with_images,
                    average_ai_score,
                    errors_count
                FROM statistics
                ORDER BY date DESC
                LIMIT ?
            """, (days,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_source_statistics(self) -> List[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    name,
                    total_articles,
                    successful_articles,
                    failed_articles,
                    average_score,
                    last_fetch_at
                FROM sources
                ORDER BY total_articles DESC
            """)
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_failed_articles(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT * FROM posted_articles
                WHERE posting_status = 'failed'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def delete_article(self, link: str) -> bool:
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    await conn.execute("""
                        DELETE FROM posted_articles
                        WHERE link = ? OR normalized_link = ?
                    """, (link, link))
                    
                    await conn.commit()
                    
                    if conn.total_changes > 0:
                        if link in self._link_cache:
                            self._link_cache.remove(link)
                        return True
                    
                    return False
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка удаления статьи: {e}")
                    self._stats.errors += 1
                    return False
    
    async def cleanup_old_articles(self, days: int = 90) -> int:
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                    
                    cursor = await conn.execute("""
                        DELETE FROM posted_articles
                        WHERE published_at < ?
                    """, (cutoff,))
                    
                    deleted = cursor.rowcount
                    await conn.commit()
                    
                    if deleted > 0:
                        print(f"🧹 [DB] Удалено {deleted} записей старше {days} дней")
                        await self._load_cache()
                    
                    await conn.execute("VACUUM")
                    
                    return deleted
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка очистки: {e}")
                    self._stats.errors += 1
                    return 0
    
    async def cleanup_failed_articles(self, older_than_days: int = 7) -> int:
        async with self._lock:
            async with self._get_connection() as conn:
                try:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
                    
                    cursor = await conn.execute("""
                        DELETE FROM posted_articles
                        WHERE posting_status = 'failed' AND created_at < ?
                    """, (cutoff,))
                    
                    deleted = cursor.rowcount
                    await conn.commit()
                    
                    if deleted > 0:
                        print(f"🧹 [DB] Удалено {deleted} failed записей")
                    
                    return deleted
                
                except Exception as e:
                    print(f"❌ [DB] Ошибка очистки failed: {e}")
                    self._stats.errors += 1
                    return 0
    
    async def create_backup(self, backup_dir: Optional[Path] = None) -> Optional[Path]:
        if backup_dir is None:
            backup_dir = self.db_path.parent / 'backups'
        
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_path)
            
            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            
            async with self._get_connection() as conn:
                await conn.execute("""
                    INSERT INTO backups (backup_path, backup_size_mb, articles_count)
                    VALUES (?, ?, ?)
                """, (str(backup_path), backup_size_mb, self._stats.total_articles))
                
                await conn.commit()
            
            self._stats.last_backup = datetime.now(timezone.utc)
            
            print(f"💾 [DB] Backup создан: {backup_path} ({backup_size_mb:.2f}MB)")
            
            return backup_path
        
        except Exception as e:
            print(f"❌ [DB] Ошибка создания backup: {e}")
            self._stats.errors += 1
            return None
    
    async def cleanup_old_backups(self, keep_count: int = 7) -> int:
        backup_dir = self.db_path.parent / 'backups'
        
        if not backup_dir.exists():
            return 0
        
        try:
            backups = sorted(backup_dir.glob('backup_*.db'), key=lambda x: x.stat().st_mtime, reverse=True)
            
            removed_count = 0
            for backup_file in backups[keep_count:]:
                backup_file.unlink()
                removed_count += 1
            
            if removed_count > 0:
                print(f"🧹 [DB] Удалено старых backups: {removed_count}")
            
            return removed_count
        
        except Exception as e:
            print(f"❌ [DB] Ошибка очистки backups: {e}")
            return 0
    
    async def export_to_json(self, output_path: Path, limit: Optional[int] = None) -> bool:
        try:
            articles = await self.get_recent_articles(limit=limit or 1000000)
            
            export_data = {
                'export_date': datetime.now(timezone.utc).isoformat(),
                'total_articles': len(articles),
                'database_stats': self._stats.to_dict(),
                'articles': articles
            }
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"📤 [DB] Экспорт в JSON: {output_path}")
            return True
        
        except Exception as e:
            print(f"❌ [DB] Ошибка экспорта в JSON: {e}")
            self._stats.errors += 1
            return False
    
    async def import_from_json(self, input_path: Path) -> int:
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = data.get('articles', [])
            imported_count = 0
            
            for article_data in articles:
                success = await self.save_article(article=article_data)
                if success:
                    imported_count += 1
            
            print(f"📥 [DB] Импортировано статей: {imported_count}/{len(articles)}")
            return imported_count
        
        except Exception as e:
            print(f"❌ [DB] Ошибка импорта из JSON: {e}")
            self._stats.errors += 1
            return 0
    
    async def get_stats_summary(self) -> DatabaseStats:
        await self._update_stats()
        return self._stats
    
    async def get_full_stats(self) -> Dict[str, Any]:
        await self._update_stats()
        
        feed_stats = await self.get_feed_statistics(days=30)
        daily_stats = await self.get_daily_statistics(days=7)
        source_stats = await self.get_source_statistics()
        
        return {
            'database': self._stats.to_dict(),
            'feeds': feed_stats,
            'daily': daily_stats,
            'sources': source_stats,
        }
    
    async def set_metadata(self, key: str, value: Any, description: str = None):
        value_type = type(value).__name__
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        async with self._get_connection() as conn:
            await conn.execute("""
                INSERT INTO metadata (key, value, type, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    type = excluded.type,
                    description = excluded.description,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value_str, value_type, description))
            
            await conn.commit()
    
    async def get_metadata(self, key: str, default: Any = None) -> Any:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT value, type FROM metadata WHERE key = ?
            """, (key,))
            
            row = await cursor.fetchone()
            
            if not row:
                return default
            
            value_str, value_type = row
            
            if value_type == 'str':
                return value_str
            else:
                try:
                    return json.loads(value_str)
                except:
                    return value_str
    
    async def log_query(
        self,
        query_type: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        success: bool = True,
        error_message: str = None
    ):
        async with self._get_connection() as conn:
            await conn.execute("""
                INSERT INTO query_log 
                (query_type, execution_time_ms, rows_affected, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (query_type, execution_time_ms, rows_affected, success, error_message))
            
            await conn.commit()
    
    async def get_query_performance(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    query_type,
                    AVG(execution_time_ms) as avg_time,
                    MAX(execution_time_ms) as max_time,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
                FROM query_log
                GROUP BY query_type
                ORDER BY avg_time DESC
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def vacuum_database(self):
        async with self._get_connection() as conn:
            await conn.execute("VACUUM")
            print("🧹 [DB] VACUUM выполнен")
    
    async def analyze_database(self):
        async with self._get_connection() as conn:
            await conn.execute("ANALYZE")
            print("📊 [DB] ANALYZE выполнен")
    
    async def check_integrity(self) -> bool:
        async with self._get_connection() as conn:
            cursor = await conn.execute("PRAGMA integrity_check")
            result = await cursor.fetchone()
            
            is_ok = result and result[0] == 'ok'
            
            if is_ok:
                print("✅ [DB] Целостность БД в порядке")
            else:
                print(f"❌ [DB] Проблемы целостности: {result}")
            
            return is_ok
    
    async def close(self):
        print("💾 [DB] Closing database...")
        
        if self._cache_loaded:
            self._cache_loaded = False
            self._link_cache.clear()
            self._source_cache.clear()
        
        if self._connection:
            await self._connection.close()
            self._connection = None


class DatabaseManager:
    
    def __init__(self, db_path: Optional[Path] = None):
        self._async_db = AsyncDatabaseManager(db_path)
        print("⚠️ [DB] Используется deprecated DatabaseManager")
        print("   Рекомендуется перейти на AsyncDatabaseManager")
        
        try:
            asyncio.run(self._async_db.initialize())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_db.initialize())
            loop.close()
    
    def save_article(self, **kwargs) -> bool:
        try:
            return asyncio.run(self._async_db.save_article(**kwargs))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_db.save_article(**kwargs))
            loop.close()
            return result
    
    def is_link_posted(self, link: str) -> bool:
        try:
            return asyncio.run(self._async_db.is_link_posted(link))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_db.is_link_posted(link))
            loop.close()
            return result
    
    def get_all_links(self) -> Set[str]:
        try:
            return asyncio.run(self._async_db.get_all_links())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_db.get_all_links())
            loop.close()
            return result
    
    def get_recent_articles(self, limit: int = 100) -> List[Dict]:
        try:
            return asyncio.run(self._async_db.get_recent_articles(limit))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_db.get_recent_articles(limit))
            loop.close()
            return result


NewsDatabase = AsyncDatabaseManager


__all__ = [
    'AsyncDatabaseManager',
    'DatabaseManager',
    'NewsDatabase',
    'Article',
    'DatabaseStats',
    'PostingStatus',
]