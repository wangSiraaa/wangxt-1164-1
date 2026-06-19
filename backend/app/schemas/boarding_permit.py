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
    reschedule_suggestion: str | None = None
    suggested_boarding_date: date | None = None
    sea_condition_met: bool | None = None
    capacity_checked: bool | None = None
    life_equipment_checked: bool | None = None
    operation_license_checked: bool | None = None
    life_equipment_count: int | None = None
    operation_license_number: str | None = None
    requires_reapproval: bool | None = None
    reapproval_reason: str | None = None
    personnel_changed: bool | None = None
    personnel: list[BoardingPersonnelItem] = []
    created_at: datetime
    updated_at: datetime


BoardingPermitOut = BoardingPermitRead


class CaptainConfirmRequest(BaseModel):
    captain_id: str
    reschedule_suggestion: str | None = None
    suggested_boarding_date: date | None = None


class CaptainRejectRequest(BaseModel):
    captain_id: str
    rejection_reason: str
    reschedule_suggestion: str | None = None
    suggested_boarding_date: date | None = None


class SafetyClearRequest(BaseModel):
    safety_officer_id: str
    life_equipment_count: int
    operation_license_number: str


class RejectRequest(BaseModel):
    rejection_reason: str


class PersonnelUpdateRequest(BaseModel):
    personnel: list[BoardingPersonnelItem]
    change_reason: str
    updated_by: str


class RescheduleRequest(BaseModel):
    boarding_date: datetime
    reschedule_reason: str
    updated_by: str


class CheckResult(BaseModel):
    passed: bool
    message: str
    details: list[str] = []


class PreCheckResponse(BaseModel):
    certificate_check: CheckResult
    position_risk_check: CheckResult
    same_day_high_risk_check: CheckResult
    all_passed: bool
