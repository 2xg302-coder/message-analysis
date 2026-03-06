from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict
from pydantic import BaseModel
from services.storyline_manager import StorylineManager
from services.storyline_generator import storyline_generator
import json
import uuid
import asyncio
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/storylines", tags=["storylines"])

# --- Task Management ---
tasks: Dict[str, Dict] = {}

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str
    result: Optional[dict] = None

async def run_batch_generation(task_id: str, days: int):
    # This must be run in background
    tasks[task_id]['status'] = 'processing'
    tasks[task_id]['progress'] = 0
    tasks[task_id]['message'] = 'Initializing...'
    
    try:
        # We need to run async code inside background task.
        # But BackgroundTasks runs synchronous functions in threadpool, or async functions in event loop.
        # Since this is async function, it runs in loop.
        
        manager = StorylineManager()
        await manager.ensure_seed_series()
        
        today = datetime.now()
        
        for i in range(days):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            tasks[task_id]['message'] = f"正在生成 {date_str} ({i+1}/{days})..."
            tasks[task_id]['progress'] = int((i / days) * 100)
            
            # Generate
            await storyline_generator.generate_daily_storylines(date_str)
            
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['message'] = '全量刷新完成'
        tasks[task_id]['progress'] = 100
        
    except Exception as e:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['message'] = f"Error: {str(e)}"
        print(f"Batch generation failed: {e}")

@router.post("/batch-generate", response_model=TaskStatus)
async def start_batch_generation(days: int = Query(7, description="Number of days to look back"), background_tasks: BackgroundTasks = None):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'task_id': task_id,
        'status': 'pending',
        'progress': 0,
        'message': 'Task initialized',
        'result': None
    }
    
    background_tasks.add_task(run_batch_generation, task_id, days)
    
    return TaskStatus(**tasks[task_id])

@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatus(**tasks[task_id])

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
    related_news_ids: List[str] = []

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

@router.get("/series", response_model=List[dict])
async def get_all_series(status: str = "active"):
    manager = StorylineManager()
    # Ensure seed series exist when this endpoint is called, 
    # just in case migration/init didn't run or db was reset
    await manager.ensure_seed_series()
    
    series_list = await manager.get_all_series(status)
    # Parse keywords
    for s in series_list:
        if isinstance(s.get('keywords'), str):
            try:
                s['keywords'] = json.loads(s['keywords'])
            except:
                s['keywords'] = []
    return series_list

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

        related_news_ids = []
        if sl.related_news_ids:
            try:
                if isinstance(sl.related_news_ids, str):
                    related_news_ids = json.loads(sl.related_news_ids)
                elif isinstance(sl.related_news_ids, list):
                    related_news_ids = sl.related_news_ids
            except:
                related_news_ids = []
                
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
            related_event_ids=related_event_ids,
            related_news_ids=related_news_ids
        ))
    return response_list
