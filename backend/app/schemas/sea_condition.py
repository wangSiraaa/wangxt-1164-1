from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SeaConditionBase(BaseModel):
    vessel_id: str
    record_time: datetime
    wave_height: float
    wind_speed: float
    visibility: float
    sea_state: Literal["calm", "slight", "moderate", "rough", "very_rough"] = "calm"
    is_navigable: bool = True
    recorder_name: str


class SeaConditionCreate(SeaConditionBase):
    pass


class SeaConditionUpdate(BaseModel):
    vessel_id: str | None = None
    record_time: datetime | None = None
    wave_height: float | None = None
    wind_speed: float | None = None
    visibility: float | None = None
    sea_state: Literal["calm", "slight", "moderate", "rough", "very_rough"] | None = None
    is_navigable: bool | None = None
    recorder_name: str | None = None


class SeaConditionRead(SeaConditionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


SeaConditionOut = SeaConditionRead
