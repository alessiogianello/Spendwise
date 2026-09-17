"""Deterministic demo/fixture data. Used both for local manual testing and to
reset the DB to a known state before each offline eval case."""

import json
from datetime import date

from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import (
    Budget,
    Category,
    CategoryTransfer,
    ConversationMessage,
    ConversationSession,
    SavingsGoal,
    Transaction,
    User,
    UserPreference,
)

DEMO_USER_ID = 1
DEMO_EMAIL = "demo@spendwise.app"

CATEGORY_NAMES = ["Ristoranti", "Spesa", "Trasporti", "Intrattenimento", "Bollette", "Shopping"]

# amount_limit per category for the seeded month
BUDGETS = {
    "Ristoranti": 150.0,
    "Spesa": 400.0,
    "Trasporti": 100.0,
    "Intrattenimento": 80.0,
    "Bollette": 200.0,
    "Shopping": 100.0,
}

# (category, amount, day_of_month, description) - day_of_month is clamped to
# today's day so every seeded transaction always lands in the *current* month,
# regardless of what day of the month the seed script runs on.
TRANSACTIONS = [
    ("Ristoranti", 35.0, 3, "Cena fuori"),
    ("Ristoranti", 30.0, 8, "Pranzo di lavoro"),
    ("Ristoranti", 25.0, 14, "Pizza"),
    ("Spesa", 120.0, 2, "Spesa settimanale"),
    ("Spesa", 90.0, 9, "Spesa settimanale"),
    ("Spesa", 40.0, 15, "Spesa settimanale"),
    ("Trasporti", 40.0, 5, "Abbonamento mezzi"),
    ("Intrattenimento", 30.0, 6, "Cinema"),
    ("Intrattenimento", 30.0, 12, "Concerto"),
    ("Bollette", 180.0, 1, "Bollette luce e gas"),
    ("Shopping", 20.0, 10, "Scarpe"),
]

SAVINGS_GOAL_MONTHLY_TARGET = 300.0

PREFERENCES = {
    "cost_cutting_priority": ["Intrattenimento", "Shopping", "Ristoranti"],
    "habitual_categories": ["Ristoranti", "Spesa"],
}


def reset_and_seed(db: Session) -> None:
    for model in [
        ConversationMessage,
        ConversationSession,
        CategoryTransfer,
        Transaction,
        Budget,
        SavingsGoal,
        UserPreference,
        Category,
        User,
    ]:
        db.query(model).delete()
    db.commit()

    user = User(id=DEMO_USER_ID, email=DEMO_EMAIL, name="Utente Demo")
    db.add(user)
    db.flush()

    categories = {}
    for name in CATEGORY_NAMES:
        cat = Category(user_id=user.id, name=name, is_default=True)
        db.add(cat)
        db.flush()
        categories[name] = cat

    month = date.today().strftime("%Y-%m")
    for name, limit in BUDGETS.items():
        db.add(Budget(user_id=user.id, category_id=categories[name].id, month=month, amount_limit=limit))

    today = date.today()
    for name, amount, day_of_month, desc in TRANSACTIONS:
        db.add(
            Transaction(
                user_id=user.id,
                category_id=categories[name].id,
                amount=amount,
                description=desc,
                date=today.replace(day=min(day_of_month, today.day)),
            )
        )

    db.add(SavingsGoal(user_id=user.id, name="Risparmio mensile", monthly_target=SAVINGS_GOAL_MONTHLY_TARGET))

    for key, value in PREFERENCES.items():
        db.add(UserPreference(user_id=user.id, key=key, value_json=json.dumps(value, ensure_ascii=False)))

    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reset_and_seed(db)
        print("Database seeded.")
    finally:
        db.close()
