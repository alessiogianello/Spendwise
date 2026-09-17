from datetime import date, datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str | None = None

    class Config:
        from_attributes = True


class BudgetOut(BaseModel):
    id: int
    category_id: int
    category_name: str
    month: str
    amount_limit: float
    spent: float
    remaining: float

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    category_id: int
    category_name: str
    amount: float
    description: str | None
    date: date
    created_at: datetime

    class Config:
        from_attributes = True


class SavingsGoalOut(BaseModel):
    id: int
    name: str | None
    monthly_target: float

    class Config:
        from_attributes = True
