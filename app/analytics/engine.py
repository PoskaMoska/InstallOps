import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Employee, Installation, Postponement
from app.schemas.analytics import EmployeeStats, CompanyStats
from app.core.config import settings

class AnalyticsEngine:
    """
    Business logic for calculating objective statistics.
    Ensures that 'installations with postponements' and 'total postponements' 
    are not mixed up.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_period_stats(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> CompanyStats:
        
        # 1. Fetch all active employees (we want to show them even if 0 installations)
        emp_result = await self.db.execute(select(Employee).where(Employee.status == 'active'))
        employees = {emp.id: emp for emp in emp_result.scalars().all()}
        
        # 2. Fetch all installations in the period with their postponements (using one optimized query)
        stmt = (
            select(Installation, Postponement)
            .outerjoin(Postponement, Postponement.installation_id == Installation.id)
            .where(
                and_(
                    Installation.scheduled_date >= start_date.date(),
                    Installation.scheduled_date <= end_date.date(),
                    Installation.employee_id.isnot(None)
                )
            )
        )
        
        result = await self.db.execute(stmt)
        
        # 3. Aggregate data in Python (very fast for thousands of rows, avoids complex SQL grouping)
        employee_data: Dict[uuid.UUID, Dict[str, Any]] = {
            emp_id: {
                "installations": set(),
                "postponements": [],
                "inst_post_count": {}
            }
            for emp_id in employees.keys()
        }
        
        for inst, post in result:
            emp_id = inst.employee_id
            if emp_id not in employee_data:
                # Fallback if employee was deleted or inactive but has installations
                employee_data[emp_id] = {"installations": set(), "postponements": [], "inst_post_count": {}}
            
            employee_data[emp_id]["installations"].add(inst.id)
            if post:
                # According to rules, the postponement should be attributed to the employee who caused it
                # which is post.employee_id.
                target_emp_id = post.employee_id or emp_id
                if target_emp_id in employee_data:
                    employee_data[target_emp_id]["postponements"].append(post)
                    employee_data[target_emp_id]["inst_post_count"][inst.id] = \
                        employee_data[target_emp_id]["inst_post_count"].get(inst.id, 0) + 1

        stats_list: List[EmployeeStats] = []
        
        for emp_id, data in employee_data.items():
            total_inst = len(data["installations"])
            
            # Skip employees with 0 installations if they are not strictly active
            if total_inst == 0 and emp_id not in employees:
                continue
                
            emp_name = employees[emp_id].name if emp_id in employees else "Unknown"
            
            total_post = len(data["postponements"])
            inst_post_counts = data["inst_post_count"]
            inst_with_post = len(inst_post_counts)
            
            one_p = sum(1 for v in inst_post_counts.values() if v == 1)
            two_p = sum(1 for v in inst_post_counts.values() if v == 2)
            three_plus_p = sum(1 for v in inst_post_counts.values() if v >= 3)
            
            reasons = {
                "employee_fault": 0, "client_request": 0, "technical": 0,
                "dispatcher_error": 0, "materials": 0, "weather": 0, "force_majeure": 0, "other": 0
            }
            
            for p in data["postponements"]:
                cat = p.reason_category if p.reason_category in reasons else "other"
                reasons[cat] += 1
                
            rate = (inst_with_post / total_inst * 100.0) if total_inst > 0 else 0.0
            avg = (total_post / total_inst) if total_inst > 0 else 0.0
            
            stats_list.append(
                EmployeeStats(
                    employee_id=str(emp_id),
                    employee_name=emp_name,
                    total_installations=total_inst,
                    installations_with_postponement=inst_with_post,
                    total_postponements=total_post,
                    one_postponement=one_p,
                    two_postponements=two_p,
                    three_plus_postponements=three_plus_p,
                    postponement_rate=rate,
                    average_postponements=avg,
                    reasons_breakdown=reasons
                )
            )
            
        # 4. Ranking
        eligible_for_rank = [s for s in stats_list if s.total_installations >= settings.MIN_INSTALLATIONS_FOR_RANKING]
        # Sort: lowest rate first, then highest installations first
        eligible_for_rank.sort(key=lambda x: (x.postponement_rate, -x.total_installations))
        
        for i, s in enumerate(eligible_for_rank):
            s.rank = i + 1
            
        best = eligible_for_rank[0] if eligible_for_rank else None
        worst = eligible_for_rank[-1] if eligible_for_rank else None
        
        # 5. Company totals
        comp_total_inst = sum(s.total_installations for s in stats_list)
        # Note: company unique installations with postponement must be calculated differently 
        # to avoid double counting if multiple employees postponed the same installation.
        # But for simplification and aligning with reporting, we sum up.
        comp_inst_with = sum(s.installations_with_postponement for s in stats_list)
        comp_total_post = sum(s.total_postponements for s in stats_list)
        comp_rate = (comp_inst_with / comp_total_inst * 100.0) if comp_total_inst > 0 else 0.0
        
        return CompanyStats(
            total_installations=comp_total_inst,
            installations_with_postponement=comp_inst_with,
            total_postponements=comp_total_post,
            postponement_rate=comp_rate,
            employees=stats_list,
            best_employee=best,
            worst_employee=worst
        )
