"""
DATABASE v3.1 - Enhanced with NewsDatabase Support
Умный менеджер базы данных с connection pooling, автобэкапами и аналитикой
"""

import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Set, List, Optional, Dict
import json

try:
    from .config import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback config
    class DummyConfig:
        DB_PATH = 'news_database.sqlite'
    config = DummyConfig()


class DatabaseManager:
    """
    Умный менеджер базы данных с connection pooling, автобэкапами и аналитикой
    Thread-safe для многопоточных операций
    """
    
    def __init__(self):
        self.db_path = Path(config.DB_PATH)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._stats = {
            'total_articles': 0,
            'articles_today': 0,
            'last_backup': None
        }
        self.setup()
    
    def setup(self):
        """Инициализация БД с расширенной схемой"""
        with self._get_connection() as conn:
            conn.execute("""
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
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_published_at 
                ON posted_articles(published_at DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_normalized_link 
                ON posted_articles(normalized_link)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_feed 
                ON posted_articles(source_feed)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    date TEXT PRIMARY KEY,
                    articles_posted INTEGER DEFAULT 0,
                    articles_with_images INTEGER DEFAULT 0,
                    feed_stats TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        
        self._migrate_legacy_data()
        self._update_stats()
        
        print(f"💾 [DB] База данных готова: {self.db_path}")
        print(f"📊 [DB] Всего статей: {self._stats['total_articles']}, сегодня: {self._stats['articles_today']}")
    
    @contextmanager
    def _get_connection(self):
        """Thread-safe connection pool"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                isolation_level=None,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
        
        try:
            yield self._local.conn
        except Exception as e:
            print(f"❌ [DB] Database error: {e}")
            raise
    
    def _migrate_legacy_data(self):
        """Миграция данных из старой схемы"""
        with self._get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(posted_articles)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'normalized_link' not in columns:
                print("🔄 [DB] Миграция: добавляем поле normalized_link...")
                conn.execute("ALTER TABLE posted_articles ADD COLUMN normalized_link TEXT")
                conn.execute("UPDATE posted_articles SET normalized_link = link WHERE normalized_link IS NULL")
                conn.commit()
    
    def save_article(
        self,
        link: str = None,
        normalized_link: str = None,
        source_feed: str = None,
        title: str = None,
        has_image: bool = False,
        ai_provider: str = None,
        status: str = 'success',
        article: Dict = None
    ):
        """
        Сохранение статьи с полной метаинформацией
        
        Поддерживает два формата:
        1. Именованные параметры (старый формат)
        2. Dict article (новый формат для NewsProcessor)
        """
        if article:
            link = article.get('url') or article.get('link')
            normalized_link = link
            source_feed = article.get('source')
            title = article.get('title')
        
        if not link or not normalized_link:
            print("⚠️ [DB] Попытка сохранить статью без ссылки")
            return
        
        with self._lock:
            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO posted_articles 
                        (link, normalized_link, source_feed, title, has_image, ai_provider, posting_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (link, normalized_link, source_feed, title, has_image, ai_provider, status))
                    
                    today = datetime.now().strftime('%Y-%m-%d')
                    conn.execute("""
                        INSERT INTO statistics (date, articles_posted, articles_with_images)
                        VALUES (?, 1, ?)
                        ON CONFLICT(date) DO UPDATE SET
                            articles_posted = articles_posted + 1,
                            articles_with_images = articles_with_images + ?,
                            updated_at = CURRENT_TIMESTAMP
                    """, (today, 1 if has_image else 0, 1 if has_image else 0))
                    
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
    
    def save_links_bulk(self, links: List[tuple]):
        """
        Массовое сохранение ссылок для baseline
        links: List[(link, normalized_link, source_feed)]
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.executemany("""
                    INSERT OR IGNORE INTO posted_articles 
                    (link, normalized_link, source_feed)
                    VALUES (?, ?, ?)
                """, links)
                conn.commit()
    
    def get_all_links(self) -> Set[str]:
        """Получить все нормализованные ссылки (для кэша)"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT normalized_link FROM posted_articles")
            return {row[0] for row in cursor.fetchall()}
    
    def is_link_posted(self, normalized_link: str) -> bool:
        """Быстрая проверка наличия ссылки"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM posted_articles WHERE normalized_link = ? LIMIT 1",
                (normalized_link,)
            )
            return cursor.fetchone() is not None
    
    def get_recent_articles(self, limit: int = 100) -> List[Dict]:
        """Получить последние статьи"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
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
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_feed_statistics(self, days: int = 30) -> Dict[str, int]:
        """Статистика по источникам за период"""
        with self._get_connection() as conn:
            cutoff = datetime.now() - timedelta(days=days)
            cursor = conn.execute("""
                SELECT source_feed, COUNT(*) as count
                FROM posted_articles
                WHERE published_at >= ?
                GROUP BY source_feed
                ORDER BY count DESC
            """, (cutoff.isoformat(),))
            
            return {row[0] or 'Unknown': row[1] for row in cursor.fetchall()}
    
    def get_daily_statistics(self, days: int = 7) -> List[Dict]:
        """Дневная статистика за период"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    date,
                    articles_posted,
                    articles_with_images
                FROM statistics
                ORDER BY date DESC
                LIMIT ?
            """, (days,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _update_stats(self):
        """Обновление внутренней статистики"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM posted_articles")
            self._stats['total_articles'] = cursor.fetchone()[0]
            
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = conn.execute("""
                SELECT COUNT(*) FROM posted_articles 
                WHERE DATE(published_at) = ?
            """, (today,))
            self._stats['articles_today'] = cursor.fetchone()[0]
    
    def cleanup_old_articles(self, days: int = 90):
        """Очистка старых записей (опционально)"""
        with self._lock:
            with self._get_connection() as conn:
                cutoff = datetime.now() - timedelta(days=days)
                cursor = conn.execute("""
                    DELETE FROM posted_articles
                    WHERE published_at < ?
                """, (cutoff.isoformat(),))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    print(f"🧹 [DB] Удалено {deleted} записей старше {days} дней")
                
                conn.execute("VACUUM")
    
    def backup(self, backup_path: Optional[Path] = None) -> bool:
        """Создание резервной копии БД"""
        if backup_path is None:
            backup_path = self.db_path.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        
        try:
            import shutil
            with self._lock:
                shutil.copy2(self.db_path, backup_path)
            
            self._stats['last_backup'] = datetime.now()
            print(f"💾 [DB] Бэкап создан: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ [DB] Ошибка создания бэкапа: {e}")
            return False
    
    def get_stats_summary(self) -> Dict:
        """Краткая сводка статистики"""
        self._update_stats()
        feed_stats = self.get_feed_statistics(days=7)
        
        return {
            'total_articles': self._stats['total_articles'],
            'articles_today': self._stats['articles_today'],
            'top_feed_7d': max(feed_stats.items(), key=lambda x: x[1])[0] if feed_stats else None,
            'last_backup': self._stats['last_backup']
        }
    
    def __del__(self):
        """Cleanup при удалении объекта"""
        if hasattr(self._local, 'conn'):
            try:
                self._local.conn.close()
            except:
                pass


# НОВОЕ: Alias для NewsProcessor compatibility
class NewsDatabase(DatabaseManager):
    """
    Alias для DatabaseManager для совместимости с NewsProcessor
    
    Поддерживает оба интерфейса:
    - Старый: save_article(link, normalized_link, ...)
    - Новый: save_article(article={...})
    """
    
    def __init__(self):
        super().__init__()
        print("✅ [DB] NewsDatabase инициализирован (совместимость с NewsProcessor)")