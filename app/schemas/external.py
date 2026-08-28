from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class EmployeeDTO(BaseModel):
    """Normalized Data Transfer Object for Employee."""
    external_id: str
    name: str
    phone: Optional[str] = None
    status: str = "active"

class OrderDTO(BaseModel):
    """Normalized Data Transfer Object for Order."""
    external_id: str
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    status: str
    created_at_external: Optional[datetime] = None
    updated_at_external: Optional[datetime] = None

class InstallationDTO(BaseModel):
    """Normalized Data Transfer Object for Installation."""
    external_id: Optional[str] = None
    order_external_id: str
    employee_external_id: Optional[str] = None
    scheduled_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: str
