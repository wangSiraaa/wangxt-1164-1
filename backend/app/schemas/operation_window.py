from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationWindowBase(BaseModel):
    work_position_id: str
    start_time: datetime
    end_time: datetime
    max_wave_height: float = 1.5
    max_wind_speed: float = 10.0
    min_visibility: float = 1.0


class OperationWindowCreate(OperationWindowBase):
    pass


class OperationWindowUpdate(BaseModel):
    work_position_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_wave_height: float | None = None
    max_wind_speed: float | None = None
    min_visibility: float | None = None


class OperationWindowRead(OperationWindowBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


OperationWindowOut = OperationWindowRead
