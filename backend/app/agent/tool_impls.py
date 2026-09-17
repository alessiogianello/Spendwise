from datetime import date, datetime

from sqlalchemy.orm import Session

from app.agent.memory import get_preferences, set_preference
from app.services import budget_service, goal_service


def _month(value: str | None) -> str:
    return value or budget_service.current_month()


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _list_categories(db: Session, user_id: int, **_) -> dict:
    cats = budget_service.list_categories(db, user_id)
    return {"categories": [{"id": c.id, "name": c.name} for c in cats]}


def _get_monthly_spending(db: Session, user_id: int, category: str | None = None, month: str | None = None, **_) -> dict:
    month = _month(month)
    if category:
        cat = budget_service.get_category(db, user_id, category)
        spent = budget_service.spent_in_category(db, user_id, cat.id, month)
        return {"month": month, "category": cat.name, "total_spent": round(spent, 2)}
    breakdown = [
        {"category": c.name, "spent": round(budget_service.spent_in_category(db, user_id, c.id, month), 2)}
        for c in budget_service.list_categories(db, user_id)
    ]
    return {
        "month": month,
        "total_spent": round(sum(b["spent"] for b in breakdown), 2),
        "breakdown": breakdown,
    }


def _get_budget_status(db: Session, user_id: int, category: str | None = None, month: str | None = None, **_) -> dict:
    month = _month(month)
    if category:
        cat = budget_service.get_category(db, user_id, category)
        return budget_service.budget_status(db, user_id, cat, month)
    return {"month": month, "categories": budget_service.all_budget_statuses(db, user_id, month)}


def _get_savings_goal_status(db: Session, user_id: int, month: str | None = None, **_) -> dict:
    return goal_service.goal_status(db, user_id, _month(month))


def _get_user_preferences(db: Session, user_id: int, **_) -> dict:
    return {"preferences": get_preferences(db, user_id)}


def _add_expense(
    db: Session,
    user_id: int,
    category: str,
    amount: float,
    description: str | None = None,
    date: str | None = None,
    **_,
) -> dict:
    cat = budget_service.get_category(db, user_id, category)
    txn = budget_service.add_expense(db, user_id, cat, amount, description, _parse_date(date))
    status = budget_service.budget_status(db, user_id, cat, txn.date.strftime("%Y-%m"))
    return {
        "transaction_id": txn.id,
        "category": cat.name,
        "amount": txn.amount,
        "date": txn.date.isoformat(),
        "category_remaining_after": status["remaining"],
    }


def _create_or_update_budget(
    db: Session, user_id: int, category: str, amount_limit: float, month: str | None = None, **_
) -> dict:
    cat = budget_service.get_category(db, user_id, category)
    budget = budget_service.upsert_budget(db, user_id, cat, amount_limit, _month(month))
    return {"budget_id": budget.id, "category": cat.name, "month": budget.month, "amount_limit": budget.amount_limit}


def _set_savings_goal(db: Session, user_id: int, monthly_target: float, name: str | None = None, **_) -> dict:
    goal = goal_service.set_goal(db, user_id, monthly_target, name)
    return {"goal_id": goal.id, "name": goal.name, "monthly_target": goal.monthly_target}


def _move_funds_between_categories(
    db: Session,
    user_id: int,
    from_category: str,
    to_category: str,
    amount: float,
    month: str | None = None,
    reason: str | None = None,
    **_,
) -> dict:
    from_cat = budget_service.get_category(db, user_id, from_category)
    to_cat = budget_service.get_category(db, user_id, to_category)
    return budget_service.move_funds(db, user_id, from_cat, to_cat, amount, _month(month), reason)


def _update_user_preference(db: Session, user_id: int, key: str, value: str, **_) -> dict:
    return set_preference(db, user_id, key, value)


TOOL_IMPLS = {
    "list_categories": _list_categories,
    "get_monthly_spending": _get_monthly_spending,
    "get_budget_status": _get_budget_status,
    "get_savings_goal_status": _get_savings_goal_status,
    "get_user_preferences": _get_user_preferences,
    "add_expense": _add_expense,
    "create_or_update_budget": _create_or_update_budget,
    "set_savings_goal": _set_savings_goal,
    "move_funds_between_categories": _move_funds_between_categories,
    "update_user_preference": _update_user_preference,
}


def execute_tool(db: Session, user_id: int, name: str, tool_input: dict) -> dict:
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        raise ValueError(f"Tool sconosciuto: {name}")
    return impl(db, user_id, **tool_input)
