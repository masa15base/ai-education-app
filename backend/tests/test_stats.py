"""統計サマリー API のスモークテスト。"""
from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_current_uid, get_optional_uid

client = TestClient(app)


def _uid_factory(value: str):
    def uid():
        return value

    return uid


def test_stats_summary_guest_empty_timeline():
    res = client.get("/api/stats/summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["timeline"] == []
    assert body["quiz_sessions_week"] == 0
    assert body.get("steps_today") is None
    assert body.get("steps_goal") == 5000


def test_stats_summary_memory_follows_progress():
    uid = _uid_factory("stats-test-user")
    app.dependency_overrides[get_current_uid] = uid
    app.dependency_overrides[get_optional_uid] = uid
    try:
        h = {"Authorization": "Bearer dummy"}
        payload = {"subject": "math", "level": 2, "score": 90}
        r1 = client.post("/api/progress", json=payload, headers=h)
        assert r1.status_code == 200, r1.text

        payload2 = {"subject": "english", "level": 1, "score": 70}
        r1b = client.post("/api/progress", json=payload2, headers=h)
        assert r1b.status_code == 200, r1b.text

        r2 = client.get("/api/stats/summary", headers=h)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["quiz_sessions_total"] >= 2
        assert len(data["timeline"]) >= 2
        head = data["timeline"][0]
        assert head["subject"] in ("math", "english")
        assert data.get("steps_today") is not None
        assert data.get("steps_goal") == 5000
        assert data.get("steps_ymd")

        assert len(data["weekly_activity"]) == 7
        assert sum(d["quiz_sessions"] for d in data["weekly_activity"]) >= 2

        subjects = {row["subject"] for row in data["subject_breakdown"]}
        assert "math" in subjects
        assert "english" in subjects
        math_row = next(r for r in data["subject_breakdown"] if r["subject"] == "math")
        assert math_row["sessions_week"] >= 1
        assert math_row["average_score_week"] == 90.0
    finally:
        app.dependency_overrides.clear()
