"""CORS オリジン解決（FRONTEND_ORIGINS + FRONTEND_URL）。"""
from __future__ import annotations

import pytest

from app.main import _cors_origins


def test_cors_origins_includes_frontend_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    monkeypatch.setenv("FRONTEND_URL", "https://ai-edu-app-frontend.vercel.app/")

    origins = _cors_origins()
    assert "http://localhost:5173" in origins
    assert "https://ai-edu-app-frontend.vercel.app" in origins


def test_cors_origins_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGINS",
        "https://ai-edu-app-frontend.vercel.app,http://localhost:5173",
    )
    monkeypatch.setenv("FRONTEND_URL", "https://ai-edu-app-frontend.vercel.app")

    origins = _cors_origins()
    assert origins.count("https://ai-edu-app-frontend.vercel.app") == 1
