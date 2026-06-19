from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.work_position import WorkPosition
from app.schemas.work_position import WorkPositionCreate, WorkPositionOut, WorkPositionUpdate

router = APIRouter(prefix="/work-positions", tags=["work-positions"])


@router.get("/", response_model=list[WorkPositionOut])
def list_work_positions(db: Session = Depends(get_db)):
    return db.query(WorkPosition).all()


@router.post("/", response_model=WorkPositionOut, status_code=201)
def create_work_position(data: WorkPositionCreate, db: Session = Depends(get_db)):
    obj = WorkPosition(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=WorkPositionOut)
def read_work_position(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(WorkPosition).filter(WorkPosition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="WorkPosition not found")
    return obj


@router.put("/{item_id}", response_model=WorkPositionOut)
def update_work_position(item_id: str, data: WorkPositionUpdate, db: Session = Depends(get_db)):
    obj = db.query(WorkPosition).filter(WorkPosition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="WorkPosition not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_work_position(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(WorkPosition).filter(WorkPosition.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="WorkPosition not found")
    db.delete(obj)
    db.commit()
