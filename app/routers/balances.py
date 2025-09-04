from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..services.finance import convert

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=list[schemas.BalanceOut])
def get_balances(group_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Group).get(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    rows = db.query(models.Balance).filter_by(group_id=group_id).all()
    return [schemas.BalanceOut(user_id=r.user_id, balance_base=round(r.balance_base, 2)) for r in rows]

@router.get("/summary")
def get_balance_summary(group_id: int, db: Session = Depends(get_db)):
    group = db.query(models.Group).get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
                        
    members = [m.user_id for m in db.query(models.GroupMember).filter_by(group_id=group_id).all()]
    paid_total: dict[int, float] = {uid: 0.0 for uid in members}
    owed_total: dict[int, float] = {uid: 0.0 for uid in members}

    \
    exps = db.query(models.Expense).filter_by(group_id=group_id).all()
    if exps:
        exp_id_to_exp = {e.id: e for e in exps}
                      
        for e in exps:
            paid_total[e.payer_id] = round(paid_total.get(e.payer_id, 0.0) + convert(db, e.amount, e.currency, group.base_currency), 10)
                                
        splits = db.query(models.ExpenseSplit).filter(models.ExpenseSplit.expense_id.in_(list(exp_id_to_exp.keys()))).all()
        for s in splits:
            e = exp_id_to_exp.get(s.expense_id)
            if e is None:
                continue
            base = convert(db, s.amount_expense_ccy, e.currency, group.base_currency)
            owed_total[s.user_id] = round(owed_total.get(s.user_id, 0.0) + base, 10)

    summary = []
    for uid in set(list(paid_total.keys()) + list(owed_total.keys()) + members):
        net_row = db.query(models.Balance).filter_by(group_id=group_id, user_id=uid).first()
        net = round(net_row.balance_base, 2) if net_row else 0.0
        summary.append({
            "user_id": uid,
            "paid_total": round(paid_total.get(uid, 0.0), 2),
            "owed_total": round(owed_total.get(uid, 0.0), 2),
            "net": net,
            "currency": group.base_currency,
        })
    return {"group_id": group_id, "base_currency": group.base_currency, "users": summary}
