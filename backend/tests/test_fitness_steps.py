"""Google Fit 連携・歩数マージのテスト。"""

from fastapi.testclient import TestClient

from app.deps import get_current_uid, get_optional_uid
from app.main import app
from app.services import google_fit_service as gf
from app.steps_service import get_steps_today, merge_steps_for_day

client = TestClient(app)


def test_merge_steps_monotonic():
    uid = "merge-user"
    merge_steps_for_day(uid, 1000, "2026-09-13", source="google_fit")
    merged, delta = merge_steps_for_day(uid, 800, "2026-09-13", source="google_fit")
    assert merged == 1000
    assert delta == 0
    merged2, delta2 = merge_steps_for_day(uid, 1500, "2026-09-13", source="google_fit")
    assert merged2 == 1500
    assert delta2 == 500
    steps, src = get_steps_today(uid, "2026-09-13")
    assert steps == 1500
    assert src == "google_fit"


def test_fitness_status_guest_requires_auth():
    r = client.get("/api/fitness/status")
    assert r.status_code in (401, 403)


def test_fitness_status_authed():
    def uid():
        return "fitness-user"

    app.dependency_overrides[get_current_uid] = uid
    try:
        r = client.get("/api/fitness/status", headers={"Authorization": "Bearer dummy"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "configured" in body
        assert body["connected"] is False
    finally:
        app.dependency_overrides.clear()


def test_fitness_sync_not_connected():
    def uid():
        return "fitness-user-2"

    app.dependency_overrides[get_current_uid] = uid
    try:
        r = client.post("/api/fitness/sync", headers={"Authorization": "Bearer dummy"})
        assert r.status_code in (400, 503)
    finally:
        app.dependency_overrides.clear()


def test_steps_sync_from_device_merge():
    from app.growth_service import app_ymd

    day = app_ymd()

    def uid():
        return "native-user"

    app.dependency_overrides[get_current_uid] = uid
    try:
        r = client.post(
            "/api/steps/sync-from-device",
            headers={"Authorization": "Bearer dummy"},
            json={
                "source": "health_connect",
                "days": [{"ymd": day, "steps": 3000}],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "health_connect"
        assert body["today_steps"] >= 3000

        r2 = client.post(
            "/api/steps/sync-from-device",
            headers={"Authorization": "Bearer dummy"},
            json={
                "source": "health_connect",
                "days": [{"ymd": day, "steps": 2500}],
            },
        )
        assert r2.status_code == 200
        assert r2.json()["today_steps"] >= 3000
        assert r2.json()["delta_applied"] == 0
    finally:
        app.dependency_overrides.clear()


def test_fitness_sync_mock(monkeypatch):
    def uid():
        return "fitness-user-3"

    gf._memory_connections["fitness-user-3"] = {
        "provider": "google_fit",
        "refresh_token": "rt-test",
        "last_sync_at": None,
    }
    monkeypatch.setattr(gf, "is_google_fit_configured", lambda: True)
    monkeypatch.setattr(
        gf,
        "refresh_access_token",
        lambda _rt: {"access_token": "at-test"},
    )
    monkeypatch.setattr(gf, "fetch_steps_for_day", lambda _at, _ymd: 4321)

    app.dependency_overrides[get_current_uid] = uid
    try:
        r = client.post("/api/fitness/sync", headers={"Authorization": "Bearer dummy"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["today_steps"] >= 4321
        assert body["provider"] == "google_fit"
    finally:
        app.dependency_overrides.clear()
        gf._memory_connections.pop("fitness-user-3", None)
