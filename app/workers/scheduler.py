from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.jobs.google_sync import job_sync_google_sheets
from app.jobs.daily_report import job_daily_report
from app.core.config import settings

scheduler = AsyncIOScheduler()

def setup_scheduler():
    # Sync Google Sheets periodically
    scheduler.add_job(
        job_sync_google_sheets, 
        'interval', 
        minutes=settings.SYNC_INTERVAL_MINUTES,
        id='google_sheets_sync',
        replace_existing=True
    )
    
    # Send Daily report every day at 20:00 (UTC)
    scheduler.add_job(
        job_daily_report,
        'cron',
        hour=20,
        minute=0,
        id='daily_telegram_report',
        replace_existing=True
    )
    
    # Check pending Telegram events every minute
    from app.jobs.pending_processor import process_pending_events_job
    scheduler.add_job(
        process_pending_events_job,
        'interval',
        minutes=1,
        id='process_pending_events',
        replace_existing=True
    )

def start_scheduler():
    setup_scheduler()
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
