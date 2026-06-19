from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.personnel_certificate import PersonnelCertificate
from app.schemas.personnel_certificate import (
    PersonnelCertificateCreate,
    PersonnelCertificateOut,
    PersonnelCertificateUpdate,
)

router = APIRouter(prefix="/personnel-certificates", tags=["personnel-certificates"])


@router.get("/", response_model=list[PersonnelCertificateOut])
def list_personnel_certificates(db: Session = Depends(get_db)):
    return db.query(PersonnelCertificate).all()


@router.get("/expired", response_model=list[PersonnelCertificateOut])
def list_expired_certificates(db: Session = Depends(get_db)):
    today = date.today()
    return (
        db.query(PersonnelCertificate)
        .filter(PersonnelCertificate.expiry_date < today)
        .all()
    )


@router.post("/", response_model=PersonnelCertificateOut, status_code=201)
def create_personnel_certificate(data: PersonnelCertificateCreate, db: Session = Depends(get_db)):
    obj = PersonnelCertificate(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=PersonnelCertificateOut)
def read_personnel_certificate(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(PersonnelCertificate).filter(PersonnelCertificate.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="PersonnelCertificate not found")
    return obj


@router.put("/{item_id}", response_model=PersonnelCertificateOut)
def update_personnel_certificate(item_id: str, data: PersonnelCertificateUpdate, db: Session = Depends(get_db)):
    obj = db.query(PersonnelCertificate).filter(PersonnelCertificate.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="PersonnelCertificate not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_personnel_certificate(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(PersonnelCertificate).filter(PersonnelCertificate.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="PersonnelCertificate not found")
    db.delete(obj)
    db.commit()
