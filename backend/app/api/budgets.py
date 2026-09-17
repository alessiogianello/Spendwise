from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services import budget_service
from app.schemas import BudgetOut, CategoryOut

router = APIRouter(prefix="/budgets", tags=["budgets"])
settings = get_settings()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return budget_service.list_categories(db, settings.demo_user_id)


@router.get("", response_model=list[BudgetOut])
def list_budgets(month: str | None = None, db: Session = Depends(get_db)):
    month = month or budget_service.current_month()
    statuses = budget_service.all_budget_statuses(db, settings.demo_user_id, month)
    categories = {c.name: c for c in budget_service.list_categories(db, settings.demo_user_id)}
    out = []
    for s in statuses:
        cat = categories[s["category"]]
        budget = budget_service.get_budget(db, settings.demo_user_id, cat.id, month)
        out.append(
            BudgetOut(
                id=budget.id if budget else 0,
                category_id=cat.id,
                category_name=cat.name,
                month=month,
                amount_limit=s["budget_limit"],
                spent=s["spent"],
                remaining=s["remaining"],
            )
        )
    return out
