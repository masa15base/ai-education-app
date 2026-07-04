from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _assert_diag_shape(data: dict) -> None:
    assert data.get("ok") is True
    assert "database_configured" in data
    assert "database_ping_ok" in data


def test_health_diagnostic_structure():
    r = client.get("/api/health/diagnostic")
    assert r.status_code == 200
    _assert_diag_shape(r.json())


def test_diagnostic_flat_path():
    r = client.get("/api/diagnostic")
    assert r.status_code == 200
    _assert_diag_shape(r.json())


def test_health_include_diagnostic_query():
    r = client.get("/api/health", params={"include_diagnostic": True})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "database_configured" in data


def test_health_default_minimal():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
