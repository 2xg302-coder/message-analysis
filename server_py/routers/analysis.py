from fastapi import APIRouter
from pydantic import BaseModel
from analyzer import get_analysis_status, set_analysis_status

router = APIRouter(prefix="/api/analysis")

class AnalysisControl(BaseModel):
    running: bool

@router.get("/status")
async def read_analysis_status():
    return {"success": True, "data": get_analysis_status()}

@router.post("/control")
async def control_analysis(control: AnalysisControl):
    set_analysis_status(control.running)
    return {"success": True, "running": control.running}
