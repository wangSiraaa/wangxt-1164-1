from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.maintenance_plan import MaintenancePlan
from app.schemas.maintenance_plan import (
    MaintenancePlanCreate,
    MaintenancePlanOut,
    MaintenancePlanStatusUpdate,
    MaintenancePlanUpdate,
)

VALID_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"approved"},
    "approved": {"completed"},
    "completed": set(),
}

router = APIRouter(prefix="/maintenance-plans", tags=["maintenance-plans"])


@router.get("/", response_model=list[MaintenancePlanOut])
def list_maintenance_plans(db: Session = Depends(get_db)):
    return db.query(MaintenancePlan).all()


@router.post("/", response_model=MaintenancePlanOut, status_code=201)
def create_maintenance_plan(data: MaintenancePlanCreate, db: Session = Depends(get_db)):
    obj = MaintenancePlan(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=MaintenancePlanOut)
def read_maintenance_plan(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(MaintenancePlan).filter(MaintenancePlan.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="MaintenancePlan not found")
    return obj


@router.put("/{item_id}", response_model=MaintenancePlanOut)
def update_maintenance_plan(item_id: str, data: MaintenancePlanUpdate, db: Session = Depends(get_db)):
    obj = db.query(MaintenancePlan).filter(MaintenancePlan.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="MaintenancePlan not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_maintenance_plan(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(MaintenancePlan).filter(MaintenancePlan.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="MaintenancePlan not found")
    db.delete(obj)
    db.commit()


@router.patch("/{item_id}/status", response_model=MaintenancePlanOut)
def update_plan_status(item_id: str, data: MaintenancePlanStatusUpdate, db: Session = Depends(get_db)):
    obj = db.query(MaintenancePlan).filter(MaintenancePlan.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="MaintenancePlan not found")
    new_status = data.status
    allowed = VALID_TRANSITIONS.get(obj.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition from '{obj.status}' to '{new_status}'. "
            f"Allowed transitions: {sorted(allowed) if allowed else 'none'}",
        )
    obj.status = new_status
    db.commit()
    db.refresh(obj)
    return obj
