from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=schemas.GroupOut)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    g = models.Group(name=group.name, base_currency=group.base_currency.upper())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g

@router.post("/{group_id}/members")
def add_member(group_id: int, member: schemas.AddMember, db: Session = Depends(get_db)):
    if not db.query(models.Group).get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    if not db.query(models.User).get(member.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if db.query(models.GroupMember).filter_by(group_id=group_id, user_id=member.user_id).first():
        return {"message": "Already a member"}
    m = models.GroupMember(group_id=group_id, user_id=member.user_id)
    db.add(m)
                                    
    if not db.query(models.Balance).filter_by(group_id=group_id, user_id=member.user_id).first():
        db.add(models.Balance(group_id=group_id, user_id=member.user_id, balance_base=0.0))
    db.commit()
    return {"message": "Member added"}
