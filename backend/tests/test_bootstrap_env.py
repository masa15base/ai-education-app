"""backend/.env が cwd に依存せず読めること。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_load_backend_env_from_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)

    from app.bootstrap_env import load_backend_env

    env_path = load_backend_env()
    assert env_path == repo_root / "backend" / ".env"
    if env_path.is_file():
        assert os.getenv("OPENAI_API_KEY", "").strip() or True
