from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.schemas.external import EmployeeDTO, OrderDTO, InstallationDTO
from app.models import Employee, Order, Installation, InstallationHistory, SyncRun
from app.repositories import crud
from app.core.logging import logger

class SyncService:
    """
    Core engine for synchronizing data from external CRM.
    Ensures idempotency and history tracking.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.run_id = None

    async def start_run(self) -> SyncRun:
        run = SyncRun(started_at=datetime.now(timezone.utc), status="running")
        self.db.add(run)
        await self.db.flush()
        self.run_id = run.id
        return run
        
    async def finish_run(self, status: str = "success", error_msg: Optional[str] = None):
        if not self.run_id:
            return
        run = await self.db.get(SyncRun, self.run_id)
        if run:
            run.finished_at = datetime.now(timezone.utc)
            run.status = status
            run.error_message = error_msg
            await self.db.flush()

    async def upsert_employee(self, dto: EmployeeDTO) -> Employee:
        emp = await crud.get_employee_by_ext_id(self.db, dto.external_id)
        if not emp:
            emp = Employee(
                external_id=dto.external_id, 
                name=dto.name, 
                phone=dto.phone, 
                status=dto.status
            )
            self.db.add(emp)
            logger.info(f"Created employee: {dto.external_id}")
        else:
            emp.name = dto.name
            emp.phone = dto.phone
            emp.status = dto.status
        await self.db.flush()
        return emp

    async def upsert_order(self, dto: OrderDTO) -> Order:
        order = await crud.get_order_by_ext_id(self.db, dto.external_id)
        if not order:
            order = Order(
                external_id=dto.external_id,
                client_name=dto.client_name,
                client_phone=dto.client_phone,
                status=dto.status,
                created_at_external=dto.created_at_external,
                updated_at_external=dto.updated_at_external
            )
            self.db.add(order)
            logger.info(f"Created order: {dto.external_id}")
        else:
            order.client_name = dto.client_name
            order.client_phone = dto.client_phone
            order.status = dto.status
            order.updated_at_external = dto.updated_at_external
        await self.db.flush()
        return order

    async def process_installation(self, dto: InstallationDTO, event_id: str, raw_payload: dict) -> Installation:
        """
        Idempotent processor for installation changes.
        Creates InstallationHistory entry ONLY if date, employee or status changed.
        """
        order = await crud.get_order_by_ext_id(self.db, dto.order_external_id)
        if not order:
            raise ValueError(f"Order {dto.order_external_id} not found. Cannot process installation.")
        
        emp = None
        if dto.employee_external_id:
            emp = await crud.get_employee_by_ext_id(self.db, dto.employee_external_id)

        inst = None
        if dto.external_id:
            inst = await crud.get_installation_by_ext_id(self.db, dto.external_id)
        if not inst:
            inst = await crud.get_installation_by_order_id(self.db, order.id)

        if not inst:
            # Create new installation and initial history
            inst = Installation(
                external_id=dto.external_id,
                order_id=order.id,
                employee_id=emp.id if emp else None,
                scheduled_date=dto.scheduled_date,
                actual_date=dto.actual_date,
                status=dto.status
            )
            self.db.add(inst)
            await self.db.flush()
            
            hist = InstallationHistory(
                installation_id=inst.id,
                changed_at=datetime.now(timezone.utc),
                old_date=None,
                new_date=dto.scheduled_date,
                old_employee_id=None,
                new_employee_id=emp.id if emp else None,
                old_status=None,
                new_status=dto.status,
                change_source="sync_creation",
                event_id=event_id,
                raw_payload=raw_payload
            )
            self.db.add(hist)
            logger.info(f"Created new installation for order: {dto.order_external_id}")
            
            # Run Postponement Detector for new creations (needed for ChatOps)
            from app.services.postponement_engine import PostponementDetector
            reason_str = raw_payload.get("reason") if raw_payload else None
            postponement = PostponementDetector.detect(hist, raw_reason=reason_str)
            if postponement:
                self.db.add(postponement)
                logger.info(f"Postponement detected for NEW installation {inst.id}: {postponement.reason_category}")
        else:
            # Idempotency check: only create history if something important actually changed
            emp_id = emp.id if emp else None
            changed = False
            
            old_date = inst.scheduled_date
            old_emp_id = inst.employee_id
            old_status = inst.status

            if old_date != dto.scheduled_date or old_emp_id != emp_id or old_status != dto.status:
                changed = True
            
            if changed:
                inst.scheduled_date = dto.scheduled_date
                inst.employee_id = emp_id
                inst.status = dto.status
                inst.actual_date = dto.actual_date
                
                hist = InstallationHistory(
                    installation_id=inst.id,
                    changed_at=datetime.now(timezone.utc),
                    old_date=old_date,
                    new_date=dto.scheduled_date,
                    old_employee_id=old_emp_id,
                    new_employee_id=emp_id,
                    old_status=old_status,
                    new_status=dto.status,
                    change_source="sync_update",
                    event_id=event_id,
                    raw_payload=raw_payload
                )
                self.db.add(hist)
                logger.info(f"Updated installation for order: {dto.order_external_id}. Changes recorded.")
                
                # Run Postponement Detector
                from app.services.postponement_engine import PostponementDetector
                reason_str = raw_payload.get("reason") if raw_payload else None
                postponement = PostponementDetector.detect(hist, raw_reason=reason_str)
                if postponement:
                    self.db.add(postponement)
                    logger.info(f"Postponement detected for installation {inst.id}: {postponement.reason_category}")
            else:
                logger.debug(f"Event {event_id} ignored (idempotency): no changes for order {dto.order_external_id}")
        
        await self.db.flush()
        return inst
