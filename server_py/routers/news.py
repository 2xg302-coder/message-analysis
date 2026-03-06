from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# Import models
# Assuming models.py is in the parent directory (server_py)
# When running from server_py context, we can import directly if sys.path is set correctly
# Or we can use relative imports if this is a package
try:
    from models import NewsItem
except ImportError:
    # Fallback if models not found directly
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models import NewsItem

from fastapi import Depends
from services.news_service import NewsService
from services.deps import get_news_service
from core.logging import get_logger

logger = get_logger("news_router")
router = APIRouter(prefix="/api")

class WatchlistUpdate(BaseModel):
    keywords: List[str]

@router.post("/news")
async def create_news(news_item: NewsItem, service: NewsService = Depends(get_news_service)):
    try:
        item_dict = news_item.dict()
        added = await service.add_news(item_dict)
        return {"success": True, "added": added}
    except Exception as e:
        logger.error(f"Error creating news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/news/batch")
async def create_news_batch(news_list: List[NewsItem], service: NewsService = Depends(get_news_service)):
    try:
        items = [item.dict() for item in news_list]
        added_count = await service.add_news_batch(items)
        return {"success": True, "received": len(news_list), "added": added_count}
    except Exception as e:
        logger.error(f"Error creating news batch: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

@router.get("/news")
async def read_news(
    limit: int = 100, 
    offset: int = 0, 
    type: Optional[str] = None, 
    min_impact: Optional[int] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: NewsService = Depends(get_news_service)
):
    try:
        if type == 'all':
            type = None
            
        news = await service.get_news(
            limit=limit, 
            offset=offset, 
            news_type=type, 
            min_impact=min_impact,
            tag=tag,
            start_date=start_date,
            end_date=end_date
        )
        
        # Filter by source if needed (DB doesn't index source efficiently yet, do in memory or update service)
        if source:
             news = [n for n in news if n.get('source') == source]

        return {"count": len(news), "data": news}
    except Exception as e:
        logger.error(f"Error reading news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def read_stats(start_date: Optional[str] = None, end_date: Optional[str] = None, service: NewsService = Depends(get_news_service)):
    try:
        stats = await service.get_stats(start_date=start_date, end_date=end_date)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error reading stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

@router.get("/stats/tags")
async def read_tag_stats(limit: int = 100, start_date: Optional[str] = None, end_date: Optional[str] = None, service: NewsService = Depends(get_news_service)):
    try:
        tags = await service.get_tag_stats(limit=limit, start_date=start_date, end_date=end_date)
        return {"success": True, "count": len(tags), "data": tags}
    except Exception as e:
        logger.error(f"Error reading tag stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tag stats")

@router.get("/stats/types")
async def read_type_stats(start_date: Optional[str] = None, end_date: Optional[str] = None, service: NewsService = Depends(get_news_service)):
    try:
        types = await service.get_type_stats(start_date=start_date, end_date=end_date)
        return {"success": True, "count": len(types), "data": types}
    except Exception as e:
        logger.error(f"Error reading type stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get type stats")

@router.get("/entities")
async def read_entities(limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None, service: NewsService = Depends(get_news_service)):
    try:
        entities = await service.get_top_entities(limit=limit, start_date=start_date, end_date=end_date)
        return {"success": True, "count": len(entities), "data": entities}
    except Exception as e:
        logger.error(f"Error reading entities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get entities")

@router.get("/series")
async def read_series(service: NewsService = Depends(get_news_service)):
    try:
        series_list = await service.get_series_list()
        return {"success": True, "count": len(series_list), "data": series_list}
    except Exception as e:
        logger.error(f"Error reading series: {e}")
        raise HTTPException(status_code=500, detail="Failed to get series list")

@router.get("/series/{tag}")
async def read_series_by_tag(tag: str, service: NewsService = Depends(get_news_service)):
    try:
        news = await service.get_news_by_series(tag)
        return {"success": True, "count": len(news), "data": news}
    except Exception as e:
        logger.error(f"Error reading series tag {tag}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get series news")

@router.get("/watchlist")
async def read_watchlist(service: NewsService = Depends(get_news_service)):
    keywords = await service.get_watchlist()
    if not keywords:
        keywords = ['半导体', '人工智能', '新能源']
        await service.update_watchlist(keywords)
    return {"success": True, "data": keywords}

@router.post("/watchlist")
async def update_watchlist_endpoint(watchlist: WatchlistUpdate, service: NewsService = Depends(get_news_service)):
    success = await service.update_watchlist(watchlist.keywords)
    if not success:
         raise HTTPException(status_code=500, detail="Failed to update watchlist")
    return {"success": True}
