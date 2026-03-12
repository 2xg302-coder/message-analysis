from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from collections import Counter

from sqlmodel import select, func, col, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from models_orm import News, Storyline, Series, DailyReport, WeeklyReport
from core.database_orm import engine
from llm_service import call_llm
import asyncio

class WeeklyReportService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return async_session()

    async def get_available_weeks(self, limit: int = 30) -> List[Dict[str, str]]:
        """Get list of available report weeks"""
        session = await self._get_session()
        try:
            stmt = select(WeeklyReport.week_start, WeeklyReport.week_end).order_by(WeeklyReport.week_start.desc()).limit(limit)
            result = await session.execute(stmt)
            return [{"start": row[0], "end": row[1]} for row in result.all()]
        finally:
            if not self.session:
                await session.close()

    async def get_report_snapshot(self, week_start: str) -> Optional[Dict[str, Any]]:
        """Get persisted report from DB"""
        session = await self._get_session()
        try:
            stmt = select(WeeklyReport).where(WeeklyReport.week_start == week_start)
            result = (await session.execute(stmt)).scalar_one_or_none()
            if result:
                return json.loads(result.content)
            return None
        finally:
            if not self.session:
                await session.close()

    async def generate_report(self, week_start: str) -> Dict[str, Any]:
        """
        Generate a weekly report for the week starting from week_start (YYYY-MM-DD).
        """
        session = await self._get_session()
        try:
            start_dt = datetime.strptime(week_start, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=6)
            week_end = end_dt.strftime("%Y-%m-%d")

            # Define time range
            start_time = f"{week_start}T00:00:00"
            end_time = f"{week_end}T23:59:59.999999"

            # 1. Collection & Analysis Stats (Aggregate)
            # 2. Daily Trends (Collection count per day)
            # 3. Hotspots (Top News & Tags)
            # 4. Series Updates (Storylines)
            
            # Execute DB queries in parallel
            # Use a separate session for each query to avoid sharing session issues in asyncio.gather
            # Or use the same session but be careful. SQLAlchemy async session is not thread-safe but 
            # with asyncio within same thread context, concurrent execution on same session might be risky if not serialized.
            # Best practice: Each task gets its own short-lived session or run sequentially.
            # But we want speed. Let's try gathering them but we need to ensure they don't conflict on session usage.
            # Actually, SQLAlchemy AsyncSession is not safe for concurrent use.
            # We must use separate sessions for parallel execution.
            
            async def run_with_new_session(func, *args):
                local_session = await self._get_session()
                # If self.session was provided, we are reusing it, which is bad for parallel.
                # If self.session is None, _get_session creates a NEW one each time?
                # Wait, _get_session implementation:
                # if self.session: return self.session
                # else: create new
                
                # So if self.session is set, all tasks use same session -> Error!
                # If self.session is None, each call creates new session? No, we need to explicitly create new sessions.
                
                async with sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
                    return await func(s, *args)

            # Parallel execution with dedicated sessions
            collection_stats, daily_trends, hotspots, series_updates, high_value_info = await asyncio.gather(
                run_with_new_session(self._get_collection_stats, start_time, end_time),
                run_with_new_session(self._get_daily_trends, start_time, end_time),
                run_with_new_session(self._get_hotspots, start_time, end_time),
                run_with_new_session(self._get_series_updates, week_start, week_end),
                run_with_new_session(self._get_high_value_info, week_start, week_end)
            )

            report_data = {
                "week_start": week_start,
                "week_end": week_end,
                "generated_at": datetime.now().isoformat(),
                "collection_stats": collection_stats,
                "daily_trends": daily_trends,
                "hotspots": hotspots,
                "series_updates": series_updates,
                "high_value_info": high_value_info
            }
            
            # Persist the report
            stmt = select(WeeklyReport).where(WeeklyReport.week_start == week_start)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            content_json = json.dumps(report_data, ensure_ascii=False)
            
            if existing:
                existing.content = content_json
                existing.week_end = week_end
                existing.updated_at = datetime.now().isoformat()
            else:
                new_report = WeeklyReport(week_start=week_start, week_end=week_end, content=content_json)
                session.add(new_report)
            
            await session.commit()

            return report_data
        finally:
            if not self.session:
                await session.close()

    async def _get_collection_stats(self, session: AsyncSession, start_time: str, end_time: str) -> Dict[str, Any]:
        date_filter = and_(News.created_at >= start_time, News.created_at <= end_time)

        # Combined query for Total, Analyzed, Sentiment
        # Note: SQLite COUNT(CASE...) works well.
        stmt = select(
            func.count(News.id).label("total"),
            func.count(case((News.analysis.is_not(None), 1), else_=None)).label("analyzed"),
            func.sum(case((News.sentiment_score > 0.05, 1), else_=0)).label("positive"),
            func.sum(case((News.sentiment_score < -0.05, 1), else_=0)).label("negative"),
            func.sum(case((and_(News.sentiment_score >= -0.05, News.sentiment_score <= 0.05), 1), else_=0)).label("neutral")
        ).where(date_filter)

        res = (await session.execute(stmt)).one()
        total = res.total or 0
        analyzed = res.analyzed or 0
        sentiment = {
            "positive": res.positive or 0,
            "negative": res.negative or 0,
            "neutral": res.neutral or 0
        }

        # Source Distribution (still needs group by)
        stmt_source = select(News.source, func.count(News.id)).where(date_filter).group_by(News.source)
        source_res = await session.execute(stmt_source)
        sources = {row[0]: row[1] for row in source_res.all()}

        return {
            "total_news": total,
            "analyzed_count": analyzed,
            "sources": sources,
            "sentiment": sentiment
        }

    async def _get_daily_trends(self, session: AsyncSession, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        # SQLite substr for date extraction: substr(created_at, 1, 10) -> YYYY-MM-DD
        stmt = select(
            func.substr(News.created_at, 1, 10).label("date"), 
            func.count(News.id).label("count")
        ).where(
            and_(News.created_at >= start_time,
            News.created_at <= end_time)
        ).group_by("date").order_by("date")
        
        result = await session.execute(stmt)
        data = [{"date": row[0], "count": row[1]} for row in result.all()]
        return data

    async def _get_hotspots(self, session: AsyncSession, start_time: str, end_time: str) -> Dict[str, Any]:
        # Top News by Impact Score
        stmt_top = select(News).where(
            and_(News.created_at >= start_time,
            News.created_at <= end_time)
        ).order_by(News.impact_score.desc()).limit(10)
        
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
        stmt_tags = select(News.tags).where(
            and_(News.created_at >= start_time,
            News.created_at <= end_time,
            News.tags.is_not(None))
        ).limit(5000) 
        
        tag_res = await session.execute(stmt_tags)
        tag_counts = Counter()
        for tags_json in tag_res.scalars().all():
            try:
                tags = json.loads(tags_json)
                if isinstance(tags, list):
                    tag_counts.update(tags)
            except: pass
            
        hot_tags = [{"name": name, "count": count} for name, count in tag_counts.most_common(20)]

        return {
            "top_news": top_news_list,
            "hot_tags": hot_tags
        }

    async def _get_series_updates(self, session: AsyncSession, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        stmt = select(Storyline, Series).outerjoin(Series, Storyline.series_id == Series.id).where(
            and_(Storyline.date >= start_date,
            Storyline.date <= end_date,
            Storyline.importance >= 7)  # Only high importance updates for weekly report
        ).order_by(Storyline.date.desc())
        
        res = await session.execute(stmt)
        updates = []
        for storyline, series in res.all():
            updates.append({
                "date": storyline.date,
                "storyline_title": storyline.title,
                "importance": storyline.importance,
                "series_title": series.title if series else storyline.series_title or "Unknown Series"
            })
        return updates

    async def _get_high_value_info(self, session: AsyncSession, start_date: str, end_date: str) -> str:
        # Try to aggregate from Daily Reports first
        stmt = select(DailyReport).where(
            and_(DailyReport.date >= start_date,
            DailyReport.date <= end_date)
        ).order_by(DailyReport.date)
        
        daily_reports = (await session.execute(stmt)).scalars().all()
        
        daily_summaries = []
        for report in daily_reports:
            try:
                content = json.loads(report.content)
                summary = content.get('high_value_info')
                if summary:
                    # Clean up JSON string if it was stored as JSON string
                    if isinstance(summary, str) and summary.strip().startswith('{'):
                         try:
                             summary_json = json.loads(summary)
                             if 'summary' in summary_json:
                                 summary = summary_json['summary']
                         except: pass
                    
                    daily_summaries.append(f"【{report.date}】\n{summary}")
            except: pass
            
        if not daily_summaries:
            return "本周暂无高价值信息记录。"
            
        combined_text = "\n\n".join(daily_summaries)
        
        prompt = f"""
请根据以下过去一周每日的高价值信息简报，生成一份**周报总结**。
要求：
1. 提炼本周最核心的3-5个关键事件或趋势。
2. 分析这些事件的跨日联系（如有）。
3. 总结整体市场/舆论情绪走向。
4. 字数控制在 300-500 字。
5. 请务必以 JSON 格式返回，字段名为 'summary'。

每日简报内容：
{combined_text}
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await call_llm(messages, use_fast_model=False)
            if isinstance(response, dict) and 'summary' in response:
                return response['summary']
            if isinstance(response, dict):
                 # Fallback if key is different but still dict
                 return json.dumps(response, ensure_ascii=False)
            return str(response)
        except Exception as e:
            return f"生成周报总结失败: {str(e)}"

    def _extract_summary(self, news: News) -> str:
        if news.analysis:
            try:
                analysis = json.loads(news.analysis)
                if isinstance(analysis, dict) and 'summary' in analysis:
                    return analysis['summary']
            except: pass
        return (news.content[:100] + "...") if news.content else ""
