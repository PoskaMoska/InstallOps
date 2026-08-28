from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import logger
from app.api.webhooks import router as webhooks_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Installation Tracking & Analytics System API",
    version="0.1.0",
)

from app.workers.scheduler import start_scheduler, stop_scheduler

app.include_router(webhooks_router, prefix="/api")

from app.integrations.telegram.bot import start_bot
import asyncio

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up", extra={"extra_info": {"env": settings.ENVIRONMENT}})
    
    # Initialize Google Sheets structure
    try:
        from app.integrations.google.sheets import GoogleSheetsProvider
        sheets = GoogleSheetsProvider()
        await sheets.async_initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Sheets on startup: {e}")
        
    start_scheduler()
    asyncio.create_task(start_bot())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
    stop_scheduler()

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@app.get("/ready", tags=["System"])
async def ready_check():
    # TODO: Check database connection here
    return {"status": "ready"}

