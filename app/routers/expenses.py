from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, schemas
from ..services.finance import split_equal, validate_exact, validate_percent, apply_expense, add_history

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

@router.post("/equal", response_model=schemas.ExpenseOut)
def add_equal(group_id: int, data: schemas.ExpenseEqualIn, db: Session = Depends(get_db)):
    group = get_group(db, group_id)
    splits = split_equal(data.amount, data.user_ids)
    exp = models.Expense(group_id=group.id, payer_id=data.payer_id, amount=data.amount, currency=data.currency.upper(), split_type="equal", description=data.description or "")
    db.add(exp); db.flush()
                    
    for uid, share in splits.items():
        db.add(models.ExpenseSplit(expense_id=exp.id, user_id=uid, amount_expense_ccy=share, amount_base_ccy=0.0))                        
                     
    apply_expense(db, group, data.payer_id, data.amount, data.currency.upper(), splits)
    add_history(db, group.id, "expense", {"expense_id": exp.id, "split_type": "equal", "amount": data.amount, "currency": data.currency.upper(), "payer_id": data.payer_id, "participants": data.user_ids, "description": data.description})
    db.commit(); db.refresh(exp)
    return exp

@router.post("/exact", response_model=schemas.ExpenseOut)
def add_exact(group_id: int, data: schemas.ExpenseExactIn, db: Session = Depends(get_db)):
    group = get_group(db, group_id)
    validate_exact(data.amount, data.amounts)
    exp = models.Expense(group_id=group.id, payer_id=data.payer_id, amount=data.amount, currency=data.currency.upper(), split_type="exact", description=data.description or "")
    db.add(exp); db.flush()
    for uid, share in data.amounts.items():
        db.add(models.ExpenseSplit(expense_id=exp.id, user_id=uid, amount_expense_ccy=share, amount_base_ccy=0.0))
    apply_expense(db, group, data.payer_id, data.amount, data.currency.upper(), data.amounts)
    add_history(db, group.id, "expense", {"expense_id": exp.id, "split_type": "exact", "amount": data.amount, "currency": data.currency.upper(), "payer_id": data.payer_id, "amounts": data.amounts, "description": data.description})
    db.commit(); db.refresh(exp)
    return exp

@router.post("/percentage", response_model=schemas.ExpenseOut)
def add_percentage(group_id: int, data: schemas.ExpensePercentIn, db: Session = Depends(get_db)):
    group = get_group(db, group_id)
    validate_percent(data.amount, data.percentages)
    splits = {uid: round(data.amount * pct / 100.0, 10) for uid, pct in data.percentages.items()}
    exp = models.Expense(group_id=group.id, payer_id=data.payer_id, amount=data.amount, currency=data.currency.upper(), split_type="percentage", description=data.description or "")
    db.add(exp); db.flush()
    for uid, share in splits.items():
        db.add(models.ExpenseSplit(expense_id=exp.id, user_id=uid, amount_expense_ccy=share, amount_base_ccy=0.0))
    apply_expense(db, group, data.payer_id, data.amount, data.currency.upper(), splits)
    add_history(db, group.id, "expense", {"expense_id": exp.id, "split_type": "percentage", "amount": data.amount, "currency": data.currency.upper(), "payer_id": data.payer_id, "percentages": data.percentages, "description": data.description})
    db.commit(); db.refresh(exp)
    return exp
