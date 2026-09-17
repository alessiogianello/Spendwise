from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


def make_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_categories(db_session):
    client = make_client(db_session)
    response = client.get("/budgets/categories")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert names == {"Ristoranti", "Spesa", "Trasporti", "Intrattenimento", "Bollette", "Shopping"}
    app.dependency_overrides.clear()


def test_list_budgets(db_session):
    client = make_client(db_session)
    response = client.get("/budgets")
    assert response.status_code == 200
    ristoranti = next(b for b in response.json() if b["category_name"] == "Ristoranti")
    assert ristoranti["amount_limit"] == 150.0
    assert ristoranti["spent"] == 90.0
    app.dependency_overrides.clear()


def test_list_transactions(db_session):
    client = make_client(db_session)
    response = client.get("/transactions")
    assert response.status_code == 200
    assert len(response.json()) == 11
    app.dependency_overrides.clear()


def test_goal_status(db_session):
    client = make_client(db_session)
    response = client.get("/goals/status")
    assert response.status_code == 200
    body = response.json()
    assert body["on_track"] is True
    assert body["margin"] == 90.0
    app.dependency_overrides.clear()
