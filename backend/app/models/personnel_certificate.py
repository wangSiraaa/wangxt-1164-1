import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PersonnelCertificate(Base):
    __tablename__ = "personnel_certificate"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    personnel_id: Mapped[str] = mapped_column(String(36), ForeignKey("personnel.id"), nullable=False)
    cert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    cert_number: Mapped[str] = mapped_column(String(128), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    allowed_risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    is_valid: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
