"""Fresh, deterministic DB per eval case - isolated from the dev spendwise.db."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from seed_data import DEMO_USER_ID, reset_and_seed

EVAL_DB_PATH = os.path.join(os.path.dirname(__file__), "eval_spendwise.db")

EVAL_USER_ID = DEMO_USER_ID


def fresh_eval_session() -> Session:
    engine = create_engine(f"sqlite:///{EVAL_DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    reset_and_seed(session)
    return session
