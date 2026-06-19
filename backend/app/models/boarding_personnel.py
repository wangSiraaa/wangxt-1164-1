import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BoardingPersonnel(Base):
    __tablename__ = "boarding_personnel"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    boarding_permit_id: Mapped[str] = mapped_column(String(36), ForeignKey("boarding_permit.id"), nullable=False)
    personnel_id: Mapped[str] = mapped_column(String(36), ForeignKey("personnel.id"), nullable=False)
    role_on_board: Mapped[str] = mapped_column(String(64), nullable=False, default="crew")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
