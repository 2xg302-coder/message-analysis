from services.news_service import NewsService, news_service
from services.daily_report_service import DailyReportService
from core.database import db

def get_news_service() -> NewsService:
    return news_service

def get_daily_report_service() -> DailyReportService:
    """Dependency provider for DailyReportService"""
    return DailyReportService()

def get_legacy_news_service() -> NewsService:
    """Legacy Dependency provider for NewsService (Direct SQL)"""
    return NewsService(db)
