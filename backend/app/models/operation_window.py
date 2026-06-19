import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OperationWindow(Base):
    __tablename__ = "operation_window"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_position_id: Mapped[str] = mapped_column(String(36), ForeignKey("work_position.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=False)
    max_wave_height: Mapped[float] = mapped_column(Float, nullable=False, default=1.5)
    max_wind_speed: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    min_visibility: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
