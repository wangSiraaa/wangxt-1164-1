from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vessel import Vessel
from app.schemas.vessel import VesselCreate, VesselOut, VesselUpdate

router = APIRouter(prefix="/vessels", tags=["vessels"])


@router.get("/", response_model=list[VesselOut])
def list_vessels(db: Session = Depends(get_db)):
    return db.query(Vessel).all()


@router.post("/", response_model=VesselOut, status_code=201)
def create_vessel(data: VesselCreate, db: Session = Depends(get_db)):
    obj = Vessel(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=VesselOut)
def read_vessel(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(Vessel).filter(Vessel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return obj


@router.put("/{item_id}", response_model=VesselOut)
def update_vessel(item_id: str, data: VesselUpdate, db: Session = Depends(get_db)):
    obj = db.query(Vessel).filter(Vessel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Vessel not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_vessel(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(Vessel).filter(Vessel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Vessel not found")
    db.delete(obj)
    db.commit()
