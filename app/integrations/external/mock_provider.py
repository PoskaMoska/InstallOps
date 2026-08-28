import asyncio
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone

from app.schemas.external import EmployeeDTO, OrderDTO, InstallationDTO
from app.integrations.external.provider import ExternalDataProvider

class MockExternalProvider(ExternalDataProvider):
    """
    Mock implementation of ExternalDataProvider for testing and development
    without a real CRM connection.
    """
    
    async def get_employees(self) -> List[EmployeeDTO]:
        await asyncio.sleep(0.1)  # Simulate network latency
        return [
            EmployeeDTO(external_id="emp-1", name="Иван Иванов", phone="+38000000001", status="active"),
            EmployeeDTO(external_id="emp-2", name="Сергей Сергеев", phone="+38000000002", status="active"),
            EmployeeDTO(external_id="emp-3", name="Алексей Алексеев", phone="+38000000003", status="active"),
        ]

    async def get_orders(self, since: Optional[datetime] = None) -> List[OrderDTO]:
        await asyncio.sleep(0.1)
        now = datetime.now(timezone.utc)
        return [
            OrderDTO(
                external_id="ord-1", 
                client_name="ООО Ромашка", 
                status="new", 
                created_at_external=now
            ),
            OrderDTO(
                external_id="ord-2", 
                client_name="ИП Петров", 
                status="in_progress", 
                created_at_external=now - timedelta(days=1)
            ),
        ]

    async def get_installations(self, since: Optional[datetime] = None) -> List[InstallationDTO]:
        await asyncio.sleep(0.1)
        today = date.today()
        return [
            InstallationDTO(
                external_id="inst-1",
                order_external_id="ord-1",
                employee_external_id="emp-1",
                scheduled_date=today + timedelta(days=2),
                status="scheduled"
            ),
            InstallationDTO(
                external_id="inst-2",
                order_external_id="ord-2",
                employee_external_id="emp-2",
                scheduled_date=today,
                status="in_progress"
            ),
        ]
