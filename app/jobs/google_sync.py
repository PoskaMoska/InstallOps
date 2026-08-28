from datetime import datetime, timezone
from app.db.session import AsyncSessionLocal
from app.analytics.engine import AnalyticsEngine
from app.integrations.google.sheets import GoogleSheetsProvider
from app.core.logging import logger

async def job_sync_google_sheets():
    """Background job to aggregate statistics and export to Google Sheets."""
    logger.info("Starting scheduled Google Sheets sync")
    try:
        now = datetime.now(timezone.utc)
        # Assuming we want current month statistics on the dashboard
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async with AsyncSessionLocal() as db:
            engine = AnalyticsEngine(db)
            stats = await engine.calculate_period_stats(start_date, now)
            
        provider = GoogleSheetsProvider()
        await provider.publish_statistics(stats)
        logger.info("Scheduled Google Sheets sync completed successfully")
    except Exception as e:
        logger.error(f"Error in Google Sheets sync job: {e}")
