import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models
from app.services.finance import split_equal, validate_exact, validate_percent, apply_expense, min_cash_flow, convert
from app.schemas import SettlementIn
from app.routers import settlements as settlements_router
from app.routers import history as history_router

@pytest.fixture
def db():
    engine = create_engine("sqlite://", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

def bootstrap(db):
    u1 = models.User(name="User1", email="u1@example.com")
    u2 = models.User(name="User2", email="u2@example.com")
    u3 = models.User(name="User3", email="u3@example.com")
    db.add_all([u1, u2, u3])
    db.flush()
    g = models.Group(name="Trip", base_currency="USD")
    db.add(g); db.flush()
    for u in (u1,u2,u3):
        db.add(models.GroupMember(group_id=g.id, user_id=u.id))
        db.add(models.Balance(group_id=g.id, user_id=u.id, balance_base=0.0))
                      
    db.add(models.CurrencyRate(base="USD", target="USD", rate=1.0))
    db.commit()
    return g, u1, u2, u3

def test_equal_split(db):
    g, u1, u2, u3 = bootstrap(db)
    shares = split_equal(90.0, [u1.id, u2.id, u3.id])
    assert set(shares.values()) == {30.0}
    apply_expense(db, g, payer_id=u1.id, amount=90.0, currency="USD", shares=shares)
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=g.id).all()}
    assert round(bals[u1.id],2) == 60.00                           
    assert round(bals[u2.id],2) == -30.00
    assert round(bals[u3.id],2) == -30.00

def test_exact_split(db):
    g, u1, u2, _ = bootstrap(db)
    validate_exact(100.0, {u1.id: 70.0, u2.id: 30.0})
    apply_expense(db, g, payer_id=u1.id, amount=100.0, currency="USD", shares={u1.id: 70.0, u2.id: 30.0})
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=g.id).all()}
    assert round(bals[u1.id],2) == 30.00
    assert round(bals[u2.id],2) == -30.00

def test_percentage_split(db):
    g, u1, u2, _ = bootstrap(db)
    validate_percent(200.0, {u1.id: 60.0, u2.id: 40.0})
    apply_expense(db, g, payer_id=u1.id, amount=200.0, currency="USD", shares={u1.id: 120.0, u2.id: 80.0})
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=g.id).all()}
    assert round(bals[u1.id],2) == 80.00
    assert round(bals[u2.id],2) == -80.00

def test_min_cash_flow(db):
    g, u1, u2, u3 = bootstrap(db)
                                      
    b1 = db.query(models.Balance).filter_by(group_id=g.id, user_id=u1.id).first(); b1.balance_base = 50
    b2 = db.query(models.Balance).filter_by(group_id=g.id, user_id=u2.id).first(); b2.balance_base = -30
    b3 = db.query(models.Balance).filter_by(group_id=g.id, user_id=u3.id).first(); b3.balance_base = -20
    db.commit()
    transfers = min_cash_flow({u1.id: 50, u2.id: -30, u3.id: -20})
    assert transfers == [(u2.id, u1.id, 30.0), (u3.id, u1.id, 20.0)]

def test_fx_conversion_and_balances(db):
    g, u1, u2, _ = bootstrap(db)
                                 
    db.add(models.CurrencyRate(base="EUR", target="USD", rate=1.2))
    db.commit()
                                                                                   
    shares = split_equal(120.0, [u1.id, u2.id])
    apply_expense(db, g, payer_id=u1.id, amount=120.0, currency="EUR", shares=shares)
    bals = {b.user_id: b.balance_base for b in db.query(models.Balance).filter_by(group_id=g.id).all()}
    assert round(bals[u1.id], 2) == 72.00                                    
    assert round(bals[u2.id], 2) == -72.00

def test_settlement_and_overpay_guard(db):
    g, u1, u2, _ = bootstrap(db)
                                                
    apply_expense(db, g, payer_id=u1.id, amount=100.0, currency="USD", shares={u1.id: 50.0, u2.id: 50.0})
                                                    
    s = settlements_router.settle(group_id=g.id, data=SettlementIn(debtor_id=u2.id, creditor_id=u1.id, amount_base=30.0), db=db)
    assert s.amount_base == 30.0
    deb = db.query(models.Balance).filter_by(group_id=g.id, user_id=u2.id).first(); assert round(deb.balance_base,2) == -20.00
    cred = db.query(models.Balance).filter_by(group_id=g.id, user_id=u1.id).first(); assert round(cred.balance_base,2) == 20.00
                          
    import pytest
    with pytest.raises(Exception):
        settlements_router.settle(group_id=g.id, data=SettlementIn(debtor_id=u2.id, creditor_id=u1.id, amount_base=25.0), db=db)

def test_simplify_apply_effect(db):
    g, u1, u2, u3 = bootstrap(db)
                                          
    db.query(models.Balance).filter_by(group_id=g.id, user_id=u1.id).first().balance_base = 50
    db.query(models.Balance).filter_by(group_id=g.id, user_id=u2.id).first().balance_base = -30
    db.query(models.Balance).filter_by(group_id=g.id, user_id=u3.id).first().balance_base = -20
    db.commit()
    from app.services.finance import min_cash_flow, upsert_balance
    transfers = min_cash_flow({u1.id: 50, u2.id: -30, u3.id: -20})
    for d, c, a in transfers:
        upsert_balance(db, g.id, d, +a)
        upsert_balance(db, g.id, c, -a)
    db.commit()
    bals = {b.user_id: round(b.balance_base,2) for b in db.query(models.Balance).filter_by(group_id=g.id).all()}
    assert bals[u1.id] == 0.00
    assert bals[u2.id] == 0.00
    assert bals[u3.id] == 0.00

def test_history_filters(db):
    g, u1, u2, _ = bootstrap(db)
                                                                                        
    shares = split_equal(90.0, [u1.id, u2.id])
    apply_expense(db, g, payer_id=u1.id, amount=90.0, currency="USD", shares=shares)
    settlements_router.settle(group_id=g.id, data=SettlementIn(debtor_id=u2.id, creditor_id=u1.id, amount_base=30.0), db=db)
                            
    exps = history_router.get_history(group_id=g.id, type="expense", db=db)
    assert all(r.type == "expense" for r in exps)
                               
    sets = history_router.get_history(group_id=g.id, type="settlement", db=db)
    assert all(r.type == "settlement" for r in sets)
                    
    user_rows = history_router.get_history(group_id=g.id, user_id=u1.id, type=None, db=db)
    assert len(user_rows) >= 1
