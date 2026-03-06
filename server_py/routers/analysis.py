from fastapi import APIRouter, Query
from pydantic import BaseModel
from services.analyzer import get_analysis_status, set_analysis_status
from services.entity_miner import get_entity_miner_result

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

@router.get("/entity-graph")
async def get_entity_graph(
    hours: int = Query(2, ge=1, le=48, description="Lookback hours"),
    force: bool = Query(False, description="Force refresh cache")
):
    """
    Get entity co-occurrence graph data for visualization.
    """
    graph_data, _ = await get_entity_miner_result(hours=hours, force_refresh=force)
    return {"success": True, "data": graph_data}

@router.get("/hot-clusters")
async def get_hot_clusters(
    hours: int = Query(2, ge=1, le=48, description="Lookback hours"),
    force: bool = Query(False, description="Force refresh cache")
):
    """
    Get detected entity communities (hot topics).
    """
    _, clusters = await get_entity_miner_result(hours=hours, force_refresh=force)
    return {"success": True, "data": clusters}
