import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'news.db')

def migrate():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check if 'series' table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='series'")
    if not cursor.fetchone():
        print("Creating 'series' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                keywords TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                current_summary TEXT,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_series_title ON series (title)")

    # 2. Check if 'storylines' has 'related_news_ids'
    cursor.execute("PRAGMA table_info(storylines)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'related_news_ids' not in columns:
        print("Adding 'related_news_ids' column to 'storylines' table...")
        cursor.execute("ALTER TABLE storylines ADD COLUMN related_news_ids TEXT DEFAULT '[]'")
    
    # 3. Check if 'storylines' has 'series_id' (it should, but just in case)
    if 'series_id' not in columns:
        print("Adding 'series_id' column to 'storylines' table...")
        cursor.execute("ALTER TABLE storylines ADD COLUMN series_id TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_storylines_series_id ON storylines (series_id)")
    
    if 'series_title' not in columns:
        print("Adding 'series_title' column to 'storylines' table...")
        cursor.execute("ALTER TABLE storylines ADD COLUMN series_title TEXT")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
