from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import logging

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

            # 2. Format prompt
            calendar_data_str = self._format_events(events)
            prompt = STORYLINE_USER_PROMPT_TEMPLATE.format(calendar_data=calendar_data_str)

            # 3. Call LLM
            logger.info(f"Generating storylines for {date} with {len(events)} events...")
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

            # 4. Save to DB
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

                storyline = Storyline(
                    date=date,
                    title=item.get("title", "No Title"),
                    description=item.get("description", ""),
                    keywords=keywords_str,
                    importance=item.get("importance", 3),
                    expected_impact=item.get("expected_impact", ""),
                    status="active"
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
        for e in events:
            line = f"- {e.time} [{e.country}] {e.event} (重要性: {e.importance})"
            if e.consensus:
                line += f" 预期:{e.consensus}"
            if e.previous:
                line += f" 前值:{e.previous}"
            lines.append(line)
        return "\n".join(lines)

storyline_generator = StorylineGenerator()
