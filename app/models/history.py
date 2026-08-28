import uuid
from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Date, DateTime, JSON
from app.db.base_class import Base, generate_uuid

class InstallationHistory(Base):
    __tablename__ = "installation_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    installation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("installations.id", ondelete="CASCADE"), index=True, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    old_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    old_employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    new_employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    change_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    installation = relationship("Installation", back_populates="history")
