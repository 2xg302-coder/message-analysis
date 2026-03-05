from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import services
from database import (
    add_news, add_news_batch, get_latest_news, get_stats, 
    get_series_list, get_news_by_series, init_db
)
from analyzer import analysis_worker, get_analysis_status, set_analysis_status
from collector import fetch_and_save_news

# Pydantic models
class NewsItem(BaseModel):
    id: str
    title: Optional[str] = None
    link: Optional[str] = None
    content: Optional[str] = None
    time: Optional[str] = None
    timestamp: Optional[str] = None
    scrapedAt: Optional[str] = None
    source: Optional[str] = "unknown"
    raw_data: Optional[Dict[str, Any]] = None

class AnalysisControl(BaseModel):
    running: bool

class WatchlistUpdate(BaseModel):
    keywords: List[str]

# Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
    # Start analysis worker
    asyncio.create_task(analysis_worker())
    
    # Start scheduler for data collection
    scheduler.add_job(fetch_and_save_news, 'interval', minutes=10)
    scheduler.start()
    
    # Run collection immediately once on startup
    asyncio.create_task(asyncio.to_thread(fetch_and_save_news))
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes

@app.post("/api/news")
async def create_news(news_item: NewsItem):
    try:
        added = add_news(news_item.dict())
        print(f"[News] [{news_item.source}] Received: {news_item.title or (news_item.content[:20] if news_item.content else '')}...")
        return {"success": True, "added": added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/batch")
async def create_news_batch(news_list: List[NewsItem]):
    try:
        # Convert Pydantic models to dicts
        items = [item.dict() for item in news_list]
        added_count = add_news_batch(items)
        return {"success": True, "received": len(news_list), "added": added_count}
    except Exception as e:
        print(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

@app.get("/api/news")
async def read_news(source: Optional[str] = None):
    # Note: filtering by source is not implemented in db.py yet, but requested in original code
    # For now returning latest news
    news = get_latest_news()
    if source:
        news = [n for n in news if n.get('source') == source]
    return {"count": len(news), "data": news}

@app.get("/api/stats")
async def read_stats():
    try:
        stats = get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get stats")

@app.get("/api/series")
async def read_series():
    try:
        series_list = get_series_list()
        return {"success": True, "count": len(series_list), "data": series_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get series list")

@app.get("/api/series/{tag}")
async def read_series_by_tag(tag: str):
    try:
        news = get_news_by_series(tag)
        return {"success": True, "count": len(news), "data": news}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get series news")

@app.get("/api/watchlist")
async def read_watchlist():
    # Mock
    return {"success": True, "data": ['半导体', '人工智能', '新能源']}

@app.post("/api/watchlist")
async def update_watchlist(watchlist: WatchlistUpdate):
    print('Updated watchlist:', watchlist.keywords)
    return {"success": True}

@app.get("/api/analysis/status")
async def read_analysis_status():
    return {"success": True, "data": get_analysis_status()}

@app.post("/api/analysis/control")
async def control_analysis(control: AnalysisControl):
    set_analysis_status(control.running)
    return {"success": True, "running": control.running}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
