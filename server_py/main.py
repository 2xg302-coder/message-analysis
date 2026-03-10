import sys
import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings

# Windows-specific asyncio policy fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.logging import get_logger
from services.ingestion import start_ingestion_scheduler, stop_ingestion_scheduler
from services.analyzer import start_scheduler as start_analysis_scheduler, stop_scheduler as stop_analysis_scheduler

# Routers
from routers import news, analysis, calendar, storyline, monitor, reports, ingestion, maintenance

logger = get_logger("main")
_bootstrap_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bootstrap_task
    logger.info("Application starting up...")
    from core.database_orm import init_db
    await init_db()

    async def bootstrap_services():
        try:
            if settings.APP_STARTUP_DELAY_SECONDS > 0:
                await asyncio.sleep(settings.APP_STARTUP_DELAY_SECONDS)
            await start_ingestion_scheduler()
            await start_analysis_scheduler()
            logger.info("Background service bootstrap completed.")
        except Exception as e:
            logger.error(f"Background service bootstrap failed: {e}")

    if settings.APP_STARTUP_BACKGROUND:
        _bootstrap_task = asyncio.create_task(bootstrap_services())
        logger.info("Service bootstrap scheduled in background.")
    else:
        await bootstrap_services()
    
    yield
    
    logger.info("Application shutting down...")
    if _bootstrap_task and not _bootstrap_task.done():
        _bootstrap_task.cancel()
    stop_ingestion_scheduler()
    stop_analysis_scheduler()

app = FastAPI(lifespan=lifespan, title="News Analysis API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 认证中间件
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
        
    if not settings.API_SECRET:
        return await call_next(request)
    
    if request.url.path in {"/health", "/ready", "/"}:
        return await call_next(request)
        
    api_key = request.headers.get("X-API-Key")
    
    if not api_key or not secrets.compare_digest(api_key, settings.API_SECRET):
        return JSONResponse(
            status_code=401,
            content={"detail": "未授权: API Key 无效或缺失"}
        )
        
    response = await call_next(request)
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

# Include Routers
app.include_router(news.router)
app.include_router(analysis.router)
app.include_router(calendar.router)
app.include_router(storyline.router)
app.include_router(monitor.router)
app.include_router(reports.router)
app.include_router(ingestion.router)
app.include_router(maintenance.router)

if __name__ == "__main__":
    import uvicorn
    # Use selector event loop on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    logger.info("Starting server on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")
