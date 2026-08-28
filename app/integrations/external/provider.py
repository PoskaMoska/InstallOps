from typing import Protocol, List, Optional
from datetime import datetime
from app.schemas.external import EmployeeDTO, OrderDTO, InstallationDTO

class ExternalDataProvider(Protocol):
    """
    Protocol defining the interface for fetching data from an external CRM/ERP.
    Any concrete integration (e.g. AmoCRM, Bitrix24, custom ERP) must implement this.
    """
    
    async def get_employees(self) -> List[EmployeeDTO]:
        """Fetch all employees from the external source."""
        ...

    async def get_orders(self, since: Optional[datetime] = None) -> List[OrderDTO]:
        """Fetch orders, optionally filtering by modified date."""
        ...

    async def get_installations(self, since: Optional[datetime] = None) -> List[InstallationDTO]:
        """Fetch installations, optionally filtering by modified date."""
        ...
