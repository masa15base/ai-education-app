from __future__ import annotations

from .bootstrap_env import load_backend_env

load_backend_env()

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pydantic import BaseModel, Field

from .deps import get_current_uid, init_firebase
from .security_settings import is_production_hardened
from .progress_service import append_progress, list_progress
from .question_service import questions_for_quiz
from .routes import (
    answers,
    character as character_routes,
    chat,
    generate_character,
    image_preprocess,
    quiz,
    stats,
    steps as steps_routes,
)


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def _cors_regex() -> str | None:
    """
    明示リストに無いローカルポート（例: 5174 / Vite preview）を許可。
    本番の独自ドメインは FRONTEND_ORIGINS に必ず含める。
    無効化: FRONTEND_ORIGIN_REGEX= 空
    """
    raw = os.getenv(
        "FRONTEND_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )
    return raw.strip() or None


def _init_database_on_startup() -> None:
    """起動時の DB 初期化。失敗しても API は起動する（メモリフォールバック）。"""
    from .db import Base, disable_database, engine

    from . import models  # noqa: F401

    if engine is None:
        return
    if os.getenv("SKIP_DB_CREATE_ALL", "").lower() in ("1", "true", "yes"):
        logger.info("SKIP_DB_CREATE_ALL: skipping create_all")
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema ready")
    except Exception as exc:
        logger.warning(
            "Database unavailable at startup (%s). Running without DB (memory fallback).",
            exc,
        )
        disable_database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    _init_database_on_startup()
    yield


_production = is_production_hardened()
app = FastAPI(
    debug=os.getenv("DEBUG", "").lower() in ("1", "true", "yes"),
    lifespan=lifespan,
    docs_url=None if _production else "/docs",
    redoc_url=None if _production else "/redoc",
    openapi_url=None if _production else "/openapi.json",
)

_cors_kw: dict = {
    "allow_origins": _cors_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
_reg = _cors_regex()
if _reg:
    _cors_kw["allow_origin_regex"] = _reg
app.add_middleware(CORSMiddleware, **_cors_kw)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(character_routes.router, prefix="/api/character", tags=["character"])
app.include_router(answers.router, prefix="/api/answers", tags=["answers"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["quiz"])
app.include_router(image_preprocess.router, prefix="/api", tags=["image"])
app.include_router(generate_character.router, prefix="/api", tags=["character"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(steps_routes.router, prefix="/api/steps", tags=["steps"])

_static_root = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_root):
    app.mount("/static", StaticFiles(directory=_static_root), name="static")


class ProgressIn(BaseModel):
    subject: str
    level: int = Field(ge=1, le=99)
    score: int = Field(ge=0, le=100)


@app.get("/")
def root():
    return {"message": "まなとも API", "docs": "/docs"}


def _character_vision_enabled() -> bool:
    from .services.vision_client import is_character_vision_enabled

    return is_character_vision_enabled()


def _health_diagnostic_payload() -> dict[str, Any]:
    """接続テスト用（秘密は返さない）。"""
    from .db import SessionLocal as SL

    db_configured = SL is not None
    db_ping_ok = False
    if db_configured:
        try:
            db = SL()
            try:
                db.execute(text("SELECT 1"))
                db_ping_ok = True
            finally:
                db.close()
        except Exception:
            db_ping_ok = False

    return {
        "ok": True,
        "api": True,
        "database_configured": db_configured,
        "database_ping_ok": db_ping_ok,
        "replicate_configured": bool(os.getenv("REPLICATE_API_TOKEN")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "character_vision_enabled": _character_vision_enabled(),
        "firebase_admin_configured": bool(os.getenv("FIREBASE_CREDENTIALS_JSON")),
        "cors_origins_count": len(_cors_origins()),
    }


@app.get("/api/health")
def api_health(include_diagnostic: bool = Query(False, description="詳細チェック結果を JSON に付与")):
    """
    `/api/health?include_diagnostic=true` で診断付き応答。
    （Heroku が古く `/api/health/diagnostic` だけ無いときでも、最新デプロイでここだけ直せば済む）
    """
    payload: dict[str, Any] = {"ok": True}
    if include_diagnostic:
        extra = _health_diagnostic_payload()
        extra.pop("ok", None)
        payload.update(extra)
    return payload


@app.get("/api/health/diagnostic")
def health_diagnostic() -> dict[str, Any]:
    return _health_diagnostic_payload()


@app.get("/api/diagnostic")
def connection_diagnostic() -> dict[str, Any]:
    """`/api/health/diagnostic` の別名（ルータ・プロキシでネスト経路のみ失敗する場合向け）。"""
    return _health_diagnostic_payload()


@app.get("/api/questions")
def get_questions(subject: str, level: int, limit: int = 5):
    """
    JawsDB の `questions` を優先（算数・英語含む）。
    件数不足や DB 未設定時は `quiz_engine` の動的生成で補完。
    """
    try:
        lim = max(1, min(int(limit), 10))
        return questions_for_quiz(subject, level, lim)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"questions error: {e}")


@app.post("/api/progress")
def save_progress(body: ProgressIn, uid: str = Depends(get_current_uid)):
    append_progress(uid, body.subject, body.level, body.score)
    return {"status": "ok", "uid": uid}


@app.get("/api/progress")
def list_progress_api(
    subject: Optional[str] = None,
    uid: str = Depends(get_current_uid),
):
    items, total = list_progress(uid, subject)
    return {
        "items": items,
        "page": {"limit": total, "offset": 0, "total": total},
    }
