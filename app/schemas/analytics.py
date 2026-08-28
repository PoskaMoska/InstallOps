from pydantic import BaseModel
from typing import List, Dict, Optional

class EmployeeStats(BaseModel):
    employee_id: str
    employee_name: str
    total_installations: int
    installations_with_postponement: int
    total_postponements: int
    
    one_postponement: int
    two_postponements: int
    three_plus_postponements: int
    
    postponement_rate: float
    average_postponements: float
    
    reasons_breakdown: Dict[str, int]
    
    rank: Optional[int] = None
    trend_pp: Optional[float] = None  # Percentage point change vs prev period

class CompanyStats(BaseModel):
    total_installations: int
    installations_with_postponement: int
    total_postponements: int
    postponement_rate: float
    
    employees: List[EmployeeStats]
    best_employee: Optional[EmployeeStats] = None
    worst_employee: Optional[EmployeeStats] = None
