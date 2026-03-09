from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from services.daily_report_service import DailyReportService
from services.deps import get_daily_report_service
from core.logging import get_logger

logger = get_logger("reports_router")
router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/daily")
async def get_daily_report(
    date: Optional[str] = Query(None, description="Report date in YYYY-MM-DD format. Defaults to yesterday."),
    service: DailyReportService = Depends(get_daily_report_service)
):
    try:
        if not date:
            # Default to yesterday
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
        report = await service.generate_report(date)
        return {"success": True, "data": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
