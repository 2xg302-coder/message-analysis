import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
from config import settings
from core.logging import get_logger

logger = get_logger("database")

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise e
        finally:
            conn.close()

    def _init_db(self):
        try:
            with self.get_cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        link TEXT,
                        content TEXT,
                        time TEXT,
                        timestamp TEXT,
                        scraped_at TEXT,
                        created_at TEXT,
                        source TEXT,
                        raw_data TEXT,
                        analysis TEXT,
                        analyzed_at TEXT,
                        type TEXT DEFAULT 'article',
                        tags TEXT,
                        entities TEXT,
                        impact_score INTEGER,
                        sentiment_score REAL,
                        simhash TEXT
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS watchlist (
                        keyword TEXT PRIMARY KEY,
                        created_at TEXT
                    )
                ''')
                # Calendar Events Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS calendar_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,          -- YYYY-MM-DD
                        time TEXT,
                        country TEXT,
                        event TEXT,
                        importance INTEGER,
                        previous TEXT,
                        consensus TEXT,
                        actual TEXT,
                        UNIQUE(date, event, country)
                    )
                ''')
                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_created_at ON news(created_at DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_impact_score ON news(impact_score)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_analysis ON news(analysis)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date)")
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {query}, error: {e}")
            return []

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return True
        except Exception as e:
            logger.error(f"Update execution failed: {query}, error: {e}")
            return False

# Global instance
db = DatabaseManager(settings.DB_PATH)
