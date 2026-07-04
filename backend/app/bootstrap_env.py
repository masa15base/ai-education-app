"""backend/.env を cwd に依存せず読み込む。"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_LOADED = False
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def load_backend_env(*, override: bool = False) -> Path:
    """プロジェクトルートや別 cwd から起動しても OPENAI_API_KEY 等を読む。"""
    global _LOADED
    env_path = _BACKEND_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=override)
    _LOADED = True
    return env_path
