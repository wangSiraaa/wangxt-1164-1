from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operation_window import OperationWindow
from app.schemas.operation_window import (
    OperationWindowCreate,
    OperationWindowOut,
    OperationWindowUpdate,
)

router = APIRouter(prefix="/operation-windows", tags=["operation-windows"])


@router.get("/", response_model=list[OperationWindowOut])
def list_operation_windows(db: Session = Depends(get_db)):
    return db.query(OperationWindow).all()


@router.get("/position/{position_id}/active", response_model=list[OperationWindowOut])
def get_active_windows(position_id: str, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return (
        db.query(OperationWindow)
        .filter(
            OperationWindow.work_position_id == position_id,
            OperationWindow.start_time <= now,
            OperationWindow.end_time >= now,
        )
        .all()
    )


@router.post("/", response_model=OperationWindowOut, status_code=201)
def create_operation_window(data: OperationWindowCreate, db: Session = Depends(get_db)):
    obj = OperationWindow(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=OperationWindowOut)
def read_operation_window(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(OperationWindow).filter(OperationWindow.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="OperationWindow not found")
    return obj


@router.put("/{item_id}", response_model=OperationWindowOut)
def update_operation_window(item_id: str, data: OperationWindowUpdate, db: Session = Depends(get_db)):
    obj = db.query(OperationWindow).filter(OperationWindow.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="OperationWindow not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_operation_window(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(OperationWindow).filter(OperationWindow.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="OperationWindow not found")
    db.delete(obj)
    db.commit()
