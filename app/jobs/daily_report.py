from datetime import datetime, timezone
from app.db.session import AsyncSessionLocal
from app.analytics.engine import AnalyticsEngine
from app.integrations.telegram.notifier import TelegramNotifier
from app.core.logging import logger

async def job_daily_report():
    """Background job to send daily performance report to Telegram."""
    logger.info("Generating daily report")
    try:
        now = datetime.now(timezone.utc)
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with AsyncSessionLocal() as db:
            engine = AnalyticsEngine(db)
            stats = await engine.calculate_period_stats(start_date, now)
        
        if stats.total_installations == 0:
            logger.info("No installations today, skipping daily report.")
            return
        
        date_str = now.strftime("%d.%m.%Y")
        text = (
            f"📅 <b>Отчёт за {date_str}</b>\n\n"
            f"Монтажей: {stats.total_installations}\n"
            f"Заказов с переносами: {stats.installations_with_postponement}\n"
            f"Фактов переносов: {stats.total_postponements}\n"
            f"Показатель: {stats.postponement_rate:.1f}%\n\n"
            f"<b>Монтажники:</b>\n"
        )
        
        for e in stats.employees:
            if e.total_installations > 0:
                text += (
                    f"\n<b>{e.employee_name}</b>\n"
                    f"{e.total_installations} монтажей\n"
                    f"{e.total_postponements} переносов\n"
                    f"{e.postponement_rate:.2f}%\n"
                )
        
        notifier = TelegramNotifier()
        await notifier.send_message(text)
        logger.info("Daily report sent successfully")
    except Exception as e:
        logger.error(f"Error in daily report job: {e}")
