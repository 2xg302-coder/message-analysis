import sys
import asyncio

# Windows-specific asyncio policy fix
if sys.platform == 'win32':
    # This needs to happen before any asyncio loop is created
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import services
from database import (
    add_news, add_news_batch, get_latest_news, get_stats, 
    get_series_list, get_news_by_series, init_db,
    get_watchlist, update_watchlist as db_update_watchlist,
    get_news_filtered, get_top_entities
)
from analyzer import get_analysis_status, set_analysis_status, start_scheduler
from models import NewsItem

# Import Collectors and Processor
try:
    from collectors.sina_collector import SinaCollector
    from collectors.eastmoney_collector import EastMoneyCollector
    from processor import NewsProcessor
    COLLECTORS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Collectors or Processor not available: {e}")
    COLLECTORS_AVAILABLE = False

class AnalysisControl(BaseModel):
    running: bool

class WatchlistUpdate(BaseModel):
    keywords: List[str]

# Scheduler
scheduler = AsyncIOScheduler()

# Collector wrapper
async def run_ingestion(collector, source_name, processor):
    # print(f"Running ingestion for {source_name}...")
    try:
        # Run in executor to avoid blocking event loop
        news_list = await asyncio.to_thread(collector.collect)
        if news_list:
            processed_list = []
            for news in news_list:
                try:
                    # Process news (clean, dedupe, NER, rate)
                    processed = processor.process(news)
                    if processed:
                        # Map processed fields to NewsItem/DB schema
                        # Processor adds 'rating' dict, we need to flatten it to impact_score/sentiment_score
                        if 'rating' in processed:
                            processed['impact_score'] = processed['rating'].get('impact_score', 0)
                            processed['sentiment_score'] = processed['rating'].get('sentiment', 0.0)
                        
                        # Processor adds 'entities' list of dicts/strings. 
                        # DB expects 'entities' to be a dict {name: type/desc} or just JSON.
                        # Database.py handles JSON dumping.
                        # But NewsItem expects Dict[str, str].
                        # Processor adds 'entities' list of dicts: [{'name': 'Moutai', 'code': '600519', ...}]
                        # We should convert it to {'Moutai': '600519'} or similar.
                        if 'entities' in processed and isinstance(processed['entities'], list):
                            ent_dict = {}
                            for ent in processed['entities']:
                                if isinstance(ent, dict):
                                    ent_dict[ent.get('name', 'Unknown')] = ent.get('code', 'Stock')
                                elif isinstance(ent, str):
                                    ent_dict[ent] = 'Keyword'
                            processed['entities'] = ent_dict
                        
                        # Processor adds 'tags' list of strings.
                        # DB expects 'tags' to be a list or JSON string (handled by database.py).
                        # NewsItem expects List[str].
                        if 'tags' not in processed:
                            processed['tags'] = []
                        
                        processed_list.append(processed)
                except Exception as e:
                    print(f"Error processing item from {source_name}: {e}")
            
            if processed_list:
                count = add_news_batch(processed_list)
                print(f"Saved {count} new items from {source_name}")
            else:
                pass
                # print(f"No new items from {source_name} after processing (all duplicates/filtered).")
    except Exception as e:
        print(f"Ingestion error for {source_name}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        init_db()
        start_scheduler()
        
        # Start Collectors if available
        if COLLECTORS_AVAILABLE:
            sina_collector = SinaCollector()
            em_collector = EastMoneyCollector()
            processor = NewsProcessor()
            
            # Use the analyzer's scheduler or creating a new one?
            # analyzer.start_scheduler() starts its own scheduler.
            # We can use the same scheduler if we import it, but it's not exported directly as 'scheduler' var from analyzer.
            # But we have 'scheduler' var in main.py (from AsyncIOScheduler()).
            # We can use that one for ingestion.
            
            scheduler.add_job(run_ingestion, IntervalTrigger(seconds=30), args=[sina_collector, 'Sina', processor], id='sina_ingestion', replace_existing=True)
            scheduler.add_job(run_ingestion, IntervalTrigger(minutes=5), args=[em_collector, 'EastMoney', processor], id='em_ingestion', replace_existing=True)
            scheduler.start()
            print("Ingestion Scheduler started.")
            
            # Run immediately on startup
            asyncio.create_task(run_ingestion(sina_collector, 'Sina', processor))
            # asyncio.create_task(run_ingestion(em_collector, 'EastMoney', processor)) 
            
    except Exception as e:
        print(f"Startup Error: {e}")
    
    yield
    
    # Shutdown
    if scheduler.running:
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
        # Convert Pydantic model to dict
        item_dict = news_item.dict()
        added = add_news(item_dict)
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
async def read_news(
    limit: int = 100, 
    offset: int = 0, 
    type: Optional[str] = None, 
    min_impact: Optional[int] = None,
    source: Optional[str] = None # Keeping for backward compatibility if needed
):
    try:
        # Handle 'all' type from frontend
        if type == 'all':
            type = None
            
        # If source is provided, we might want to filter by it too, but current task didn't specify it.
        # However, the previous implementation had it.
        # But get_news_filtered doesn't support source yet.
        # I'll stick to the requested parameters: limit, offset, type, min_impact.
        
        news = get_news_filtered(limit=limit, offset=offset, news_type=type, min_impact=min_impact)
        
        if source:
             news = [n for n in news if n.get('source') == source]
             
        return {"count": len(news), "data": news}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def read_stats():
    try:
        stats = get_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get stats")

@app.get("/api/entities")
async def read_entities(limit: int = 50):
    try:
        entities = get_top_entities(limit=limit)
        return {"success": True, "count": len(entities), "data": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get entities")

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
    keywords = get_watchlist()
    if not keywords:
        # Default fallback if empty
        keywords = ['半导体', '人工智能', '新能源']
        db_update_watchlist(keywords)
    return {"success": True, "data": keywords}

@app.post("/api/watchlist")
async def update_watchlist_endpoint(watchlist: WatchlistUpdate):
    success = db_update_watchlist(watchlist.keywords)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to update watchlist")
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
    if sys.platform == 'win32':
        # Use selector event loop on Windows to avoid "WinError 10022" and other issues
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")
