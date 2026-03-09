from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import settings

# Use aiosqlite for async support
DATABASE_URL = f"sqlite+aiosqlite:///{settings.DB_PATH}"

# Create Async Engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_source_config (
                source TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_created_at ON news(created_at DESC)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_impact_score ON news(impact_score)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_analysis ON news(analysis)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(date)"))

async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
