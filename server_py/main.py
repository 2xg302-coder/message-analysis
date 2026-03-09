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
from services.analyzer import start_scheduler as start_analysis_scheduler

# Routers
from routers import news, analysis, calendar, storyline, monitor, reports, ingestion

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    
    # Init Database (Raw) - Moved from sync import time to async startup
    from core.database import db
    await db.init_db()

    # Init ORM DB (ensure tables)
    from core.database_orm import init_db
    await init_db()

    # Start Schedulers
    await start_ingestion_scheduler()
    await start_analysis_scheduler()
    
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

# API 认证中间件
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # 允许 OPTIONS 请求（CORS 预检）直接通过
    if request.method == "OPTIONS":
        return await call_next(request)
        
    # 如果没有配置 API_SECRET，则跳过验证（开发模式或未启用认证）
    if not settings.API_SECRET:
        return await call_next(request)
    
    # 如果请求的是静态资源或文档（如果以后添加），可以放行
    # 目前只保护 /api 路径，但为了简单起见，保护所有非 OPTIONS 请求
    # 如果有健康检查端点如 /health，可以排除
    if request.url.path == "/health" or request.url.path == "/":
        return await call_next(request)
        
    # 获取请求头中的 API Key
    api_key = request.headers.get("X-API-Key")
    
    # 验证 API Key
    # 使用 secrets.compare_digest 防止时序攻击
    if not api_key or not secrets.compare_digest(api_key, settings.API_SECRET):
        return JSONResponse(
            status_code=401,
            content={"detail": "未授权: API Key 无效或缺失"}
        )
        
    response = await call_next(request)
    return response

# Include Routers
app.include_router(news.router)
app.include_router(analysis.router)
app.include_router(calendar.router)
app.include_router(storyline.router)
app.include_router(monitor.router)
app.include_router(reports.router)
app.include_router(ingestion.router)

if __name__ == "__main__":
    import uvicorn
    # Use selector event loop on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    logger.info("Starting server on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")
