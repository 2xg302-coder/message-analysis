from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from models_orm import Storyline
from core.database_orm import engine

class StorylineManager:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return async_session()

    def _process_result(self, storyline: Storyline) -> Dict[str, Any]:
        item = storyline.dict()
        try:
            item['keywords'] = json.loads(item['keywords']) if item['keywords'] else []
        except Exception:
            item['keywords'] = []
            
        try:
            item['related_event_ids'] = json.loads(item['related_event_ids']) if item.get('related_event_ids') else []
        except Exception:
            item['related_event_ids'] = []
            
        return item

    async def get_storyline_series(self, series_id: str) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.series_id == series_id).order_by(Storyline.date.desc())
            result = await session.execute(stmt)
            storylines = result.scalars().all()
            return [self._process_result(sl) for sl in storylines]
        except Exception as e:
            print(f"Error getting storyline series: {e}")
            return []
        finally:
            if not self.session:
                await session.close()

    async def create_storyline(self, storyline_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session = await self._get_session()
        try:
            # Check for duplicate title on the same date
            stmt = select(Storyline).where(Storyline.title == storyline_data['title']).where(Storyline.date == storyline_data['date'])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return self._process_result(existing)

            storyline = Storyline(**storyline_data)
            if isinstance(storyline_data.get('keywords'), list):
                storyline.keywords = json.dumps(storyline_data['keywords'], ensure_ascii=False)
            
            # Ensure defaults
            if not storyline.created_at:
                storyline.created_at = datetime.now().isoformat()
            if not storyline.updated_at:
                storyline.updated_at = datetime.now().isoformat()
            
            session.add(storyline)
            await session.commit()
            await session.refresh(storyline)
            return self._process_result(storyline)
        except Exception as e:
            await session.rollback()
            return None
        finally:
            if not self.session:
                await session.close()

    async def activate_storyline(self, storyline_id: int) -> bool:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.id == storyline_id)
            result = await session.execute(stmt)
            storyline = result.scalar_one_or_none()
            if storyline:
                storyline.status = 'active'
                storyline.updated_at = datetime.now().isoformat()
                session.add(storyline)
                await session.commit()
                return True
            return False
        except Exception as e:
            await session.rollback()
            return False
        finally:
            if not self.session:
                await session.close()

    async def archive_storylines(self, date: Optional[str] = None) -> int:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.status == 'active')
            if date:
                stmt = stmt.where(Storyline.date <= date)
            
            result = await session.execute(stmt)
            storylines = result.scalars().all()
            
            count = 0
            for sl in storylines:
                sl.status = 'archived'
                sl.updated_at = datetime.now().isoformat()
                session.add(sl)
                count += 1
            
            if count > 0:
                await session.commit()
            return count
        except Exception as e:
            await session.rollback()
            return 0
        finally:
            if not self.session:
                await session.close()

    async def get_storylines_by_date(self, date: str) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.date == date).order_by(Storyline.importance.desc())
            result = await session.execute(stmt)
            storylines = result.scalars().all()
            return [self._process_result(sl) for sl in storylines]
        except Exception as e:
            print(f"Error getting storylines by date: {e}")
            return []
        finally:
            if not self.session:
                await session.close()

    async def get_active_storylines(self) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.status == 'active').order_by(Storyline.importance.desc())
            result = await session.execute(stmt)
            storylines = result.scalars().all()
            return [self._process_result(sl) for sl in storylines]
        except Exception as e:
            print(f"Error active storylines: {e}")
            return []
        finally:
            if not self.session:
                await session.close()

    async def get_history_storylines(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.status == 'archived').order_by(Storyline.date.desc(), Storyline.importance.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            storylines = result.scalars().all()
            return [self._process_result(sl) for sl in storylines]
        except Exception as e:
            print(f"Error history storylines: {e}")
            return []
        finally:
            if not self.session:
                await session.close()

    async def archive_single_storyline(self, storyline_id: int) -> bool:
        session = await self._get_session()
        try:
            stmt = select(Storyline).where(Storyline.id == storyline_id)
            result = await session.execute(stmt)
            storyline = result.scalar_one_or_none()
            if storyline:
                storyline.status = 'archived'
                storyline.updated_at = datetime.now().isoformat()
                session.add(storyline)
                await session.commit()
                return True
            return False
        except Exception as e:
            await session.rollback()
            return False
        finally:
            if not self.session:
                await session.close()
