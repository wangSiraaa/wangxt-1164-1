from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VesselBase(BaseModel):
    name: str
    code: str
    capacity: int = 12
    vessel_type: str = "transfer"
    status: str = "active"


class VesselCreate(VesselBase):
    pass


class VesselUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    capacity: int | None = None
    vessel_type: str | None = None
    status: str | None = None


class VesselRead(VesselBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


VesselOut = VesselRead
