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

    class Config:
        orm_mode = True

@router.get("/", response_model=List[StorylineResponse])
async def get_storylines(date: str = Query(..., description="Date to fetch storylines for (YYYY-MM-DD)")):
    manager = StorylineManager()
    storylines = await manager.get_storylines_by_date(date)
    
    response = []
    for sl in storylines:
        response.append(StorylineResponse(
            id=sl['id'],
            date=sl['date'],
            title=sl['title'],
            keywords=sl['keywords'],
            description=sl.get('description'),
            importance=sl['importance'],
            expected_impact=sl.get('expected_impact'),
            status=sl['status'],
            created_at=sl['created_at'],
            updated_at=sl.get('updated_at') or sl['created_at']
        ))
    return response

@router.post("/", response_model=StorylineResponse)
async def create_storyline(storyline: StorylineCreate):
    manager = StorylineManager()
    sl = await manager.create_storyline(storyline.dict())
    if not sl:
        raise HTTPException(status_code=500, detail="Failed to create storyline")
    return StorylineResponse(
        id=sl['id'],
        date=sl['date'],
        title=sl['title'],
        keywords=sl['keywords'],
        description=sl.get('description'),
        importance=sl['importance'],
        expected_impact=sl.get('expected_impact'),
        status=sl['status'],
        created_at=sl['created_at'],
        updated_at=sl.get('updated_at') or sl['created_at']
    )

@router.get("/active", response_model=List[StorylineResponse])
async def get_active_storylines():
    manager = StorylineManager()
    storylines = await manager.get_active_storylines()
    
    # Process dictionaries into Pydantic models
    response = []
    for sl in storylines:
        # sl is a dict from manager._process_result
        response.append(StorylineResponse(
            id=sl['id'],
            date=sl['date'],
            title=sl['title'],
            keywords=sl['keywords'],
            description=sl.get('description'),
            importance=sl['importance'],
            expected_impact=sl.get('expected_impact'),
            status=sl['status'],
            created_at=sl['created_at'],
            updated_at=sl.get('updated_at') or sl['created_at']
        ))
    return response

@router.get("/history", response_model=List[StorylineResponse])
async def get_history_storylines(limit: int = 50, offset: int = 0):
    manager = StorylineManager()
    storylines = await manager.get_history_storylines(limit, offset)
    
    response = []
    for sl in storylines:
        response.append(StorylineResponse(
            id=sl['id'],
            date=sl['date'],
            title=sl['title'],
            keywords=sl['keywords'],
            description=sl.get('description'),
            importance=sl['importance'],
            expected_impact=sl.get('expected_impact'),
            status=sl['status'],
            created_at=sl['created_at'],
            updated_at=sl.get('updated_at') or sl['created_at']
        ))
    return response

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
            updated_at=sl.updated_at or sl.created_at
        ))
    return response_list
