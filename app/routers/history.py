from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import SessionLocal
from .. import models, schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=list[schemas.HistoryOut])
def get_history(group_id: int, user_id: int | None = None, type: str | None = Query(default=None, pattern="^(expense|settlement)$"),
                start: datetime | None = None, end: datetime | None = None, db: Session = Depends(get_db)):
    if not db.query(models.Group).get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    q = db.query(models.History).filter_by(group_id=group_id)
    if type:
        q = q.filter(models.History.type == type)
    if start:
        q = q.filter(models.History.created_at >= start)
    if end:
        q = q.filter(models.History.created_at <= end)
    rows = q.order_by(models.History.created_at.desc()).all()
                                                            
    if user_id is not None:
        filtered = []
        for r in rows:
            p = r.payload or {}
            if (p.get("payer_id") == user_id) or (user_id in p.get("participants", [])) or (user_id in p.get("amounts", {}).keys()) or (p.get("from") == user_id) or (p.get("to") == user_id):
                filtered.append(r)
        rows = filtered
    return rows
