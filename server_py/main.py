import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Windows-specific asyncio policy fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.logging import get_logger
from services.ingestion import start_ingestion_scheduler, stop_ingestion_scheduler
from analyzer import start_scheduler as start_analysis_scheduler

# Routers
from routers import news, analysis, calendar

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    
    # Start Schedulers
    start_ingestion_scheduler()
    start_analysis_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    stop_ingestion_scheduler()
    # Analyzer scheduler shutdown is handled internally or needs explicit call if we expose it
    # Currently analyzer.py has scheduler global but no stop function exposed easily without import
    # We can rely on process termination or add stop_scheduler to analyzer.py later.

app = FastAPI(lifespan=lifespan, title="News Analysis API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(news.router)
app.include_router(analysis.router)
app.include_router(calendar.router)

if __name__ == "__main__":
    import uvicorn
    # Use selector event loop on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    logger.info("Starting server on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")
