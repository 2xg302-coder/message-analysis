from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ingestion import get_source_configs, set_source_enabled

router = APIRouter(prefix="/api/ingestion")


class SourceControl(BaseModel):
    enabled: bool


@router.get("/sources")
async def read_source_configs():
    data = await get_source_configs()
    return {"success": True, "data": data}


@router.put("/sources/{source}")
async def update_source_config(source: str, payload: SourceControl):
    try:
        await set_source_enabled(source, payload.enabled)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update source config")
