from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .. import models

def get_rate(db: Session, base: str, target: str) -> float:
    if base == target:
        return 1.0
    fx = db.query(models.CurrencyRate).filter_by(base=base, target=target).first()
    if not fx:
        raise HTTPException(status_code=400, detail=f"Missing FX rate {base}->{target}. Add via /rates.")
    return fx.rate

def convert(db: Session, amount: float, src: str, dst: str) -> float:
    rate = get_rate(db, base=src, target=dst)
    return amount * rate

def ensure_member(db: Session, group_id: int, user_id: int):
    if not db.query(models.GroupMember).filter_by(group_id=group_id, user_id=user_id).first():
        raise HTTPException(status_code=404, detail=f"User {user_id} is not a member of group {group_id}")

def upsert_balance(db: Session, group_id: int, user_id: int, delta: float):
    bal = db.query(models.Balance).filter_by(group_id=group_id, user_id=user_id).first()
    if not bal:
        bal = models.Balance(group_id=group_id, user_id=user_id, balance_base=0.0)
        db.add(bal)
        db.flush()
    bal.balance_base = round(bal.balance_base + delta, 10)                      
    return bal

def add_history(db: Session, group_id: int, type_: str, payload: dict):
    h = models.History(group_id=group_id, type=type_, payload=payload)
    db.add(h)
    return h

def split_equal(amount: float, participants: List[int]) -> Dict[int, float]:
    if not participants:
        raise HTTPException(status_code=400, detail="Participants cannot be empty.")
    per = round(amount / len(participants), 10)
                                             
    shares = {u: per for u in participants}
    total_assigned = per * len(participants)
    residue = round(amount - total_assigned, 10)
    if residue != 0:
        last = participants[-1]
        shares[last] = round(shares[last] + residue, 10)
    return shares

def validate_exact(amount: float, amounts: Dict[int, float]):
    s = round(sum(amounts.values()), 10)
    if s != round(amount, 10):
        raise HTTPException(status_code=400, detail=f"Exact amounts sum ({s}) must equal total ({amount}).")    

def validate_percent(amount: float, percentages: Dict[int, float]):
    s = round(sum(percentages.values()), 10)
    if s != 100.0:
        raise HTTPException(status_code=400, detail=f"Percentages must sum to 100, got {s}.")

def apply_expense(db: Session, group: models.Group, payer_id: int, amount: float, currency: str, shares: Dict[int, float]):
                                      
    for uid in shares.keys():
        ensure_member(db, group.id, uid)
    ensure_member(db, group.id, payer_id)

    \
    total_in_base = convert(db, amount, currency, group.base_currency)

    \
    for uid, share in shares.items():
        share_base = convert(db, share, currency, group.base_currency)
        upsert_balance(db, group.id, uid, -share_base)

    upsert_balance(db, group.id, payer_id, total_in_base)

def min_cash_flow(balances: Dict[int, float]) -> List[Tuple[int, int, float]]:
                                                                                 
    creditors = [(u, amt) for u, amt in balances.items() if amt > 1e-9]
    debtors = [(u, -amt) for u, amt in balances.items() if amt < -1e-9]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    i = j = 0
    transfers = []
    while i < len(debtors) and j < len(creditors):
        d_id, d_amt = debtors[i]
        c_id, c_amt = creditors[j]
        pay = round(min(d_amt, c_amt), 10)
        transfers.append((d_id, c_id, pay))
        d_amt = round(d_amt - pay, 10)
        c_amt = round(c_amt - pay, 10)
        if d_amt <= 1e-9:
            i += 1
        else:
            debtors[i] = (d_id, d_amt)
        if c_amt <= 1e-9:
            j += 1
        else:
            creditors[j] = (c_id, c_amt)
    return transfers
