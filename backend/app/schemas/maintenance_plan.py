from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MaintenancePlanBase(BaseModel):
    plan_code: str
    title: str
    work_position_id: str
    plan_date: date
    description: str | None = None
    risk_level: Literal["low", "medium", "high"] = "low"
    status: Literal["draft", "submitted", "approved", "completed"] = "draft"
    created_by: str


class MaintenancePlanCreate(MaintenancePlanBase):
    pass


class MaintenancePlanUpdate(BaseModel):
    plan_code: str | None = None
    title: str | None = None
    work_position_id: str | None = None
    plan_date: date | None = None
    description: str | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    status: Literal["draft", "submitted", "approved", "completed"] | None = None
    created_by: str | None = None


class MaintenancePlanRead(MaintenancePlanBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


MaintenancePlanOut = MaintenancePlanRead


class MaintenancePlanStatusUpdate(BaseModel):
    status: Literal["draft", "submitted", "approved", "completed"]
