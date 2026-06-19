import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
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
    submitted_by: Mapped[Optional[str]] = mapped_column(String(64))
    captain_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("personnel.id"))
    captain_confirmed_at: Mapped[Optional[datetime]] = mapped_column()
    safety_officer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("personnel.id"))
    safety_cleared_at: Mapped[Optional[datetime]] = mapped_column()
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    reschedule_suggestion: Mapped[Optional[str]] = mapped_column(Text)
    suggested_boarding_date: Mapped[Optional[date]] = mapped_column(Date)
    sea_condition_met: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    capacity_checked: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    life_equipment_checked: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    operation_license_checked: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    life_equipment_count: Mapped[Optional[int]] = mapped_column(Integer)
    operation_license_number: Mapped[Optional[str]] = mapped_column(String(128))
    requires_reapproval: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    reapproval_reason: Mapped[Optional[str]] = mapped_column(Text)
    personnel_changed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
