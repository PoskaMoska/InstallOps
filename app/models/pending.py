import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.sql import func
from app.db.base_class import Base, generate_uuid

class PendingEvent(Base):
    __tablename__ = "pending_events"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=generate_uuid)
    
    message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    
    ticket_number: Mapped[str] = mapped_column(String(50), index=True)
    raw_text: Mapped[str] = mapped_column(String)
    extracted_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True) # pending, confirmed, rejected
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
