import uuid
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Date, Index
from app.db.base_class import Base, TimestampMixin, generate_uuid

class Installation(Base, TimestampMixin):
    __tablename__ = "installations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), index=True, nullable=True)
    
    scheduled_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    order = relationship("Order", back_populates="installations")
    employee = relationship("Employee", back_populates="installations")
    history = relationship("InstallationHistory", back_populates="installation", cascade="all, delete-orphan")
    postponements = relationship("Postponement", back_populates="installation", cascade="all, delete-orphan")
