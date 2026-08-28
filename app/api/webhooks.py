import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.sync_engine import SyncService
from app.schemas.external import InstallationDTO, OrderDTO, EmployeeDTO
from app.core.logging import logger

router = APIRouter()

@router.post("/webhook", tags=["Integration"])
async def process_webhook(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """
    Webhook endpoint to receive events from external CRM.
    The payload structure must be adapted based on real CRM specification.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    
    event_id = payload.get("event_id", str(uuid.uuid4()))
    
    try:
        # Example mapping (in reality, an Adapter pattern will map specific CRM JSON to our DTOs)
        inst_payload = payload.get("installation")
        if not inst_payload:
            return {"status": "ignored", "reason": "No installation data"}
            
        dto = InstallationDTO(**inst_payload)
    except Exception as e:
        logger.error(f"Invalid payload format: {str(e)}", extra={"extra_info": {"payload": payload}})
        raise HTTPException(status_code=422, detail="Invalid payload schema")

    sync_service = SyncService(db)
    
    try:
        # Before processing installation, we optionally upsert order/employee if provided in payload
        if "order" in payload:
            await sync_service.upsert_order(OrderDTO(**payload["order"]))
        if "employee" in payload:
            await sync_service.upsert_employee(EmployeeDTO(**payload["employee"]))
            
        await sync_service.process_installation(dto=dto, event_id=event_id, raw_payload=payload)
        
        await db.commit()
        return {"status": "ok", "event_id": event_id}
        
    except ValueError as e:
        await db.rollback()
        logger.warning(f"Validation error in webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail="Internal server error")
