from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services import budget_service, goal_service

router = APIRouter(prefix="/goals", tags=["goals"])
settings = get_settings()


@router.get("/status")
def goal_status(month: str | None = None, db: Session = Depends(get_db)):
    month = month or budget_service.current_month()
    return goal_service.goal_status(db, settings.demo_user_id, month)
