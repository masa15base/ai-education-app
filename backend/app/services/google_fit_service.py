"""Google Fit OAuth と歩数取得（Web アプリ向け自動取り込み）。"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import db as dbmod
from ..growth_service import APP_TZ, app_day_keys, app_ymd
from ..models import UserFitnessConnection
from ..steps_service import merge_steps_for_day

logger = logging.getLogger(__name__)

FITNESS_SCOPE = "https://www.googleapis.com/auth/fitness.activity.read"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"

_memory_connections: dict[str, dict[str, Any]] = {}


def is_google_fit_configured() -> bool:
    return bool(
        os.getenv("GOOGLE_FIT_CLIENT_ID", "").strip()
        and os.getenv("GOOGLE_FIT_CLIENT_SECRET", "").strip()
        and os.getenv("GOOGLE_FIT_REDIRECT_URI", "").strip()
    )


def _state_secret() -> str:
    return (
        os.getenv("FITNESS_OAUTH_STATE_SECRET", "").strip()
        or os.getenv("GOOGLE_FIT_CLIENT_SECRET", "").strip()
        or "dev-fitness-state-secret"
    )


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")


def sign_oauth_state(uid: str) -> str:
    payload = {"uid": uid, "exp": int(time.time()) + 900}
    body = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(_state_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.quote(f"{body}|{sig}")


def verify_oauth_state(state: str) -> str | None:
    try:
        raw = urllib.parse.unquote(state)
        body, sig = raw.rsplit("|", 1)
        expected = hmac.new(_state_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(body)
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        uid = str(payload.get("uid") or "")
        return uid or None
    except Exception:
        return None


def build_connect_url(uid: str) -> str:
    params = {
        "client_id": os.getenv("GOOGLE_FIT_CLIENT_ID", "").strip(),
        "redirect_uri": os.getenv("GOOGLE_FIT_REDIRECT_URI", "").strip(),
        "response_type": "code",
        "scope": FITNESS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": sign_oauth_state(uid),
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def _http_post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def _http_post_json(url: str, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {access_token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def exchange_auth_code(code: str) -> dict[str, Any]:
    return _http_post_form(
        TOKEN_URL,
        {
            "code": code,
            "client_id": os.getenv("GOOGLE_FIT_CLIENT_ID", "").strip(),
            "client_secret": os.getenv("GOOGLE_FIT_CLIENT_SECRET", "").strip(),
            "redirect_uri": os.getenv("GOOGLE_FIT_REDIRECT_URI", "").strip(),
            "grant_type": "authorization_code",
        },
    )


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    return _http_post_form(
        TOKEN_URL,
        {
            "client_id": os.getenv("GOOGLE_FIT_CLIENT_ID", "").strip(),
            "client_secret": os.getenv("GOOGLE_FIT_CLIENT_SECRET", "").strip(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )


def _save_connection(uid: str, refresh_token: str) -> None:
    if dbmod.SessionLocal is None:
        _memory_connections[uid] = {
            "provider": "google_fit",
            "refresh_token": refresh_token,
            "last_sync_at": None,
        }
        return
    db = dbmod.SessionLocal()
    try:
        row = db.query(UserFitnessConnection).filter(UserFitnessConnection.user_id == uid).first()
        if row is None:
            row = UserFitnessConnection(
                user_id=uid,
                provider="google_fit",
                refresh_token=refresh_token,
            )
            db.add(row)
        else:
            row.provider = "google_fit"
            row.refresh_token = refresh_token
        db.commit()
    finally:
        db.close()


def get_connection(uid: str) -> dict[str, Any] | None:
    if dbmod.SessionLocal is None:
        return _memory_connections.get(uid)
    db = dbmod.SessionLocal()
    try:
        row = db.query(UserFitnessConnection).filter(UserFitnessConnection.user_id == uid).first()
        if row is None:
            return None
        return {
            "provider": row.provider,
            "refresh_token": row.refresh_token,
            "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        }
    finally:
        db.close()


def disconnect(uid: str) -> None:
    if dbmod.SessionLocal is None:
        _memory_connections.pop(uid, None)
        return
    db = dbmod.SessionLocal()
    try:
        db.query(UserFitnessConnection).filter(UserFitnessConnection.user_id == uid).delete()
        db.commit()
    finally:
        db.close()


def _set_last_sync(uid: str) -> None:
    now = datetime.now(timezone.utc)
    if dbmod.SessionLocal is None:
        if uid in _memory_connections:
            _memory_connections[uid]["last_sync_at"] = now.isoformat()
        return
    db = dbmod.SessionLocal()
    try:
        row = db.query(UserFitnessConnection).filter(UserFitnessConnection.user_id == uid).first()
        if row:
            row.last_sync_at = now
            db.commit()
    finally:
        db.close()


def _jst_day_bounds_ms(ymd: str) -> tuple[int, int]:
    start_local = datetime.strptime(ymd, "%Y-%m-%d").replace(tzinfo=APP_TZ)
    end_local = start_local + timedelta(days=1)
    start_ms = int(start_local.astimezone(timezone.utc).timestamp() * 1000)
    end_ms = int(end_local.astimezone(timezone.utc).timestamp() * 1000)
    return start_ms, end_ms


def fetch_steps_for_day(access_token: str, ymd: str) -> int:
    start_ms, end_ms = _jst_day_bounds_ms(ymd)
    payload = {
        "aggregateBy": [
            {
                "dataTypeName": "com.google.step_count.delta",
                "dataSourceId": (
                    "derived:com.google.step_count.delta:"
                    "com.google.android.gms:estimated_steps"
                ),
            }
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms,
    }
    try:
        data = _http_post_json(AGGREGATE_URL, payload, access_token)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() if exc.fp else ""
        raise RuntimeError(f"google_fit_http_{exc.code}: {body[:200]}") from exc

    total = 0
    for bucket in data.get("bucket", []) or []:
        for ds in bucket.get("dataset", []) or []:
            for point in ds.get("point", []) or []:
                for val in point.get("value", []) or []:
                    total += int(val.get("intVal") or 0)
    return max(0, total)


def sync_google_fit_for_user(uid: str, *, days: int = 7) -> dict[str, Any]:
    conn = get_connection(uid)
    if not conn or not conn.get("refresh_token"):
        raise ValueError("google_fit_not_connected")

    token_data = refresh_access_token(str(conn["refresh_token"]))
    access_token = str(token_data.get("access_token") or "")
    if not access_token:
        raise RuntimeError("google_fit_token_refresh_failed")

    day_keys = app_day_keys(days)
    today_ymd = app_ymd()
    synced: list[dict[str, Any]] = []
    total_delta = 0

    for ymd in day_keys:
        fit_steps = fetch_steps_for_day(access_token, ymd)
        new_steps, delta = merge_steps_for_day(uid, fit_steps, ymd, source="google_fit")
        if delta > 0:
            total_delta += delta
        synced.append({"date": ymd, "steps": new_steps, "imported": fit_steps})

    if total_delta > 0 or any(row["steps"] > 0 for row in synced):
        from ..growth_stats_store import record_activity

        today_steps = next((r["steps"] for r in synced if r["date"] == today_ymd), 0)
        record_activity(
            uid,
            {
                "activity_type": "steps",
                "steps": total_delta,
                "goal_reached": int(today_steps) >= 5000,
            },
        )

    _set_last_sync(uid)
    today_row = next((r for r in synced if r["date"] == today_ymd), {"steps": 0})
    return {
        "provider": "google_fit",
        "today_ymd": today_ymd,
        "today_steps": int(today_row.get("steps") or 0),
        "imported_today": int(today_row.get("imported") or 0),
        "delta_applied": total_delta,
        "synced_days": synced,
    }


def fitness_status(uid: str) -> dict[str, Any]:
    conn = get_connection(uid)
    return {
        "configured": is_google_fit_configured(),
        "connected": bool(conn and conn.get("refresh_token")),
        "provider": conn.get("provider") if conn else None,
        "last_sync_at": conn.get("last_sync_at") if conn else None,
        "hint": (
            "Google Fit と連携すると、歩数が自動で取り込まれます（Android 推奨）。"
            if is_google_fit_configured()
            else "サーバーに Google Fit OAuth 設定が必要です（GOOGLE_FIT_CLIENT_ID 等）。"
        ),
    }
