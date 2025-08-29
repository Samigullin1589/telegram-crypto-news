# bot/database.py
import sqlite3
from . import config

class DatabaseManager:
    def __init__(self):
        self.db_path = config.DB_PATH
        self.setup()

    def setup(self):
        with self._get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS posted_articles (link TEXT PRIMARY KEY, published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.commit()
        print(f"💾 [DB] База данных готова: {self.db_path}")

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_link(self, link):
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO posted_articles (link) VALUES (?)", (link,))
            conn.commit()

    def save_links_bulk(self, links):
        with self._get_connection() as conn:
            conn.executemany("INSERT OR IGNORE INTO posted_articles (link) VALUES (?)", [(link,) for link in links])
            conn.commit()

    def get_all_links(self):
        with self._get_connection() as conn:
            return {row[0] for row in conn.execute("SELECT link FROM posted_articles")}