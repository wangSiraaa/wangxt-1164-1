import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BoardingPermit(Base):
    __tablename__ = "boarding_permit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    permit_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    maintenance_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("maintenance_plan.id"), nullable=False)
    vessel_id: Mapped[str] = mapped_column(String(36), ForeignKey("vessel.id"), nullable=False)
    boarding_date: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    submitted_by: Mapped[str | None] = mapped_column(String(64))
    captain_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("personnel.id"))
    captain_confirmed_at: Mapped[datetime | None] = mapped_column()
    safety_officer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("personnel.id"))
    safety_cleared_at: Mapped[datetime | None] = mapped_column()
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
