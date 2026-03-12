from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from services.daily_report_service import DailyReportService
from services.weekly_report_service import WeeklyReportService
from services.deps import get_daily_report_service, get_weekly_report_service
from core.logging import get_logger

logger = get_logger("reports_router")
router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/daily")
async def get_daily_report(
    date: Optional[str] = Query(None, description="Report date in YYYY-MM-DD format. Defaults to yesterday."),
    refresh: bool = Query(False, description="Force regenerate report"),
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
            
        if not refresh:
            snapshot = await service.get_report_snapshot(date)
            if snapshot:
                return {"success": True, "data": snapshot}
            
        report = await service.generate_report(date)
        return {"success": True, "data": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/history")
async def get_report_history(
    limit: int = 30,
    service: DailyReportService = Depends(get_daily_report_service)
):
    try:
        dates = await service.get_available_dates(limit)
        return {"success": True, "dates": dates}
    except Exception as e:
        logger.error(f"Error fetching report history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.get("/weekly")
async def get_weekly_report(
    week_start: Optional[str] = Query(None, description="Week start date in YYYY-MM-DD format (Monday)."),
    refresh: bool = Query(False, description="Force regenerate report"),
    service: WeeklyReportService = Depends(get_weekly_report_service)
):
    try:
        if not week_start:
            # Default to current week's Monday (or last week's if today is Monday and early?)
            # Usually report is for past week. Let's default to the Monday of the *current* week if requested,
            # OR maybe default to last completed week?
            # User requirement: "Generate report for this week".
            # Let's default to the Monday of the current week.
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            week_start = start_of_week.strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            dt = datetime.strptime(week_start, "%Y-%m-%d")
            # Ensure it is Monday? Not strictly necessary but good practice.
            # if dt.weekday() != 0: ...
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
        if not refresh:
            snapshot = await service.get_report_snapshot(week_start)
            if snapshot:
                return {"success": True, "data": snapshot}
            
        report = await service.generate_report(week_start)
        return {"success": True, "data": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/weekly/history")
async def get_weekly_report_history(
    limit: int = 30,
    service: WeeklyReportService = Depends(get_weekly_report_service)
):
    try:
        weeks = await service.get_available_weeks(limit)
        return {"success": True, "weeks": weeks}
    except Exception as e:
        logger.error(f"Error fetching weekly report history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
