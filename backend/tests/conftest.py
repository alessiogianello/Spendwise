import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from seed_data import reset_and_seed


@pytest.fixture()
def db_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = TestingSessionLocal()
    reset_and_seed(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.remove(path)
