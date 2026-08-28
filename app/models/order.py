import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime
from app.db.base_class import Base, TimestampMixin, generate_uuid

class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    created_at_external: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at_external: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    installations = relationship("Installation", back_populates="order")
