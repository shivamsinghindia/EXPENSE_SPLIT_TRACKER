from fastapi import APIRouter, Depends
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

@router.post("")
def upsert_rate(rate: schemas.RateUpsert, db: Session = Depends(get_db)):
    base = rate.base.upper()
    target = rate.target.upper()
    fx = db.query(models.CurrencyRate).filter_by(base=base, target=target).first()
    if fx:
        fx.rate = rate.rate
    else:
        fx = models.CurrencyRate(base=base, target=target, rate=rate.rate)
        db.add(fx)
    db.commit()
    return {"message": "Rate upserted", "base": base, "target": target, "rate": rate.rate}
