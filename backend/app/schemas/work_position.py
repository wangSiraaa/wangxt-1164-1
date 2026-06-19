from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class WorkPositionBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    risk_level: Literal["low", "medium", "high"] = "low"
    is_active: bool = True


class WorkPositionCreate(WorkPositionBase):
    pass


class WorkPositionUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    is_active: bool | None = None


class WorkPositionRead(WorkPositionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


WorkPositionOut = WorkPositionRead
