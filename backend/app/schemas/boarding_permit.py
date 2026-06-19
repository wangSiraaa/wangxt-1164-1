from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BoardingPersonnelItem(BaseModel):
    personnel_id: str
    role_on_board: str = "crew"


class BoardingPermitCreate(BaseModel):
    permit_code: str
    maintenance_plan_id: str
    vessel_id: str
    boarding_date: datetime
    submitted_by: str
    personnel: list[BoardingPersonnelItem]


class BoardingPermitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    permit_code: str
    maintenance_plan_id: str
    vessel_id: str
    boarding_date: datetime
    status: str
    submitted_by: str | None = None
    captain_id: str | None = None
    captain_confirmed_at: datetime | None = None
    safety_officer_id: str | None = None
    safety_cleared_at: datetime | None = None
    rejection_reason: str | None = None
    personnel: list[BoardingPersonnelItem] = []
    created_at: datetime
    updated_at: datetime


BoardingPermitOut = BoardingPermitRead


class CaptainConfirmRequest(BaseModel):
    captain_id: str


class SafetyClearRequest(BaseModel):
    safety_officer_id: str


class RejectRequest(BaseModel):
    rejection_reason: str
