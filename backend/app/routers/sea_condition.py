from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sea_condition import SeaCondition
from app.schemas.sea_condition import SeaConditionCreate, SeaConditionOut, SeaConditionUpdate

router = APIRouter(prefix="/sea-conditions", tags=["sea-conditions"])


@router.get("/", response_model=list[SeaConditionOut])
def list_sea_conditions(db: Session = Depends(get_db)):
    return db.query(SeaCondition).all()


@router.get("/vessel/{vessel_id}/latest", response_model=SeaConditionOut)
def get_latest_sea_condition(vessel_id: str, db: Session = Depends(get_db)):
    obj = (
        db.query(SeaCondition)
        .filter(SeaCondition.vessel_id == vessel_id)
        .order_by(SeaCondition.record_time.desc())
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="No sea condition found for this vessel")
    return obj


@router.post("/", response_model=SeaConditionOut, status_code=201)
def create_sea_condition(data: SeaConditionCreate, db: Session = Depends(get_db)):
    obj = SeaCondition(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=SeaConditionOut)
def read_sea_condition(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(SeaCondition).filter(SeaCondition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="SeaCondition not found")
    return obj


@router.put("/{item_id}", response_model=SeaConditionOut)
def update_sea_condition(item_id: str, data: SeaConditionUpdate, db: Session = Depends(get_db)):
    obj = db.query(SeaCondition).filter(SeaCondition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="SeaCondition not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_sea_condition(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(SeaCondition).filter(SeaCondition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="SeaCondition not found")
    db.delete(obj)
    db.commit()
