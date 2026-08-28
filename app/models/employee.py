import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from sqlalchemy import String, BigInteger
from app.db.base_class import Base, TimestampMixin, generate_uuid

class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    installations = relationship("Installation", back_populates="employee")
