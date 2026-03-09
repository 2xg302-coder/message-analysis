from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from collections import Counter

from sqlmodel import select, func, col, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from models_orm import News, Storyline, Series
from core.database_orm import engine

class DailyReportService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return async_session()

    async def generate_report(self, target_date: str) -> Dict[str, Any]:
        """
        Generate a daily report for the specified date (YYYY-MM-DD).
        """
        session = await self._get_session()
        try:
            # Define time range for the target date
            start_time = f"{target_date}T00:00:00"
            end_time = f"{target_date}T23:59:59.999999"

            # 1. Collection & Analysis Stats
            collection_stats = await self._get_collection_stats(session, start_time, end_time)

            # 2. Hotspots (Top News & Tags)
            hotspots = await self._get_hotspots(session, start_time, end_time)

            # 3. Series Updates (Storylines)
            series_updates = await self._get_series_updates(session, target_date)

            return {
                "date": target_date,
                "generated_at": datetime.now().isoformat(),
                "collection_stats": collection_stats,
                "hotspots": hotspots,
                "series_updates": series_updates
            }
        finally:
            # Only close if we created it
            if not self.session:
                await session.close()

    async def _get_collection_stats(self, session: AsyncSession, start_time: str, end_time: str) -> Dict[str, Any]:
        # Base filter
        date_filter = and_(News.created_at >= start_time, News.created_at <= end_time)

        # Total Count
        stmt_total = select(func.count(News.id)).where(date_filter)
        total = (await session.execute(stmt_total)).scalar() or 0

        # Analyzed Count
        stmt_analyzed = select(func.count(News.id)).where(date_filter, News.analysis.is_not(None))
        analyzed = (await session.execute(stmt_analyzed)).scalar() or 0

        # Source Distribution
        stmt_source = select(News.source, func.count(News.id)).where(date_filter).group_by(News.source)
        source_res = await session.execute(stmt_source)
        sources = {row[0]: row[1] for row in source_res.all()}

        # Sentiment Distribution
        # SQLModel/SQLAlchemy CASE syntax
        stmt_sentiment = select(
            func.sum(case((News.sentiment_score > 0.05, 1), else_=0)).label("positive"),
            func.sum(case((News.sentiment_score < -0.05, 1), else_=0)).label("negative"),
            func.sum(case((and_(News.sentiment_score >= -0.05, News.sentiment_score <= 0.05), 1), else_=0)).label("neutral")
        ).where(date_filter)

        sent_res = (await session.execute(stmt_sentiment)).one()
        sentiment = {
            "positive": sent_res.positive or 0,
            "negative": sent_res.negative or 0,
            "neutral": sent_res.neutral or 0
        }

        return {
            "total_news": total,
            "analyzed_count": analyzed,
            "pending_count": total - analyzed,
            "sources": sources,
            "sentiment": sentiment
        }

    async def _get_hotspots(self, session: AsyncSession, start_time: str, end_time: str) -> Dict[str, Any]:
        # Top News by Impact Score
        stmt_top = select(News).where(
            News.created_at >= start_time,
            News.created_at <= end_time
        ).order_by(News.impact_score.desc()).limit(5)
        
        top_news_res = await session.execute(stmt_top)
        top_news_list = []
        for news in top_news_res.scalars().all():
            top_news_list.append({
                "id": news.id,
                "title": news.title,
                "source": news.source,
                "impact_score": news.impact_score,
                "created_at": news.created_at,
                "summary": self._extract_summary(news)
            })

        # Hot Tags
        # Use simple string search or JSON parsing if DB supports it. 
        # Here we fetch tags and count in python for simplicity and compatibility
        stmt_tags = select(News.tags).where(
            News.created_at >= start_time,
            News.created_at <= end_time,
            News.tags.is_not(None)
        ).limit(2000) # Limit to avoid OOM
        
        tag_res = await session.execute(stmt_tags)
        
        tag_counts = Counter()
        for tags_json in tag_res.scalars().all():
            try:
                tags = json.loads(tags_json)
                if isinstance(tags, list):
                    tag_counts.update(tags)
            except: pass
            
        hot_tags = [{"name": name, "count": count} for name, count in tag_counts.most_common(10)]

        return {
            "top_news": top_news_list,
            "hot_tags": hot_tags
        }

    async def _get_series_updates(self, session: AsyncSession, target_date: str) -> List[Dict[str, Any]]:
        # Query Storylines for the target date
        # Left Join with Series to get Series info
        stmt = select(Storyline, Series).outerjoin(Series, Storyline.series_id == Series.id).where(
            Storyline.date == target_date
        )
        
        res = await session.execute(stmt)
        updates = []
        for storyline, series in res.all():
            updates.append({
                "storyline_id": storyline.id,
                "storyline_title": storyline.title,
                "storyline_description": storyline.description,
                "importance": storyline.importance,
                "series_id": storyline.series_id,
                "series_title": series.title if series else storyline.series_title or "Unknown Series",
                "series_category": series.category if series else "general"
            })
            
        return updates

    def _extract_summary(self, news: News) -> str:
        # Try to get summary from analysis, fallback to content snippet
        if news.analysis:
            try:
                analysis = json.loads(news.analysis)
                if isinstance(analysis, dict) and 'summary' in analysis:
                    return analysis['summary']
            except: pass
        
        return (news.content[:100] + "...") if news.content else ""
