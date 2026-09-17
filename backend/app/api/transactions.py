from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Transaction
from app.schemas import TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])
settings = get_settings()


@router.get("", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == settings.demo_user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )
    return [
        TransactionOut(
            id=t.id,
            category_id=t.category_id,
            category_name=t.category.name,
            amount=t.amount,
            description=t.description,
            date=t.date,
            created_at=t.created_at,
        )
        for t in rows
    ]
