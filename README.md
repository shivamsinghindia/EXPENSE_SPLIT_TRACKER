# Expense Split Tracker (FastAPI)

A production‑ready backend implementing the **Expense Split Tracker** assignment using **FastAPI + SQLAlchemy** with **SQLite** for quick setup (you can switch to Postgres easily).

## Features (Mapped to the Assignment)
- Create groups and invite/add members
- Add expenses with split logic:
  - Equal split
  - Exact amount split
  - Percentage split
- Currency compatibility + conversions (group has a base currency; expenses can be in any currency as long as a rate is provided)
- Track per‑user **net balances** inside a group (positive ⇒ user is owed; negative ⇒ user owes)
- Settle debts (validations prevent settling more than outstanding amount)
- **Debt simplification** (min‑cash‑flow) – preview & apply
- Transaction history with filters (by type, user, date range)
- Postman collection provided in `postman_collection.json`

> This implementation follows the instructions and sample scenarios from the assignment PDF. See the email brief for submission/README/Loom requirements.


## Tech Stack
- Python 3.11+
- FastAPI, Uvicorn
- SQLAlchemy 2.0 ORM
- Pydantic v2
- SQLite (development) – swap to Postgres by changing `DATABASE_URL`

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run API
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open Swagger UI at: http://127.0.0.1:8000/docs

Health check: `GET /` → `{ "status": "ok" }`

## Environment
By default uses a local SQLite file `expense.db` in the project root. To use Postgres, set:
```
export DATABASE_URL=postgresql+psycopg://USER:PASS@HOST:5432/DBNAME
```
(Install `psycopg[binary]` if needed.)

## Data Model (simplified)
- **User**(id, name, email)
- **Group**(id, name, base_currency)
- **GroupMember**(user_id, group_id)
- **CurrencyRate**(base, target, rate, as_of)
- **Expense**(id, group_id, payer_id, amount, currency, split_type, description, created_at)
- **ExpenseSplit**(expense_id, user_id, amount_in_expense_ccy, amount_in_base_ccy)
- **Balance**(group_id, user_id, balance_in_base)  # derived & maintained
- **Settlement**(id, group_id, debtor_id, creditor_id, amount_base, created_at)
- **History**(id, group_id, type, payload, created_at)  # expense/settlement entries

## Core Concepts
- **Balances** are kept **per group** and in the **group's base currency**.
- When adding an expense, we compute conversion from expense currency to group base currency using the latest rate (exact match `base -> target`). You can also set the reverse rate explicitly.
- Split math:
  - Let payer pay the full amount. For each participant's share (in base currency): `balances[user] -= share`.
  - Then credit the payer with the total paid (in base): `balances[payer] += total_in_base`.
  - This naturally yields `net = paid - share` for the payer.
- **Settlement** between a debtor (negative balance) and creditor (positive balance) moves balances, capped by the min of their outstanding amounts.
- **Simplify** computes a minimal set of transfers that would settle the current balances. You can preview or apply the suggestion.

## Postman Collection
Import `postman_collection.json`. The requests are ordered like a mini dashboard:
1. Create user(s)
2. Create group (with base currency)
3. Add members
4. (Optional) POST /rates to add currency rates
5. Add expenses (equal / exact / percentage)
6. GET balances
   - Or GET balances summary: `/groups/{id}/balances/summary` (paid/owed/net per user)
7. POST settlement
8. POST simplify (preview/apply)
9. GET history (filters)

## Tests
Run a small test suite covering split/settlement/simplification:
```bash
pytest -q
```

## Loom
Add your Loom link in this README (replace below):
- Loom: <ADD_YOUR_LINK_HERE>

## Notes
- The app enforces validations for currency, split totals, membership, and settlement bounds.
- You can extend `CurrencyRate` to fetch live FX externally; here it's manual for deterministic tests.
- All endpoints return clear error messages with `HTTPException` and structured payloads.
