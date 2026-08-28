import pytest
from datetime import date
from sqlalchemy import select, func

from app.schemas.external import InstallationDTO, OrderDTO
from app.services.sync_engine import SyncService
from app.models import Installation, InstallationHistory, Postponement

@pytest.mark.asyncio
async def test_acceptance_scenarios_a_to_d(db_session):
    """
    Integration tests covering acceptance scenarios A through D 
    from the original requirements.
    """
    sync_service = SyncService(db_session)
    
    # Prerequisite: Create the order
    order_dto = OrderDTO(external_id="order-123", status="new", client_name="Тест")
    await sync_service.upsert_order(order_dto)
    
    # ---------------------------------------------------------
    # Сценарий A — новый заказ
    # Новый монтаж -> sync -> PostgreSQL
    # ---------------------------------------------------------
    inst_dto_1 = InstallationDTO(
        external_id="inst-123",
        order_external_id="order-123",
        scheduled_date=date(2026, 8, 25),
        status="scheduled"
    )
    await sync_service.process_installation(inst_dto_1, event_id="event-A", raw_payload={})
    
    # Verify A
    inst_count = (await db_session.execute(select(func.count(Installation.id)))).scalar()
    hist_count = (await db_session.execute(select(func.count(InstallationHistory.id)))).scalar()
    post_count = (await db_session.execute(select(func.count(Postponement.id)))).scalar()
    
    assert inst_count == 1
    assert hist_count == 1  # 1 creation history
    assert post_count == 0  # No postponements
    
    # ---------------------------------------------------------
    # Сценарий B — первый перенос
    # 25.08 -> 27.08 (postponements = 1)
    # ---------------------------------------------------------
    inst_dto_2 = InstallationDTO(
        external_id="inst-123",
        order_external_id="order-123",
        scheduled_date=date(2026, 8, 27),
        status="scheduled"
    )
    await sync_service.process_installation(
        inst_dto_2, 
        event_id="event-B", 
        raw_payload={"reason": "клиент перенес"}
    )
    
    post_count = (await db_session.execute(select(func.count(Postponement.id)))).scalar()
    assert post_count == 1  # Exactly 1 postponement detected
    
    # ---------------------------------------------------------
    # Сценарий C — второй перенос
    # 27.08 -> 30.08 (postponements = 2)
    # ---------------------------------------------------------
    inst_dto_3 = InstallationDTO(
        external_id="inst-123",
        order_external_id="order-123",
        scheduled_date=date(2026, 8, 30),
        status="scheduled"
    )
    await sync_service.process_installation(
        inst_dto_3, 
        event_id="event-C", 
        raw_payload={"reason": "машина сломалась"}
    )
    
    post_count = (await db_session.execute(select(func.count(Postponement.id)))).scalar()
    assert post_count == 2  # Exactly 2 postponements now
    
    # ---------------------------------------------------------
    # Сценарий D — duplicate event
    # Один event приходит дважды. postponements не увеличивается.
    # ---------------------------------------------------------
    await sync_service.process_installation(
        inst_dto_3,  # Exactly the same DTO state
        event_id="event-C-duplicate", 
        raw_payload={"reason": "машина сломалась"}
    )
    
    post_count_after_dup = (await db_session.execute(select(func.count(Postponement.id)))).scalar()
    assert post_count_after_dup == 2  # Remains 2, idempotency works perfectly!
    
    # Check history count - should be 3 (creation, shift 1, shift 2). Duplicate is ignored.
    hist_count = (await db_session.execute(select(func.count(InstallationHistory.id)))).scalar()
    assert hist_count == 3
