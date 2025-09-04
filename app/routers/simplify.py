from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..services.finance import min_cash_flow, upsert_balance, add_history

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/preview", response_model=schemas.SimplifyPreviewOut)
def preview(group_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Group).get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=group_id).all()}
    transfers = [{"from": d, "to": c, "amount": round(a, 2)} for (d, c, a) in min_cash_flow(bals)]
    return {"transfers": transfers}

@router.post("/apply")
def apply(group_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Group).get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=group_id).all()}
    transfers = [{"from": d, "to": c, "amount": round(a, 2)} for (d, c, a) in min_cash_flow(bals)]
                          
    for t in transfers:
        upsert_balance(db, group_id, t["from"], +t["amount"])
        upsert_balance(db, group_id, t["to"], -t["amount"])
    add_history(db, group_id, "settlement", {"auto_simplify": True, "transfers": transfers})
    db.commit()
    return {"message": "Simplification applied", "transfers": transfers}
