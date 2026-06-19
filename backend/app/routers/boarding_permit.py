from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boarding_permit import BoardingPermit
from app.models.boarding_personnel import BoardingPersonnel
from app.schemas.boarding_permit import (
    BoardingPermitCreate,
    BoardingPermitRead,
    CaptainConfirmRequest,
    RejectRequest,
    SafetyClearRequest,
)
from app.services.boarding_permit import boarding_permit_service

router = APIRouter(prefix="/boarding-permits", tags=["boarding-permits"])


def _to_read(permit: BoardingPermit, db: Session) -> BoardingPermitRead:
    personnel = boarding_permit_service.get_permit_personnel(db, permit.id)
    return BoardingPermitRead(
        id=permit.id,
        permit_code=permit.permit_code,
        maintenance_plan_id=permit.maintenance_plan_id,
        vessel_id=permit.vessel_id,
        boarding_date=permit.boarding_date,
        status=permit.status,
        submitted_by=permit.submitted_by,
        captain_id=permit.captain_id,
        captain_confirmed_at=permit.captain_confirmed_at,
        safety_officer_id=permit.safety_officer_id,
        safety_cleared_at=permit.safety_cleared_at,
        rejection_reason=permit.rejection_reason,
        personnel=personnel,
        created_at=permit.created_at,
        updated_at=permit.updated_at,
    )


@router.get("/", response_model=List[BoardingPermitRead])
def list_permits(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(BoardingPermit)
    if status:
        q = q.filter(BoardingPermit.status == status)
    permits = q.order_by(BoardingPermit.created_at.desc()).all()
    return [_to_read(p, db) for p in permits]


@router.post("/", response_model=BoardingPermitRead, status_code=201)
def create_permit(data: BoardingPermitCreate, db: Session = Depends(get_db)):
    permit = boarding_permit_service.create_permit(db, data)
    return _to_read(permit, db)


@router.get("/{permit_id}", response_model=BoardingPermitRead)
def get_permit(permit_id: str, db: Session = Depends(get_db)):
    permit = db.query(BoardingPermit).filter(BoardingPermit.id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="登乘许可不存在")
    return _to_read(permit, db)


@router.post("/{permit_id}/captain-confirm", response_model=BoardingPermitRead)
def captain_confirm(permit_id: str, req: CaptainConfirmRequest, db: Session = Depends(get_db)):
    permit = boarding_permit_service.captain_confirm(db, permit_id, req)
    return _to_read(permit, db)


@router.post("/{permit_id}/safety-clear", response_model=BoardingPermitRead)
def safety_clear(permit_id: str, req: SafetyClearRequest, db: Session = Depends(get_db)):
    permit = boarding_permit_service.safety_clear(db, permit_id, req)
    return _to_read(permit, db)


@router.post("/{permit_id}/reject", response_model=BoardingPermitRead)
def reject_permit(permit_id: str, req: RejectRequest, db: Session = Depends(get_db)):
    permit = boarding_permit_service.reject(db, permit_id, req)
    return _to_read(permit, db)
