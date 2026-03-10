from fastapi import APIRouter, Query
from pydantic import BaseModel
from services.analyzer import get_analysis_status, set_analysis_status
from services.entity_miner import get_entity_miner_result

from core.logging import get_logger

logger = get_logger("analysis_router")

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
    force: bool = Query(False, description="Force refresh cache"),
    type: str = Query("cooccurrence", description="Graph type: 'cooccurrence' or 'causal'")
):
    try:
        graph_data, clusters = await get_entity_miner_result(hours=hours, force_refresh=force, graph_type=type)
        return {
            "success": True, 
            "data": {
                "nodes": graph_data.get("nodes", []),
                "links": graph_data.get("links", []),
                "clusters": clusters
            }
        }
    except Exception as e:
        logger.error(f"Error generating entity graph: {e}")
        return {
            "success": False,
            "data": {"nodes": [], "links": []},
            "error": str(e)
        }

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
