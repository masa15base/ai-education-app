"""進捗 API のスモークテスト（認証は依存を差し替え）。"""
from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_current_uid

client = TestClient(app)


def override_uid():
    return "test-uid"


def test_progress_save_and_list(monkeypatch):
    app.dependency_overrides[get_current_uid] = override_uid
    try:
        payload = {"subject": "math", "level": 1, "score": 100}
        headers = {"Authorization": "Bearer dummy"}

        res = client.post("/api/progress", json=payload, headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "ok"
        assert body["uid"] == "test-uid"

        res2 = client.get("/api/progress", headers=headers)
        assert res2.status_code == 200, res2.text
        data = res2.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert data["items"][0]["subject"] == "math"
    finally:
        app.dependency_overrides.clear()


def test_progress_missing_auth():
    res = client.post("/api/progress", json={"subject": "math", "level": 1, "score": 80})
    assert res.status_code == 401
