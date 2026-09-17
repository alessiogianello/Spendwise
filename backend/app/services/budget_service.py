from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Budget, Category, Transaction


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def get_category(db: Session, user_id: int, name: str) -> Category:
    category = (
        db.query(Category)
        .filter(Category.user_id == user_id, func.lower(Category.name) == name.strip().lower())
        .first()
    )
    if category is None:
        available = [c.name for c in db.query(Category).filter(Category.user_id == user_id).all()]
        raise ValueError(
            f"Categoria '{name}' non trovata. Categorie disponibili: {', '.join(available)}."
        )
    return category


def list_categories(db: Session, user_id: int) -> list[Category]:
    return db.query(Category).filter(Category.user_id == user_id).order_by(Category.name).all()


def get_budget(db: Session, user_id: int, category_id: int, month: str) -> Budget | None:
    return (
        db.query(Budget)
        .filter(Budget.user_id == user_id, Budget.category_id == category_id, Budget.month == month)
        .first()
    )


def spent_in_category(db: Session, user_id: int, category_id: int, month: str) -> float:
    total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            func.strftime("%Y-%m", Transaction.date) == month,
        )
        .scalar()
    )
    return float(total)


def budget_status(db: Session, user_id: int, category: Category, month: str) -> dict:
    budget = get_budget(db, user_id, category.id, month)
    limit = budget.amount_limit if budget else 0.0
    spent = spent_in_category(db, user_id, category.id, month)
    remaining = limit - spent
    percent_used = round((spent / limit * 100), 1) if limit > 0 else None
    return {
        "category": category.name,
        "month": month,
        "budget_limit": round(limit, 2),
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "percent_used": percent_used,
        "has_budget": budget is not None,
    }


def all_budget_statuses(db: Session, user_id: int, month: str) -> list[dict]:
    return [budget_status(db, user_id, c, month) for c in list_categories(db, user_id)]


def add_expense(
    db: Session,
    user_id: int,
    category: Category,
    amount: float,
    description: str | None,
    expense_date: date,
) -> Transaction:
    if amount <= 0:
        raise ValueError("L'importo di una spesa deve essere positivo.")
    txn = Transaction(
        user_id=user_id,
        category_id=category.id,
        amount=amount,
        description=description,
        date=expense_date,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def upsert_budget(db: Session, user_id: int, category: Category, amount_limit: float, month: str) -> Budget:
    if amount_limit < 0:
        raise ValueError("Il budget non può essere negativo.")
    budget = get_budget(db, user_id, category.id, month)
    if budget is None:
        budget = Budget(user_id=user_id, category_id=category.id, month=month, amount_limit=amount_limit)
        db.add(budget)
    else:
        budget.amount_limit = amount_limit
    db.commit()
    db.refresh(budget)
    return budget


def move_funds(
    db: Session,
    user_id: int,
    from_category: Category,
    to_category: Category,
    amount: float,
    month: str,
    reason: str | None,
) -> dict:
    if amount <= 0:
        raise ValueError("L'importo da spostare deve essere positivo.")
    if from_category.id == to_category.id:
        raise ValueError("La categoria di partenza e di arrivo non possono coincidere.")

    from_budget = get_budget(db, user_id, from_category.id, month)
    from_limit = from_budget.amount_limit if from_budget else 0.0
    if amount > from_limit:
        raise ValueError(
            f"Il budget di '{from_category.name}' per {month} è di {from_limit:.2f}€: "
            f"non puoi spostarne {amount:.2f}€."
        )

    from_budget.amount_limit = from_limit - amount
    to_budget = get_budget(db, user_id, to_category.id, month)
    if to_budget is None:
        to_budget = Budget(user_id=user_id, category_id=to_category.id, month=month, amount_limit=amount)
        db.add(to_budget)
    else:
        to_budget.amount_limit += amount

    from app.models import CategoryTransfer

    transfer = CategoryTransfer(
        user_id=user_id,
        from_category_id=from_category.id,
        to_category_id=to_category.id,
        amount=amount,
        month=month,
        reason=reason,
    )
    db.add(transfer)
    db.commit()
    db.refresh(from_budget)
    db.refresh(to_budget)
    return {
        "from_category": from_category.name,
        "to_category": to_category.name,
        "amount": amount,
        "from_category_new_limit": round(from_budget.amount_limit, 2),
        "to_category_new_limit": round(to_budget.amount_limit, 2),
    }
