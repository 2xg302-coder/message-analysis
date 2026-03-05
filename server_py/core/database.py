import aiosqlite
import sqlite3
import json
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from config import settings
from core.logging import get_logger

logger = get_logger("database")

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Init DB synchronously on startup to ensure tables exist
        self._init_db_sync()

    def _init_db_sync(self):
        """Synchronous initialization for startup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully (Sync)")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        try:
            async with self.get_connection() as conn:
                async with conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {query}, error: {e}")
            return []

    async def execute_update(self, query: str, params: tuple = ()) -> bool:
        try:
            async with self.get_connection() as conn:
                await conn.execute(query, params)
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Update execution failed: {query}, error: {e}")
            return False

    async def execute_script(self, script: str) -> bool:
        try:
            async with self.get_connection() as conn:
                await conn.executescript(script)
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Script execution failed, error: {e}")
            return False

# Global instance
db = DatabaseManager(settings.DB_PATH)