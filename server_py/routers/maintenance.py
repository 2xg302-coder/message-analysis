from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel

from services.maintenance_service import maintenance_service
from core.logging import get_logger

logger = get_logger("maintenance_router")
router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])

class CleanupRequest(BaseModel):
    days: int = 30
    min_score: int = 0
    source: Optional[str] = None
    dry_run: bool = True

class DeleteSourceRequest(BaseModel):
    source: str

@router.get("/stats")
async def get_stats():
    """获取数据库维护统计信息"""
    return await maintenance_service.get_db_stats()

@router.post("/cleanup")
async def cleanup_news(req: CleanupRequest):
    """手动触发新闻清理"""
    result = await maintenance_service.cleanup_news(
        days_retention=req.days,
        min_score=req.min_score,
        target_source=req.source,
        dry_run=req.dry_run
    )
    return result

@router.post("/delete-source")
async def delete_source_news(req: DeleteSourceRequest):
    """删除指定来源的所有新闻"""
    if not req.source:
        raise HTTPException(status_code=400, detail="Source is required")
        
    result = await maintenance_service.delete_by_source(req.source)
    return result

@router.post("/vacuum")
async def vacuum_database(background_tasks: BackgroundTasks):
    """触发数据库 VACUUM (后台执行)"""
    background_tasks.add_task(maintenance_service.vacuum_db)
    return {"status": "accepted", "message": "Vacuum task scheduled in background"}
