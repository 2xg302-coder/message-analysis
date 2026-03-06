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
    from models_orm import CalendarEvent, Storyline
    from services.llm_service import llm_service
    from prompts.storyline_prompt import STORYLINE_SYSTEM_PROMPT, STORYLINE_USER_PROMPT_TEMPLATE
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.database_orm import engine
    from models_orm import CalendarEvent, Storyline
    from services.llm_service import llm_service
    from prompts.storyline_prompt import STORYLINE_SYSTEM_PROMPT, STORYLINE_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class StorylineGenerator:
    def __init__(self):
        pass

    async def _get_session(self) -> AsyncSession:
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        return async_session()

    async def generate_daily_storylines(self, date: str) -> List[Storyline]:
        """
        Generates storylines for a given date based on calendar events.
        """
        logger.info(f"Starting storyline generation for {date}")
        
        session = await self._get_session()
        try:
            # 1. Fetch calendar events
            events = await self._get_calendar_events(session, date)
            if not events:
                logger.warning(f"No calendar events found for {date} (importance >= 2)")
                return []

            # 2. Fetch recent storylines (history)
            history_data_str = await self._get_history_context(session, date)

            # 3. Format prompt
            calendar_data_str = self._format_events(events)
            prompt = STORYLINE_USER_PROMPT_TEMPLATE.format(
                calendar_data=calendar_data_str,
                history_data=history_data_str
            )

            # 4. Call LLM
            logger.info(f"Generating storylines for {date} with {len(events)} events using model: {llm_service.model}...")
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

            # 5. Save to DB
            storylines = []
            
            # Clear old ones for the same date
            statement = select(Storyline).where(Storyline.date == date)
            existing_result = await session.execute(statement)
            existing = existing_result.scalars().all()
            for e in existing:
                await session.delete(e)
            
            for item in storylines_data:
                # Handle keywords list or string
                keywords = item.get("keywords", [])
                if isinstance(keywords, list):
                    keywords_str = json.dumps(keywords, ensure_ascii=False)
                else:
                    keywords_str = str(keywords)

                # Handle related events
                related_indices = item.get("related_event_indices", [])
                related_event_ids = []
                for idx in related_indices:
                    if isinstance(idx, int) and 0 <= idx < len(events):
                        if events[idx].id:
                            related_event_ids.append(events[idx].id)
                related_event_ids_str = json.dumps(related_event_ids)

                # Handle Series Logic
                parent_id = item.get("parent_id")
                series_id = None
                series_title = item.get("title") # Default series title

                if parent_id:
                    # Try to find parent
                    try:
                        # parent_id might be int, ensure type compatibility
                        parent_id_int = int(parent_id)
                        # Use select statement instead of session.get() for async session compatibility if needed, though get should work
                        # parent_storyline = await session.get(Storyline, parent_id_int)
                        stmt = select(Storyline).where(Storyline.id == parent_id_int)
                        result = await session.execute(stmt)
                        parent_storyline = result.scalar_one_or_none()
                        
                        if parent_storyline:
                            if parent_storyline.series_id:
                                series_id = parent_storyline.series_id
                                series_title = parent_storyline.series_title or parent_storyline.title
                            else:
                                # Parent has no series_id (legacy), generate one for it
                                new_series_id = uuid.uuid4().hex
                                parent_storyline.series_id = new_series_id
                                parent_storyline.series_title = parent_storyline.title
                                session.add(parent_storyline)
                                series_id = new_series_id
                                series_title = parent_storyline.title
                    except (ValueError, TypeError, Exception) as e:
                        logger.warning(f"Invalid parent_id processing: {parent_id}, error: {e}")
                
                if not series_id:
                    # New series
                    series_id = uuid.uuid4().hex

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
                    related_event_ids=related_event_ids_str
                )
                session.add(storyline)
                storylines.append(storyline)
            
            await session.commit()
            # Refresh to get IDs
            for s in storylines:
                await session.refresh(s)
            
            logger.info(f"Successfully generated {len(storylines)} storylines for {date}")
            return storylines

        except Exception as e:
            logger.error(f"Error generating storylines: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return []
        finally:
            await session.close()

    async def _get_calendar_events(self, session: AsyncSession, date: str) -> List[CalendarEvent]:
        # Filter importance >= 2
        statement = select(CalendarEvent).where(CalendarEvent.date == date).where(CalendarEvent.importance >= 2)
        result = await session.execute(statement)
        return result.scalars().all()

    def _format_events(self, events: List[CalendarEvent]) -> str:
        lines = []
        for i, e in enumerate(events):
            line = f"[{i}] {e.time} [{e.country}] {e.event} (重要性: {e.importance})"
            if e.consensus:
                line += f" 预期:{e.consensus}"
            if e.previous:
                line += f" 前值:{e.previous}"
            lines.append(line)
        return "\n".join(lines)

    async def _get_history_context(self, session: AsyncSession, current_date_str: str) -> str:
        """
        Get active storylines from previous 7 days
        """
        try:
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
            start_date = current_date - timedelta(days=7)
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            # Select active storylines in range [start_date, current_date)
            # Use < current_date to exclude today's (if any exist/re-generating)
            statement = select(Storyline).where(
                Storyline.date >= start_date_str,
                Storyline.date < current_date_str,
                Storyline.status == "active"
            ).order_by(Storyline.date.desc())
            
            result = await session.execute(statement)
            storylines = result.scalars().all()
            
            if not storylines:
                return "无近期历史主线。"
            
            lines = []
            for s in storylines:
                lines.append(f"- ID: {s.id} | 日期: {s.date} | 标题: {s.title} | 描述: {s.description[:50]}...")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error getting history context: {e}")
            return "无法获取历史数据。"

storyline_generator = StorylineGenerator()
