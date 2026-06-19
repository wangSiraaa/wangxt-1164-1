from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PersonnelBase(BaseModel):
    name: str
    employee_id: str
    role: Literal["maintenance_lead", "captain", "safety_officer", "crew"] = "crew"
    phone: str | None = None


class PersonnelCreate(PersonnelBase):
    pass


class PersonnelUpdate(BaseModel):
    name: str | None = None
    employee_id: str | None = None
    role: Literal["maintenance_lead", "captain", "safety_officer", "crew"] | None = None
    phone: str | None = None


class PersonnelRead(PersonnelBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


PersonnelOut = PersonnelRead
