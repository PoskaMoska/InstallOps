import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Employee, Order, Installation

async def get_employee_by_ext_id(session: AsyncSession, ext_id: str) -> Optional[Employee]:
    result = await session.execute(select(Employee).where(Employee.external_id == ext_id))
    return result.scalars().first()

async def get_employee_by_telegram_id(session: AsyncSession, tg_id: str) -> Optional[Employee]:
    result = await session.execute(select(Employee).where(Employee.telegram_user_id == int(tg_id)))
    return result.scalars().first()

async def get_order_by_ext_id(session: AsyncSession, ext_id: str) -> Optional[Order]:
    result = await session.execute(select(Order).where(Order.external_id == ext_id))
    return result.scalars().first()

async def get_installation_by_ext_id(session: AsyncSession, ext_id: str) -> Optional[Installation]:
    result = await session.execute(select(Installation).where(Installation.external_id == ext_id)) # requires adding external_id to Installation model if not there
    return result.scalars().first()

async def get_installation_by_order_id(session: AsyncSession, order_id: uuid.UUID) -> Optional[Installation]:
    result = await session.execute(select(Installation).where(Installation.order_id == order_id))
    return result.scalars().first()
