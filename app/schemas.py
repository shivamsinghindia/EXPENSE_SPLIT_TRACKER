from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Dict, Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class GroupCreate(BaseModel):
    name: str
    base_currency: str = Field(min_length=3, max_length=3, description="ISO code like INR, USD")

class GroupOut(BaseModel):
    id: int
    name: str
    base_currency: str
    model_config = ConfigDict(from_attributes=True)

class AddMember(BaseModel):
    user_id: int

class RateUpsert(BaseModel):
    base: str
    target: str
    rate: float

class ExpenseEqualIn(BaseModel):
    payer_id: int
    amount: float
    currency: str
    description: Optional[str] = "" 
    user_ids: List[int]

class ExpenseExactIn(BaseModel):
    payer_id: int
    amount: float
    currency: str
    description: Optional[str] = "" 
    amounts: Dict[int, float]                     

class ExpensePercentIn(BaseModel):
    payer_id: int
    amount: float
    currency: str
    description: Optional[str] = "" 
    percentages: Dict[int, float]                      

class ExpenseOut(BaseModel):
    id: int
    group_id: int
    payer_id: int
    amount: float
    currency: str
    split_type: str
    description: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BalanceOut(BaseModel):
    user_id: int
    balance_base: float

class SettlementIn(BaseModel):
    debtor_id: int
    creditor_id: int
    amount_base: float

class SettlementOut(BaseModel):
    id: int
    group_id: int
    debtor_id: int
    creditor_id: int
    amount_base: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class HistoryOut(BaseModel):
    id: int
    type: str
    payload: dict
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SimplifyPreviewOut(BaseModel):
    transfers: List[dict]                      
