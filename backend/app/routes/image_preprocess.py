"""手書き画像の前処理（線強調・余白トリム・正方化・PNG base64）。"""
from __future__ import annotations

import base64
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..character_image_spec import (
    PILLOW_FORMAT_NAMES,
    PREPROCESS_OUTPUT_MIME,
    character_image_requirements,
)
from ..image_preprocess_algo import ALGORITHM_ID, DEFAULT_MAX_EDGE, build_binary_scribble
from ..rate_limit import require_preprocess_rate_limit
from ..security_settings import max_preprocess_image_bytes

router = APIRouter(tags=["image"])

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore


MAX_EDGE = DEFAULT_MAX_EDGE


@router.get("/preprocess-image/info")
def preprocess_image_info():
    """接続テスト・UI表示用のアルゴリズム情報（機密なし）。"""
    return {
        "algorithm": ALGORITHM_ID,
        "max_edge": MAX_EDGE,
        "description": (
            "normalize size + grayscale + autocontrast + median + gamma + "
            "Otsu-blend threshold + morph cleanup + trim + square pad + "
            "content-aware pixel grid + BOX downscale + NEAREST upscale"
        ),
        "tips": [
            "白い紙に濃いペンで描く",
            "影が入らないように明るい場所で撮る",
            "絵全体が写真に入るように撮る",
            "線が薄いときは少し濃いペンか鉛筆でなぞり直すとドットが残りやすい",
        ],
        "requirements": character_image_requirements(),
    }


@router.post("/preprocess-image")
async def preprocess_image(
    image: UploadFile = File(...),
    _uid: str = Depends(require_preprocess_rate_limit),
):
    if Image is None:
        raise HTTPException(
            status_code=503,
            detail="Pillow is not installed",
        )
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    max_b = max_preprocess_image_bytes()
    if len(raw) > max_b:
        raise HTTPException(
            status_code=413,
            detail=f"image too large (max {max_b} bytes)",
        )

    try:
        img = Image.open(io.BytesIO(raw))
        fmt = (img.format or "").upper()
        if fmt and fmt not in PILLOW_FORMAT_NAMES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unsupported image format: {fmt}. "
                    f"Use JPEG, PNG, WebP, GIF, or BMP (HEIC/HEIF not supported)."
                ),
            )
        img = img.convert("RGB")
        processed, meta = build_binary_scribble(img, max_edge=MAX_EDGE)
        buf = io.BytesIO()
        processed.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid image: {e}") from e

    return {
        "imageBase64": b64,
        "mime": PREPROCESS_OUTPUT_MIME,
        "algorithm": ALGORITHM_ID,
        "meta": meta,
    }
