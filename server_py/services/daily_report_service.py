from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from collections import Counter

from sqlmodel import select, func, col, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from models_orm import News, Storyline, Series, DailyReport
from core.database_orm import engine
from llm_service import call_llm
import asyncio

class DailyReportService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return async_session()

    async def get_available_dates(self, limit: int = 30) -> List[str]:
        """Get list of available report dates"""
        session = await self._get_session()
        try:
            stmt = select(DailyReport.date).order_by(DailyReport.date.desc()).limit(limit)
            return (await session.execute(stmt)).scalars().all()
        finally:
            if not self.session:
                await session.close()

    async def get_report_snapshot(self, target_date: str) -> Optional[Dict[str, Any]]:
        """Get persisted report from DB"""
        session = await self._get_session()
        try:
            stmt = select(DailyReport).where(DailyReport.date == target_date)
            result = (await session.execute(stmt)).scalar_one_or_none()
            if result:
                return json.loads(result.content)
            return None
        finally:
            if not self.session:
                await session.close()

    async def save_report_snapshot(self, target_date: str, data: Dict[str, Any]):
        """Save report to DB"""
        session = await self._get_session()
        try:
            stmt = select(DailyReport).where(DailyReport.date == target_date)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            
            content_json = json.dumps(data, ensure_ascii=False)
            
            if existing:
                existing.content = content_json
                existing.updated_at = datetime.now().isoformat()
            else:
                new_report = DailyReport(date=target_date, content=content_json)
                session.add(new_report)
            
            await session.commit()
        finally:
            if not self.session:
                await session.close()

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

            # 4. High Value Info (LLM Summary)
            high_value_info = await self._get_high_value_info(hotspots.get('top_news', []))

            # 5. Hotspot Changes (Diff with yesterday)
            hotspot_changes = await self._get_hotspot_changes(session, hotspots, target_date)

            report_data = {
                "date": target_date,
                "generated_at": datetime.now().isoformat(),
                "collection_stats": collection_stats,
                "hotspots": hotspots,
                "series_updates": series_updates,
                "high_value_info": high_value_info,
                "hotspot_changes": hotspot_changes
            }
            
            # Persist the report
            # We use a separate session or the same one. Since we are inside generate_report which uses session,
            # we should be careful about transaction.
            # But save_report_snapshot uses its own session management (opens/closes if not provided).
            # Since self.session is shared if provided, we should be fine.
            # However, `save_report_snapshot` creates a NEW session if self.session is None.
            # If self.session is NOT None, it reuses it.
            # But here `session` is local if self.session is None.
            # So calling `self.save_report_snapshot` might fail if it tries to close the session we are using.
            
            # Let's just do the saving here directly or use a helper that doesn't manage session if provided.
            # Actually, let's just use the `session` we have.
            
            stmt = select(DailyReport).where(DailyReport.date == target_date)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            content_json = json.dumps(report_data, ensure_ascii=False)
            
            if existing:
                existing.content = content_json
                existing.updated_at = datetime.now().isoformat()
            else:
                new_report = DailyReport(date=target_date, content=content_json)
                session.add(new_report)
            
            await session.commit()

            return report_data
        finally:
            # Only close if we created it
            if not self.session:
                await session.close()

    async def _get_high_value_info(self, top_news: List[Dict]) -> str:
        if not top_news:
            return "今日暂无高价值新闻。"
        
        prompt = "请基于以下今日高价值新闻，生成一份简报，重点概述关键事件、核心观点及其潜在影响（100-200字）。请务必以 JSON 格式返回，字段名为 'summary'：\n\n"
        for i, news in enumerate(top_news):
            prompt += f"{i+1}. {news['title']} (Impact: {news['impact_score']})\n摘要: {news['summary']}\n\n"
        
        try:
            # Call LLM
            messages = [{"role": "user", "content": prompt}]
            response = await call_llm(messages, use_fast_model=False)
            if isinstance(response, dict) and 'summary' in response:
                return response['summary']
            if isinstance(response, dict):
                return json.dumps(response, ensure_ascii=False)
            return str(response)
        except Exception as e:
            return f"生成简报失败: {str(e)}"

    async def _get_hotspot_changes(self, session: AsyncSession, current_hotspots: Dict, target_date: str) -> Dict[str, Any]:
        try:
            # Calculate yesterday date
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            prev_date = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            
            stmt = select(DailyReport).where(DailyReport.date == prev_date)
            prev_report_row = (await session.execute(stmt)).scalar_one_or_none()
            
            changes = {"new_tags": [], "surging_tags": []}
            
            if prev_report_row:
                try:
                    prev_data = json.loads(prev_report_row.content)
                    prev_tags_list = prev_data.get('hotspots', {}).get('hot_tags', [])
                    prev_tags = {t['name']: t['count'] for t in prev_tags_list}
                    
                    curr_tags_list = current_hotspots.get('hot_tags', [])
                    curr_tags = {t['name']: t['count'] for t in curr_tags_list}
                    
                    # 1. New Tags (in top 10 today but not in top 10 yesterday)
                    # This is approximate since we only store top 10.
                    # Ideally we should compare against full list, but we only have report snapshot.
                    # So "New in Top 10" is a valid metric.
                    for t in curr_tags:
                        if t not in prev_tags:
                            changes["new_tags"].append(t)
                            
                    # 2. Surging Tags (Count increased significantly, e.g. > 50%)
                    for t, c in curr_tags.items():
                        if t in prev_tags:
                            prev_c = prev_tags[t]
                            if prev_c > 0 and (c - prev_c) / prev_c >= 0.5:
                                changes["surging_tags"].append(t)
                except Exception as e:
                    print(f"Error calculating hotspot changes: {e}")
                    
            return changes
        except Exception as e:
            print(f"Error in _get_hotspot_changes: {e}")
            return {}

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
