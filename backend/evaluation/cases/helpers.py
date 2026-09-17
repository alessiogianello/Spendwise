import json

from sqlalchemy.orm import Session

from app.models import Budget, Category, SavingsGoal, Transaction, UserPreference
from evaluation.fixtures import EVAL_USER_ID


def approx(actual: float, expected: float, tol: float = 0.01) -> bool:
    return abs(actual - expected) <= tol


def get_budget_limit(db: Session, category_name: str, month: str) -> float | None:
    row = (
        db.query(Budget)
        .join(Category, Budget.category_id == Category.id)
        .filter(Budget.user_id == EVAL_USER_ID, Category.name == category_name, Budget.month == month)
        .first()
    )
    return row.amount_limit if row else None


def count_transactions(db: Session) -> int:
    return db.query(Transaction).filter(Transaction.user_id == EVAL_USER_ID).count()


def transaction_exists(db: Session, category_name: str, amount: float) -> bool:
    row = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == EVAL_USER_ID,
            Category.name == category_name,
            Transaction.amount == amount,
        )
        .first()
    )
    return row is not None


def category_count(db: Session) -> int:
    return db.query(Category).filter(Category.user_id == EVAL_USER_ID).count()


def savings_goal_target(db: Session) -> float | None:
    row = db.query(SavingsGoal).filter(SavingsGoal.user_id == EVAL_USER_ID).first()
    return row.monthly_target if row else None


def preference_value(db: Session, key: str):
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == EVAL_USER_ID, UserPreference.key == key)
        .first()
    )
    if row is None:
        return None
    try:
        return json.loads(row.value_json)
    except json.JSONDecodeError:
        return row.value_json
