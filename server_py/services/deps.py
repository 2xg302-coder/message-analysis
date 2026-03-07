from services.news_service import NewsService
from services.news_service_orm import NewsServiceORM
from core.database import db

def get_news_service() -> NewsServiceORM:
    """Dependency provider for NewsService"""
    # Return ORM version. 
    # Note: NewsServiceORM manages its own session if not provided, 
    # but ideally we should inject session here.
    return NewsServiceORM()

def get_legacy_news_service() -> NewsService:
    """Legacy Dependency provider for NewsService (Direct SQL)"""
    return NewsService(db)
