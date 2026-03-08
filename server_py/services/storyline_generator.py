from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json
import logging
import uuid

# Ensure imports work when running from server_py root
try:
    from core.database_orm import engine
    from models_orm import CalendarEvent, Storyline, Series
    from services.llm_service import llm_service
    from prompts.storyline_prompt import STORYLINE_SYSTEM_PROMPT, STORYLINE_USER_PROMPT_TEMPLATE, SERIES_SUMMARY_UPDATE_PROMPT
    from services.news_service import news_service
    from services.storyline_manager import StorylineManager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.database_orm import engine
    from models_orm import CalendarEvent, Storyline, Series
    from services.llm_service import llm_service
    from prompts.storyline_prompt import STORYLINE_SYSTEM_PROMPT, STORYLINE_USER_PROMPT_TEMPLATE, SERIES_SUMMARY_UPDATE_PROMPT
    from services.news_service import news_service
    from services.storyline_manager import StorylineManager

logger = logging.getLogger(__name__)

class StorylineGenerator:
    def __init__(self):
        self.manager = StorylineManager()

    async def _get_session(self) -> AsyncSession:
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        return async_session()

    async def generate_daily_storylines(self, date: str) -> List[Storyline]:
        """
        Generates storylines for a given date based on calendar events AND news.
        Uses Series-based classification.
        """
        logger.info(f"Starting storyline generation for {date}")
        
        # Ensure seed series exist
        await self.manager.ensure_seed_series()
        
        session = await self._get_session()
        try:
            # 1. Fetch calendar events
            events = await self._get_calendar_events(session, date)
            
            # 2. Fetch High-Impact News
            news_items = await self._get_daily_news(date)
            
            if not events and not news_items:
                logger.warning(f"No calendar events or news found for {date}")
                return []

            # 3. Fetch Active Series
            active_series = await self.manager.get_all_series(status='active')
            
            # 4. Format prompt
            calendar_data_str = self._format_events(events)
            news_data_str = self._format_news(news_items)
            series_data_str = self._format_series(active_series)
            
            prompt = STORYLINE_USER_PROMPT_TEMPLATE.format(
                calendar_data=calendar_data_str,
                news_data=news_data_str,
                series_data=series_data_str
            )

            # 5. Call LLM
            logger.info(f"Generating storylines for {date} with {len(events)} events and {len(news_items)} news items...")
            result = await llm_service.chat_completion(
                prompt=prompt,
                system_prompt=STORYLINE_SYSTEM_PROMPT,
                json_mode=True
            )
            
            # Result should be a dict or json string parsed by llm_service
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    logger.error(f"Error parsing JSON result: {result}")
                    return []
            
            storylines_data = result.get("storylines", [])
            if not storylines_data:
                logger.warning("No storylines found in LLM response")
                return []

            # 6. Save to DB
            storylines = []
            
            # Clear old ones for the same date (Re-generation strategy)
            # Be careful: This deletes existing storylines for the day.
            statement = select(Storyline).where(Storyline.date == date)
            existing_result = await session.execute(statement)
            existing = existing_result.scalars().all()
            for e in existing:
                await session.delete(e)
            
            for item in storylines_data:
                # Handle keywords
                keywords = item.get("keywords", [])
                if isinstance(keywords, list):
                    keywords_str = json.dumps(keywords, ensure_ascii=False)
                else:
                    keywords_str = str(keywords)

                # Handle Related Calendar Events
                related_cal_indices = item.get("related_calendar_indices", [])
                related_cal_ids = []
                for idx in related_cal_indices:
                    if isinstance(idx, int) and 0 <= idx < len(events):
                        if events[idx].id:
                            related_cal_ids.append(events[idx].id)
                related_event_ids_str = json.dumps(related_cal_ids)

                # Handle Related News
                related_news_indices = item.get("related_news_indices", [])
                related_news_ids = []
                for idx in related_news_indices:
                    if isinstance(idx, int) and 0 <= idx < len(news_items):
                        if 'id' in news_items[idx]:
                            related_news_ids.append(news_items[idx]['id'])
                related_news_ids_str = json.dumps(related_news_ids)

                # Handle Series Logic
                series_id = item.get("series_id")
                series_title = None
                
                # Check new series proposal
                new_proposal = item.get("new_series_proposal")
                
                if series_id:
                    # Validate series_id exists
                    series_check = await session.get(Series, series_id)
                    if series_check:
                        series_title = series_check.title
                        # Update series timestamp
                        series_check.updated_at = datetime.now().isoformat()
                        session.add(series_check)
                    else:
                        logger.warning(f"LLM returned invalid series_id: {series_id}")
                        series_id = None # Fallback

                if not series_id and new_proposal:
                    # Create new series
                    try:
                        new_series = Series(
                            id=uuid.uuid4().hex, # or slugify title
                            title=new_proposal.get("title", "New Series"),
                            description=new_proposal.get("description", ""),
                            category=new_proposal.get("category", "general"),
                            keywords=json.dumps([], ensure_ascii=False),
                            status="active"
                        )
                        session.add(new_series)
                        await session.flush() # Get ID? No, we set it.
                        series_id = new_series.id
                        series_title = new_series.title
                        logger.info(f"Created new series: {series_title}")
                    except Exception as e:
                        logger.error(f"Error creating new series: {e}")

                storyline = Storyline(
                    date=date,
                    title=item.get("title", "No Title"),
                    description=item.get("description", ""),
                    keywords=keywords_str,
                    importance=item.get("importance", 3),
                    expected_impact=item.get("expected_impact", ""),
                    status="active",
                    series_id=series_id,
                    series_title=series_title,
                    related_event_ids=related_event_ids_str,
                    related_news_ids=related_news_ids_str
                )
                session.add(storyline)
                storylines.append(storyline)
            
            await session.commit()
            # Refresh to get IDs
            for s in storylines:
                await session.refresh(s)
            
            logger.info(f"Successfully generated {len(storylines)} storylines for {date}")
            
            # 7. Update Series Summaries (Prior Knowledge)
            await self.update_series_summaries(storylines)
            
            return storylines

        except Exception as e:
            logger.error(f"Error generating storylines: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return []
        finally:
            await session.close()

    async def update_series_summaries(self, storylines: List[Storyline]):
        """
        Updates the current_summary of related series based on new storylines.
        This is the core of "Prior Knowledge Management".
        """
        if not storylines:
            return

        # Group storylines by series_id
        series_updates = {} 
        for sl in storylines:
            if sl.series_id:
                if sl.series_id not in series_updates:
                    series_updates[sl.series_id] = []
                series_updates[sl.series_id].append(sl)
        
        if not series_updates:
            return

        logger.info(f"Updating summaries for {len(series_updates)} series...")
        
        session = await self._get_session()
        try:
            for series_id, sl_list in series_updates.items():
                try:
                    # Re-fetch series to ensure it's attached to this session
                    series = await session.get(Series, series_id)
                    if not series:
                        continue
                    
                    # Combine descriptions if multiple storylines for one series
                    sl_descriptions = [f"- {s.description}" for s in sl_list]
                    combined_desc = "\n".join(sl_descriptions)
                    
                    current_summary = series.current_summary or "暂无摘要"
                    date = sl_list[0].date
                    
                    prompt = SERIES_SUMMARY_UPDATE_PROMPT.format(
                        series_title=series.title,
                        current_summary=current_summary,
                        new_storyline_description=combined_desc,
                        date=date
                    )
                    
                    # Call LLM
                    new_summary = await llm_service.chat_completion(
                        prompt=prompt,
                        system_prompt="You are a concise financial editor.",
                        json_mode=False
                    )
                    
                    if new_summary and isinstance(new_summary, str):
                        series.current_summary = new_summary.strip()
                        series.updated_at = datetime.now().isoformat()
                        session.add(series)
                        logger.info(f"Updated summary for series: {series.title}")
                except Exception as e:
                    logger.error(f"Error processing series {series_id}: {e}")
                    # Continue to next series even if one fails
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error updating series summaries transaction: {e}")
            await session.rollback()
        finally:
            await session.close()

    async def _get_calendar_events(self, session: AsyncSession, date: str) -> List[CalendarEvent]:
        # Filter importance >= 2
        statement = select(CalendarEvent).where(CalendarEvent.date == date).where(CalendarEvent.importance >= 2)
        result = await session.execute(statement)
        return result.scalars().all()
    
    async def _get_daily_news(self, date: str) -> List[Dict[str, Any]]:
        """Fetch important news for the day to supplement calendar events"""
        try:
            # We want news from [date 00:00:00] to [date 23:59:59]
            # Since news_service uses 'created_at' or 'time', let's rely on 'created_at' for now as it is indexed/used in get_news
            # But wait, 'created_at' is when it was inserted. 'time' is event time. 
            # Ideally we use 'time' but format varies. Let's use start_date/end_date in get_news which filters on created_at.
            # Assuming scraper runs daily.
            
            # Fetch more and filter? 
            # Let's fetch top 50 news with impact >= 2 or just general news if impact not set.
            # Note: impact_score might be 0 if not analyzed yet.
            # We should probably fetch unanalyzed news too if we want real-time. 
            # But StorylineGenerator is likely run after some initial ingestion.
            
            news = await news_service.get_news(limit=50, start_date=date, end_date=date)
            
            # Filter out non-finance sources (e.g., ITHome) to keep storylines focused
            news = [n for n in news if n.get('source') != 'ITHome']
            
            # Simple deduplication based on title similarity could be done here if needed
            # For now, just return
            return news
        except Exception as e:
            logger.error(f"Error fetching daily news: {e}")
            return []

    def _format_events(self, events: List[CalendarEvent]) -> str:
        if not events:
            return "无重要财经日历事件。"
        lines = []
        for i, e in enumerate(events):
            line = f"[{i}] {e.time} [{e.country}] {e.event} (重要性: {e.importance})"
            if e.consensus:
                line += f" 预期:{e.consensus}"
            if e.previous:
                line += f" 前值:{e.previous}"
            lines.append(line)
        return "\n".join(lines)

    def _format_news(self, news_items: List[Dict[str, Any]]) -> str:
        if not news_items:
            return "无重要新闻快讯。"
        lines = []
        for i, item in enumerate(news_items):
            # Limit content length
            content = item.get('content', '')[:100].replace('\n', ' ')
            source = item.get('source', 'Unknown')
            line = f"[{i}] 【{source}】{content}..."
            lines.append(line)
        return "\n".join(lines)

    def _format_series(self, series_list: List[Dict[str, Any]]) -> str:
        if not series_list:
            return "当前无活跃主题。"
        lines = []
        for s in series_list:
            desc = s.get('description', '')[:50]
            summary = s.get('current_summary', '')
            if not summary:
                summary = "暂无最新进展摘要。"
            else:
                summary = summary[:100] + "..." if len(summary) > 100 else summary
                
            lines.append(f"- ID: {s['id']} | 标题: {s['title']} | 类别: {s['category']} | 描述: {desc}... | 当前进展: {summary}")
        return "\n".join(lines)

storyline_generator = StorylineGenerator()
