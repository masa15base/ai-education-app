"""Firebase Admin 設定（JSON / Heroku 分割 env）の読み取り。"""
from __future__ import annotations

import json

import pytest

from app.deps import _firebase_credential_dict, is_firebase_configured


def test_firebase_from_credentials_json(monkeypatch: pytest.MonkeyPatch) -> None:
    cred = {
        "type": "service_account",
        "project_id": "demo",
        "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        "client_email": "demo@demo.iam.gserviceaccount.com",
    }
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", json.dumps(cred))
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("FIREBASE_CLIENT_EMAIL", raising=False)
    monkeypatch.delenv("FIREBASE_PRIVATE_KEY", raising=False)

    parsed = _firebase_credential_dict()
    assert parsed is not None
    assert parsed["project_id"] == "demo"
    assert is_firebase_configured()


def test_firebase_from_split_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "ai-education-app-9d7ae")
    monkeypatch.setenv(
        "FIREBASE_CLIENT_EMAIL",
        "firebase-adminsdk@ai-education-app-9d7ae.iam.gserviceaccount.com",
    )
    monkeypatch.setenv(
        "FIREBASE_PRIVATE_KEY",
        "-----BEGIN PRIVATE KEY-----\\nline\\n-----END PRIVATE KEY-----\\n",
    )

    parsed = _firebase_credential_dict()
    assert parsed is not None
    assert parsed["project_id"] == "ai-education-app-9d7ae"
    assert "\\n" not in parsed["private_key"]
    assert "\n" in parsed["private_key"]
    assert is_firebase_configured()


def test_firebase_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIREBASE_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("FIREBASE_CLIENT_EMAIL", raising=False)
    monkeypatch.delenv("FIREBASE_PRIVATE_KEY", raising=False)

    assert _firebase_credential_dict() is None
    assert not is_firebase_configured()
