"""
互換エントリ。Heroku / 推奨は `uvicorn app.main:app`（Procfile と同じ）。
`uvicorn main:app` で起動したい場合のみ利用。
"""
from app.main import app

__all__ = ["app"]
