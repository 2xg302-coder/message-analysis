from typing import Optional, List, Dict
from datetime import datetime
from sqlmodel import Field, SQLModel, JSON
from sqlalchemy import Column, UniqueConstraint
import json

class NewsBase(SQLModel):
    id: str = Field(primary_key=True)
    title: str
    link: str
    content: str
    time: str
    timestamp: str
    scraped_at: str = Field(alias="scrapedAt")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: str
    type: str = Field(default="article")
    
    # JSON fields need special handling in SQLite
    # In SQLModel/SQLAlchemy, we can use sa_column=Column(JSON) but SQLite JSON support varies
    # For simplicity and compatibility, we store as string but add properties to access as dict/list
    # Or use Pydantic's validator to serialize/deserialize if we use this model for API too
    
    # Using sa_column with JSON type is the modern way if using SQLAlchemy > 1.4
    # But to be safe with existing text fields in DB, we might want to keep them as text for now
    # and use Pydantic to parse. However, let's try to map them to the existing schema.
    
    tags: str = Field(default="[]") 
    entities: str = Field(default="{}")
    triples: str = Field(default="[]")
    impact_score: int = Field(default=0)
    sentiment_score: float = Field(default=0.0)
    simhash: Optional[str] = None
    
    # New fields for analysis results
    analysis: Optional[str] = None
    analyzed_at: Optional[str] = None
    raw_data: Optional[str] = None

class News(NewsBase, table=True):
    __tablename__ = "news"

    class Config:
        arbitrary_types_allowed = True

class Watchlist(SQLModel, table=True):
    __tablename__ = "watchlist"
    keyword: str = Field(primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class CalendarEvent(SQLModel, table=True):
    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint("date", "time", "event", "country", name="uq_calendar_event"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str
    time: str
    country: str
    event: str
    importance: int
    previous: Optional[str] = None
    consensus: Optional[str] = None
    actual: Optional[str] = None

class Series(SQLModel, table=True):
    __tablename__ = "series"
    id: str = Field(primary_key=True)  # Using UUID or slug as ID
    title: str = Field(index=True)
    description: str
    category: str = Field(default="general")  # 'macro', 'geopolitics', 'industry', 'other'
    keywords: str = Field(default="[]")  # JSON list for initial matching
    status: str = Field(default="active")  # 'active', 'archived'
    current_summary: Optional[str] = None  # Dynamic summary of the series
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class Storyline(SQLModel, table=True):
    __tablename__ = "storylines"
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)
    title: str
    description: str
    keywords: str = Field(default="[]") # JSON list of strings
    series_id: Optional[str] = Field(default=None, index=True) # Linked to Series.id
    series_title: Optional[str] = Field(default=None)
    related_event_ids: str = Field(default="[]") # JSON list of Calendar IDs
    related_news_ids: str = Field(default="[]") # JSON list of News IDs
    importance: int
    expected_impact: str
    status: str = Field(default="active")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
