import uuid
from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Date, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base, generate_uuid

class Postponement(Base):
    __tablename__ = "postponements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    installation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"), index=True, nullable=False)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), index=True, nullable=True)
    
    old_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    installation = relationship("Installation", back_populates="postponements")
