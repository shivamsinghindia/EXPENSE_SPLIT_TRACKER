from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..services.finance import ensure_member, upsert_balance, add_history

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_group(db: Session, group_id: int) -> models.Group:
    g = db.query(models.Group).get(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return g

@router.post("", response_model=schemas.SettlementOut)
def settle(group_id: int, data: schemas.SettlementIn, db: Session = Depends(get_db)):
    group = get_group(db, group_id)
    ensure_member(db, group.id, data.debtor_id)
    ensure_member(db, group.id, data.creditor_id)
    if data.debtor_id == data.creditor_id:
        raise HTTPException(status_code=400, detail="Cannot settle with self.")
                    
    deb = db.query(models.Balance).filter_by(group_id=group_id, user_id=data.debtor_id).first()
    cred = db.query(models.Balance).filter_by(group_id=group_id, user_id=data.creditor_id).first()
    deb_amt = deb.balance_base if deb else 0.0
    cred_amt = cred.balance_base if cred else 0.0
    if deb_amt >= 0:
        raise HTTPException(status_code=400, detail="Debtor does not owe.")
    if cred_amt <= 0:
        raise HTTPException(status_code=400, detail="Creditor is not owed.")
    max_pay = min(-deb_amt, cred_amt)
    if data.amount_base - max_pay > 1e-9:
        raise HTTPException(status_code=400, detail=f"Cannot settle more than outstanding ({max_pay}).")

    s = models.Settlement(group_id=group_id, debtor_id=data.debtor_id, creditor_id=data.creditor_id, amount_base=data.amount_base)
    db.add(s)
                   
    upsert_balance(db, group_id, data.debtor_id, +data.amount_base)                    
    upsert_balance(db, group_id, data.creditor_id, -data.amount_base)                         
    add_history(db, group_id, "settlement", {"settlement_id": None, "from": data.debtor_id, "to": data.creditor_id, "amount_base": data.amount_base})
    db.commit(); db.refresh(s)
    return s
