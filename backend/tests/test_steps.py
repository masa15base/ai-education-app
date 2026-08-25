"""歩数 API スモークテスト。"""

from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_current_uid, get_optional_uid

client = TestClient(app)


def test_steps_today_guest():
    r = client.get("/api/steps/today")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["authenticated"] is False
    assert d["steps"] is None
    assert d["source"] == "none"
    assert d["today_ymd"]


def test_steps_put_get_memory():
    def uid():
        return "step-user-1"

    app.dependency_overrides[get_optional_uid] = uid
    app.dependency_overrides[get_current_uid] = uid
    try:
        r0 = client.get("/api/steps/today", headers={"Authorization": "Bearer dummy"})
        assert r0.status_code == 200
        assert r0.json()["steps"] == 0

        r1 = client.put(
            "/api/steps/today",
            json={"steps": 3200},
            headers={"Authorization": "Bearer dummy"},
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["steps"] == 3200

        r2 = client.get("/api/steps/today", headers={"Authorization": "Bearer dummy"})
        assert r2.status_code == 200
        assert r2.json()["steps"] == 3200
        assert r2.json()["authenticated"] is True

        rw = client.get("/api/steps/week", headers={"Authorization": "Bearer dummy"})
        assert rw.status_code == 200, rw.text
        week = rw.json()
        assert week["authenticated"] is True
        assert len(week["days"]) == 7
        assert week["goal_steps"] == 5000
        today_row = next(d for d in week["days"] if d["date"] == week["today_ymd"])
        assert today_row["steps"] == 3200
        assert today_row["goal_reached"] is False
    finally:
        app.dependency_overrides.clear()


def test_steps_week_guest():
    r = client.get("/api/steps/week")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["authenticated"] is False
    assert len(d["days"]) == 7
    assert all(row["steps"] == 0 for row in d["days"])
