from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PersonnelCertificateBase(BaseModel):
    personnel_id: str
    cert_type: str
    cert_number: str
    issue_date: date
    expiry_date: date
    is_valid: bool = True


class PersonnelCertificateCreate(PersonnelCertificateBase):
    pass


class PersonnelCertificateUpdate(BaseModel):
    personnel_id: str | None = None
    cert_type: str | None = None
    cert_number: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    is_valid: bool | None = None


class PersonnelCertificateRead(PersonnelCertificateBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


PersonnelCertificateOut = PersonnelCertificateRead
