from fastapi import APIRouter
from services.analyzer import get_analysis_status
from services.news_service import news_service
from services.storyline_manager import StorylineManager
from datetime import datetime

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

@router.get("/stats")
async def get_monitor_stats():
    # 1. Get Analyzer Status (Processing)
    analyzer_status = get_analysis_status()
    
    # 2. Get News Stats (Collection, Backlog, Failures)
    news_stats = await news_service.get_monitor_stats()
    
    # 3. Get Storyline Stats (Extracted Topics)
    storyline_manager = StorylineManager()
    storyline_stats = await storyline_manager.get_storyline_stats()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "analyzer": {
            "isRunning": analyzer_status["isRunning"],
            "schedulerRunning": analyzer_status["schedulerRunning"],
            "currentTasks": analyzer_status["currentTasks"],
            "processingCount": len(analyzer_status["currentTasks"]),
            "maxConcurrency": analyzer_status.get("maxConcurrency", 8),
            "processedTotal": analyzer_status["processedCount"],
            "failedTotal": analyzer_status["failedCount"],
            "lastProcessedTime": analyzer_status["lastProcessedTime"]
        },
        "collection": {
            "today": news_stats["collected_today"],
            "processedToday": news_stats["processed_today"],
            "backlog": news_stats["pending_count"],
            "failedToday": news_stats["failed_today"]
        },
        "topics": {
            "total": storyline_stats["total"],
            "active": storyline_stats["active"],
            "generatedToday": storyline_stats["today"]
        }
    }
