"""チャット API（OpenAI 未設定時フォールバック）。"""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _bearer(uid: str = "pytest-chat-user") -> dict[str, str]:
    h = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    p = (
        base64.urlsafe_b64encode(json.dumps({"sub": uid, "uid": uid}).encode())
        .decode()
        .rstrip("=")
    )
    return {"Authorization": f"Bearer {h}.{p}.x"}


@pytest.fixture
def clear_openai_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_chat_fallback_returns_reply_when_no_api_key(clear_openai_key):
    r = client.post(
        "/api/chat/",
        json={"message": "きょうもがんばる"},
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "reply" in body and len(body["reply"]) > 0


def test_chat_fallback_hints_quiz_keyword(clear_openai_key):
    r = client.post(
        "/api/chat/",
        json={"message": "クイズやりたい"},
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    assert "クイズ" in r.json().get("reply", "")


def test_chat_ignores_extra_json_fields_for_openapi_compat(clear_openai_key):
    r = client.post(
        "/api/chat/",
        json={"message": "hello", "prompt": "ignored", "junk": True},
        headers=_bearer(),
    )
    assert r.status_code == 200


def test_chat_capabilities_without_openai(clear_openai_key):
    r = client.get("/api/chat/capabilities")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["openai_configured"] is False
    assert d["reply_mode"] == "simple"


def test_chat_accepts_character_display_name(clear_openai_key):
    r = client.post(
        "/api/chat/",
        json={"message": "なにか話して", "character_display_name": "ふーちゃん"},
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    assert r.json().get("reply")


def test_chat_requires_auth(clear_openai_key):
    r = client.post("/api/chat/", json={"message": "hello"})
    assert r.status_code == 401
