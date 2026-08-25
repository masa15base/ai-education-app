"""Firebase ID トークン検証（本番）と開発時の JWT payload 読み取り。"""
from __future__ import annotations

import base64
import json
import os

from fastapi import Header, HTTPException

from .security_settings import is_production_hardened

try:
    import firebase_admin
    from firebase_admin import credentials, auth as fb_auth
except ImportError:  # pragma: no cover
    firebase_admin = None  # type: ignore
    credentials = None  # type: ignore
    fb_auth = None  # type: ignore

_firebase_ready = False


def _normalize_private_key(key: str) -> str:
    """Heroku 等で \\n エスケープされた PEM を復元する。"""
    return key.replace("\\n", "\n").strip()


def _firebase_credential_dict() -> dict | None:
    """
    Firebase Admin 用サービスアカウント辞書。
    FIREBASE_CREDENTIALS_JSON を優先し、無ければ Heroku 向け分割 env から組み立てる。
    """
    raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL", "").strip()
    private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").strip()
    if not (project_id and client_email and private_key):
        return None

    email_encoded = client_email.replace("@", "%40")
    return {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", "").strip() or "heroku",
        "private_key": _normalize_private_key(private_key),
        "client_email": client_email,
        "client_id": os.getenv("FIREBASE_CLIENT_ID", "").strip() or "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": (
            f"https://www.googleapis.com/robot/v1/metadata/x509/{email_encoded}"
        ),
    }


def is_firebase_configured() -> bool:
    return _firebase_credential_dict() is not None


def init_firebase() -> None:
    global _firebase_ready
    if _firebase_ready:
        return
    if firebase_admin is None or firebase_admin._apps:
        _firebase_ready = bool(firebase_admin and firebase_admin._apps)
        return
    cred_dict = _firebase_credential_dict()
    if not cred_dict:
        return
    try:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        _firebase_ready = True
    except Exception:
        _firebase_ready = False


def _decode_sub_unverified(token: str) -> str | None:
    """開発用: 署名検証なしで JWT payload の sub を取り出す。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload.get("sub")
    except Exception:
        return None


def verify_and_get_uid(token: str) -> str:
    init_firebase()
    if firebase_admin and firebase_admin._apps and fb_auth:
        try:
            decoded = fb_auth.verify_id_token(token)
            uid = decoded.get("uid") or decoded.get("sub")
            if uid:
                return uid
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    if is_production_hardened():
        raise HTTPException(
            status_code=503,
            detail="Firebase Admin SDK must be configured (set FIREBASE_CREDENTIALS_JSON)",
        )
    sub = _decode_sub_unverified(token)
    if sub:
        return sub
    raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_uid(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")
    token = authorization.split(" ", 1)[1].strip()
    return verify_and_get_uid(token)


async def get_optional_uid(authorization: str | None = Header(None)) -> str | None:
    """Authorization が無い・無効なときは None（匿名）。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        return verify_and_get_uid(token)
    except HTTPException:
        return None
