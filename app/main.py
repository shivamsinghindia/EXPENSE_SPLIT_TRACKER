from fastapi import FastAPI
from .database import init_db
from .routers import users, groups, rates, expenses, balances, settlements, history, simplify

app = FastAPI(title="Expense Split Tracker API", version="1.0.0")

init_db()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(groups.router, prefix="/groups", tags=["groups"])
app.include_router(rates.router, prefix="/rates", tags=["rates"])
app.include_router(expenses.router, prefix="/groups/{group_id}/expenses", tags=["expenses"])
app.include_router(balances.router, prefix="/groups/{group_id}/balances", tags=["balances"])
app.include_router(settlements.router, prefix="/groups/{group_id}/settlements", tags=["settlements"])
app.include_router(history.router, prefix="/groups/{group_id}/history", tags=["history"])
app.include_router(simplify.router, prefix="/groups/{group_id}/simplify", tags=["simplify"])

@app.get("/")
def health():
    return {"status": "ok"}
