from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import os
import sys

try:
    from collectors.calendar_collector import CalendarCollector
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from collectors.calendar_collector import CalendarCollector

from core.database import db

router = APIRouter(
    prefix="/api/calendar",
    tags=["calendar"]
)

# Initialize collector
# Use relative path to data dir based on execution context
collector = CalendarCollector(data_dir="data")

@router.get("/today", response_model=List[Dict[str, Any]])
async def get_today_events():
    """
    Get high-importance economic events for today.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    return await get_events_by_date(today)

@router.get("/date/{date_str}", response_model=List[Dict[str, Any]])
async def get_events_by_date(date_str: str):
    """
    Get economic events for a specific date (YYYY-MM-DD).
    """
    try:
        # Validate date format
        datetime.strptime(date_str, '%Y-%m-%d')
        
        # 1. Try DB
        query = "SELECT * FROM calendar_events WHERE date = ? ORDER BY time ASC"
        events = db.execute_query(query, (date_str,))
        
        if events:
            return events
            
        # 2. If DB empty, try collector (which will save to DB)
        # Convert YYYY-MM-DD to YYYYMMDD for collector
        ak_date = date_str.replace('-', '')
        try:
            # This will collect and save to DB
            collector_events = collector.collect(ak_date)
            # Re-query DB to get consistent format or return collector result
            return collector_events
        except Exception as e:
            print(f"Collection failed for {date_str}: {e}")
            return []
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_calendar():
    """
    Manually trigger calendar refresh.
    """
    try:
        events = collector.collect()
        return {
            "status": "success", 
            "message": f"Collected {len(events)} events.",
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
