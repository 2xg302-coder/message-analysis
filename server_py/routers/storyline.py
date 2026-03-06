from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from services.storyline_manager import StorylineManager
from services.storyline_generator import storyline_generator
import json

router = APIRouter(prefix="/api/storylines", tags=["storylines"])

class StorylineCreate(BaseModel):
    date: str
    title: str
    keywords: List[str] = []
    description: Optional[str] = None
    importance: int = 3
    status: str = "active"
    series_id: Optional[str] = None
    series_title: Optional[str] = None
    related_event_ids: List[int] = []

class StorylineResponse(BaseModel):
    id: int
    date: str
    title: str
    keywords: List[str]
    description: Optional[str] = None
    importance: int
    expected_impact: Optional[str] = None
    status: str
    created_at: str
    updated_at: str
    series_id: Optional[str] = None
    series_title: Optional[str] = None
    related_event_ids: List[int] = []

    class Config:
        orm_mode = True

@router.get("/", response_model=List[StorylineResponse])
async def get_storylines(date: str = Query(..., description="Date to fetch storylines for (YYYY-MM-DD)")):
    manager = StorylineManager()
    storylines = await manager.get_storylines_by_date(date)
    # storylines are dicts processed by manager
    return [StorylineResponse(**sl) for sl in storylines]

@router.post("/", response_model=StorylineResponse)
async def create_storyline(storyline: StorylineCreate):
    manager = StorylineManager()
    sl = await manager.create_storyline(storyline.dict())
    if not sl:
        raise HTTPException(status_code=500, detail="Failed to create storyline")
    return StorylineResponse(**sl)

@router.get("/active", response_model=List[StorylineResponse])
async def get_active_storylines():
    manager = StorylineManager()
    storylines = await manager.get_active_storylines()
    return [StorylineResponse(**sl) for sl in storylines]

@router.get("/history", response_model=List[StorylineResponse])
async def get_history_storylines(limit: int = 50, offset: int = 0):
    manager = StorylineManager()
    storylines = await manager.get_history_storylines(limit, offset)
    return [StorylineResponse(**sl) for sl in storylines]

@router.get("/series/{series_id}", response_model=List[StorylineResponse])
async def get_storyline_series(series_id: str):
    manager = StorylineManager()
    storylines = await manager.get_storyline_series(series_id)
    return [StorylineResponse(**sl) for sl in storylines]

@router.put("/{id}/archive")
async def archive_storyline(id: int):
    manager = StorylineManager()
    success = await manager.archive_single_storyline(id)
    if not success:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return {"message": "Storyline archived"}

@router.put("/archive-all")
async def archive_all_storylines(date: str = Query(..., description="Archive active storylines on or before this date")):
    manager = StorylineManager()
    count = await manager.archive_storylines(date)
    return {"message": f"Archived {count} storylines"}

@router.post("/generate", response_model=List[StorylineResponse])
async def generate_storylines(date: str):
    """
    Generate storylines for a specific date using LLM based on Calendar Events.
    This will replace any existing storylines for that date.
    """
    result = await storyline_generator.generate_daily_storylines(date)
    
    response_list = []
    for sl in result:
        # Parse keywords from JSON string if needed
        keywords = []
        if sl.keywords:
            try:
                if isinstance(sl.keywords, str):
                    keywords = json.loads(sl.keywords)
                elif isinstance(sl.keywords, list):
                    keywords = sl.keywords
            except:
                keywords = []
        
        related_event_ids = []
        if sl.related_event_ids:
            try:
                if isinstance(sl.related_event_ids, str):
                    related_event_ids = json.loads(sl.related_event_ids)
                elif isinstance(sl.related_event_ids, list):
                    related_event_ids = sl.related_event_ids
            except:
                related_event_ids = []
                
        response_list.append(StorylineResponse(
            id=sl.id,
            date=sl.date,
            title=sl.title,
            keywords=keywords,
            description=sl.description,
            importance=sl.importance,
            expected_impact=sl.expected_impact,
            status=sl.status or "active",
            created_at=sl.created_at,
            updated_at=sl.updated_at or sl.created_at,
            series_id=sl.series_id,
            series_title=sl.series_title,
            related_event_ids=related_event_ids
        ))
    return response_list
