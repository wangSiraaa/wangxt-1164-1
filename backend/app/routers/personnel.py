from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.personnel import Personnel
from app.schemas.personnel import PersonnelCreate, PersonnelOut, PersonnelUpdate

router = APIRouter(prefix="/personnel", tags=["personnel"])


@router.get("/", response_model=list[PersonnelOut])
def list_personnel(db: Session = Depends(get_db)):
    return db.query(Personnel).all()


@router.post("/", response_model=PersonnelOut, status_code=201)
def create_personnel(data: PersonnelCreate, db: Session = Depends(get_db)):
    obj = Personnel(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{item_id}", response_model=PersonnelOut)
def read_personnel(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(Personnel).filter(Personnel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return obj


@router.put("/{item_id}", response_model=PersonnelOut)
def update_personnel(item_id: str, data: PersonnelUpdate, db: Session = Depends(get_db)):
    obj = db.query(Personnel).filter(Personnel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personnel not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{item_id}", status_code=204)
def delete_personnel(item_id: str, db: Session = Depends(get_db)):
    obj = db.query(Personnel).filter(Personnel.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Personnel not found")
    db.delete(obj)
    db.commit()
