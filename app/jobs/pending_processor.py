from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.pending import PendingEvent
from app.models.employee import Employee
from app.services.sync_engine import SyncService
from app.schemas.external import InstallationDTO, OrderDTO
from app.core.logging import logger

async def process_pending_events_job():
    """
    Checks for PendingEvents that are older than 10 minutes and haven't been rejected/confirmed yet.
    Automatically confirms them and processes them as true postponements.
    """
    logger.info("Running Pending Events Processor (10-minute rule)")
    now = datetime.now(timezone.utc)
    # Ищем записи со статусом 'pending' и созданные более 10 минут назад
    # (правило 10 минут на отмену/изменение)
    cutoff_time = now - timedelta(minutes=10)
    
    async with AsyncSessionLocal() as db:
        stmt = select(PendingEvent).where(
            PendingEvent.status == "pending",
            PendingEvent.created_at <= cutoff_time
        )
        result = await db.execute(stmt)
        pending_events = result.scalars().all()
        
        if not pending_events:
            return
            
        sync_service = SyncService(db)
        
        for event in pending_events:
            try:
                # 1. Resolve employee by telegram_user_id
                emp_stmt = select(Employee).where(Employee.telegram_user_id == event.telegram_user_id)
                emp = (await db.execute(emp_stmt)).scalars().first()
                
                if not emp:
                    # If we don't know this user, maybe create a placeholder or just log it
                    # For now, we will create an Employee based on telegram ID
                    emp = Employee(
                        external_id=f"tg-{event.telegram_user_id}",
                        telegram_user_id=event.telegram_user_id,
                        name=f"TG User {event.telegram_user_id}"
                    )
                    db.add(emp)
                    await db.flush()
                
                # 2. Push through sync engine
                # We need to make sure an order and installation exist
                order_dto = OrderDTO(
                    external_id=event.ticket_number,
                    status="active"
                )
                await sync_service.upsert_order(order_dto)
                
                # We simulate an installation DTO
                inst_dto = InstallationDTO(
                    external_id=f"inst-{event.ticket_number}",
                    order_external_id=event.ticket_number,
                    employee_external_id=emp.external_id,
                    scheduled_date=now.date(), # date doesn't matter much anymore, just the fact
                    status="postponed"
                )
                
                postponement = await sync_service.process_installation(
                    inst_dto, 
                    event_id=str(event.id), 
                    raw_payload={"reason": event.extracted_reason, "from_chat": True}
                )
                
                # Append directly to Google Sheets log ONLY if it's a new postponement
                if postponement:
                    try:
                        from app.integrations.google.sheets import GoogleSheetsProvider
                        sheets = GoogleSheetsProvider()
                        await sheets.append_postponement_log(
                            ticket_number=event.ticket_number,
                            employee_name=emp.name,
                            tg_id=str(event.telegram_user_id),
                            reason=event.extracted_reason or "Не указано",
                            date_str=now.strftime("%Y-%m-%d %H:%M")
                        )
                    except Exception as sheet_err:
                        logger.error(f"Failed to append to Google Sheets: {sheet_err}")
                
                event.status = "confirmed"
            except Exception as e:
                logger.error(f"Failed to process pending event {event.id}: {e}")
                # We might mark it failed, but for now leave pending or error
                
        await db.commit()
