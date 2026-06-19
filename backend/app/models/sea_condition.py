import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SeaCondition(Base):
    __tablename__ = "sea_condition"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vessel_id: Mapped[str] = mapped_column(String(36), ForeignKey("vessel.id"), nullable=False)
    record_time: Mapped[datetime] = mapped_column(nullable=False)
    wave_height: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed: Mapped[float] = mapped_column(Float, nullable=False)
    visibility: Mapped[float] = mapped_column(Float, nullable=False)
    sea_state: Mapped[str] = mapped_column(String(32), nullable=False, default="calm")
    is_navigable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recorder_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
