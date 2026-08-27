import base64
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _bearer(uid: str = "pytest-gen-user") -> dict[str, str]:
    h = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    p = (
        base64.urlsafe_b64encode(json.dumps({"sub": uid, "uid": uid}).encode())
        .decode()
        .rstrip("=")
    )
    return {"Authorization": f"Bearer {h}.{p}.x"}


def test_generate_character_returns_local_data_url(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    r = client.post(
        "/api/generate-character",
        json={
            "imageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "stage": "child",
        },
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["image"].startswith("data:image/png;base64,")
    assert body.get("generation_mode") in ("character_dna_evolution", "famicom_sprite_spec")
    assert body.get("validation_result", {}).get("passed") is True
    assert body.get("image_understanding") is not None
    assert body.get("character_dna") is not None or body.get("generation_mode") == "famicom_sprite_spec"
    if body.get("generation_mode") == "character_dna_evolution":
        assert body.get("next_stage_preview") is not None
        assert body.get("final_hero_preview") is not None


def test_generate_character_short_payload():
    r = client.post(
        "/api/generate-character",
        json={"imageBase64": "abcd"},
        headers=_bearer(),
    )
    assert r.status_code == 422


def test_generate_character_without_stage_when_db_unavailable(monkeypatch):
    """stage 未指定でも DB 障害時は learning_level で生成できる。"""
    from sqlalchemy.exc import OperationalError

    import pymysql

    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")

    def _boom(_uid: str, db=None):
        raise OperationalError(
            "SELECT",
            {},
            pymysql.err.OperationalError(
                1226,
                "User 'x' has exceeded the 'max_questions' resource (current value: 3600)",
            ),
        )

    monkeypatch.setattr("app.routes.generate_character.get_stats", _boom)
    monkeypatch.setattr("app.routes.generate_character.get_character_exp", lambda _uid: 0)

    r = client.post(
        "/api/generate-character",
        json={
            "imageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "learning_level": 8,
        },
        headers=_bearer("pytest-db-fail-user"),
    )
    assert r.status_code == 200, r.text
    assert r.json().get("generation_mode") in ("famicom_sprite_spec", "character_dna_evolution")


def test_generate_character_requires_auth(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    r = client.post(
        "/api/generate-character",
        json={
            "imageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        },
    )
    assert r.status_code == 401
