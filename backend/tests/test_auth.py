from fastapi.testclient import TestClient

from app.main import app


def _with_password(password):
    app.state.demo_password = password
    return TestClient(app)


def test_open_when_no_password_configured():
    client = _with_password(None)
    assert client.get("/auth/check").status_code == 200


def test_protected_routes_require_the_header():
    client = _with_password("segreto")
    try:
        assert client.get("/auth/check").status_code == 401
        assert client.get("/budgets").status_code == 401
        assert client.get("/auth/check", headers={"X-Demo-Password": "sbagliata"}).status_code == 401
        assert client.get("/auth/check", headers={"X-Demo-Password": "segreto"}).status_code == 200
    finally:
        app.state.demo_password = None


def test_health_and_preflight_stay_open():
    client = _with_password("segreto")
    try:
        assert client.get("/health").status_code == 200
        preflight = client.options(
            "/chat/stream",
            headers={"Origin": "http://x", "Access-Control-Request-Method": "POST"},
        )
        assert preflight.status_code == 200
    finally:
        app.state.demo_password = None
