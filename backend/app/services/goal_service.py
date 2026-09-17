from sqlalchemy.orm import Session

from app.models import SavingsGoal
from app.services.budget_service import all_budget_statuses


def set_goal(db: Session, user_id: int, monthly_target: float, name: str | None) -> SavingsGoal:
    if monthly_target < 0:
        raise ValueError("L'obiettivo di risparmio mensile non può essere negativo.")
    goal = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).first()
    if goal is None:
        goal = SavingsGoal(user_id=user_id, monthly_target=monthly_target, name=name)
        db.add(goal)
    else:
        goal.monthly_target = monthly_target
        if name is not None:
            goal.name = name
    db.commit()
    db.refresh(goal)
    return goal


def goal_status(db: Session, user_id: int, month: str) -> dict:
    """Envelope-budgeting view: whatever is budgeted but not yet spent this month
    is money available to save. Comparing that margin to the monthly target tells
    the user whether they're on track."""
    goal = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).first()
    statuses = all_budget_statuses(db, user_id, month)
    total_budgeted = round(sum(s["budget_limit"] for s in statuses), 2)
    total_spent = round(sum(s["spent"] for s in statuses), 2)
    projected_savings = round(total_budgeted - total_spent, 2)

    if goal is None:
        return {
            "has_goal": False,
            "month": month,
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "projected_savings": projected_savings,
        }

    margin = round(projected_savings - goal.monthly_target, 2)
    return {
        "has_goal": True,
        "goal_name": goal.name,
        "month": month,
        "monthly_target": goal.monthly_target,
        "total_budgeted": total_budgeted,
        "total_spent": total_spent,
        "projected_savings": projected_savings,
        "on_track": projected_savings >= goal.monthly_target,
        "margin": margin,
    }
