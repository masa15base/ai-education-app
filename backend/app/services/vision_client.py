"""
OpenAI Vision: 手描き画像から固定 schema の JSON 特徴抽出のみ。
キャラクター設計・画像生成は character_dna 側で行う。
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from typing import Any

from openai import OpenAI
from PIL import Image

from .character_dna import VISION_RESULT_KEYS, _coerce_vision_result

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"

_VISION_SYSTEM = """\
You extract visual traits from a child's hand-drawn character sketch.
Return ONLY a single JSON object matching the required schema exactly.
Do NOT design a new character. Do NOT suggest art style or poses.
If unsure, use "unknown" for enum fields.
"""

_VISION_USER = """\
Analyze this hand-drawn character image. Extract traits ONLY.

Return JSON with exactly these keys:
{
  "face_shape": "round | oval | square | unknown",
  "hair_color": "black | dark_navy | brown | blonde | unknown",
  "hair_style": "short_bob | long | twin_tail | short | unknown",
  "bangs": "straight | center | side | none | unknown",
  "eye_shape": "large_round | small_dot | almond | unknown",
  "eye_count": 2,
  "mouth": "smile | neutral | open_smile | unknown",
  "cheeks": true,
  "accent_color": "mint_green | pink | blue | yellow | none",
  "accessory": "star | ribbon | hat | none",
  "mood": "cute | cheerful | calm | energetic",
  "signature_features": []
}

Rules:
- eye_count must be 2 if two eyes are drawn, else 2 as default.
- signature_features: short English phrases for visible traits only (max 6).
- Do not add keys outside this schema.
"""


def is_character_vision_enabled() -> bool:
    from ..bootstrap_env import load_backend_env

    load_backend_env()
    if os.getenv("CHARACTER_VISION_ENABLED", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return False
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def vision_model_name() -> str:
    return (os.getenv("CHARACTER_VISION_MODEL") or _DEFAULT_MODEL).strip()


def _image_data_url(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    fmt = (img.format or "PNG").upper()
    if fmt == "JPEG":
        img.save(buf, format="JPEG", quality=88)
        mime = "image/jpeg"
    else:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _parse_json_content(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def extract_vision_result_schema(parsed: dict[str, Any]) -> dict[str, Any]:
    """Vision 応答を schema 形に限定（設計はしない）。"""
    coerced = _coerce_vision_result(parsed)
    out: dict[str, Any] = {}
    for key in VISION_RESULT_KEYS:
        out[key] = coerced.get(key)
    out["eye_count"] = int(coerced.get("eye_count") or 2)
    out["cheeks"] = bool(coerced.get("cheeks", True))
    sig = coerced.get("signature_features")
    out["signature_features"] = sig if isinstance(sig, list) else []
    return out


def fetch_vision_result(image_bytes: bytes) -> tuple[dict[str, Any] | None, str | None]:
    """
    OpenAI Vision で schema JSON を抽出。
    戻り値: (vision_result, error_message)
    """
    if not is_character_vision_enabled():
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return None, "OPENAI_API_KEY is not set"
        return None, "CHARACTER_VISION_ENABLED is off"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = vision_model_name()
    data_url = _image_data_url(image_bytes)

    try:
        client = OpenAI(api_key=api_key, timeout=45.0)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _VISION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _VISION_USER},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "low"},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=400,
            temperature=0.1,
        )
        content = (response.choices[0].message.content or "").strip()
        parsed = _parse_json_content(content)
        if not parsed:
            return None, "model returned invalid JSON"
        return extract_vision_result_schema(parsed), None
    except Exception as exc:
        logger.exception("character vision: OpenAI request failed")
        return None, f"{type(exc).__name__}: {exc}"


# 後方互換（テスト・旧 import）
def fetch_openai_vision_attributes(
    image_bytes: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    result, err = fetch_vision_result(image_bytes)
    if result is None:
        return None, err
    return {"attributes": result, "provider": "openai"}, None
