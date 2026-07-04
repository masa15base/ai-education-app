"""キャラクター画像生成（手書きアップロード〜前処理〜生成）の要件定義。"""
from __future__ import annotations

from .security_settings import max_preprocess_image_bytes

# Pillow がデコードできる形式（HEIC/HEIF は未対応）
INPUT_MIME_TYPES: tuple[str, ...] = (
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
)
INPUT_EXTENSIONS: tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
)
PILLOW_FORMAT_NAMES: frozenset[str] = frozenset(
    {"JPEG", "PNG", "WEBP", "GIF", "BMP", "MPO"}
)

PREPROCESS_OUTPUT_MIME = "image/png"
CHARACTER_OUTPUT_MIME = "image/png"
CHARACTER_OUTPUT_ENCODING = "data_url_base64"


def character_image_requirements() -> dict:
    """GET /api/preprocess-image/info の `requirements` ブロック。"""
    max_b = max_preprocess_image_bytes()
    return {
        "workflow": [
            "upload_handdrawn_photo",
            "preprocess_to_line_art_png",
            "generate_colored_character_png",
            "preview_and_confirm",
            "save_to_home",
        ],
        "input": {
            "description": "手書きの写真・スキャン画像（アップロード）",
            "mime_types": list(INPUT_MIME_TYPES),
            "extensions": list(INPUT_EXTENSIONS),
            "max_bytes": max_b,
            "max_bytes_human": f"{max_b // (1024 * 1024)}MB",
            "unsupported": [
                "image/heic",
                "image/heif",
                "PDF",
                "動画",
            ],
            "notes": [
                "JPEG または PNG を推奨（スマホの HEIC は事前に JPEG に変換してください）",
                "1ファイルあたり最大 {} まで".format(max_b // (1024 * 1024)),
            ],
        },
        "preprocess_output": {
            "mime": PREPROCESS_OUTPUT_MIME,
            "format": "PNG",
            "encoding": "base64",
            "description": "線画抽出後の中間画像（API: POST /api/preprocess-image）",
        },
        "character_output": {
            "mime": CHARACTER_OUTPUT_MIME,
            "format": "PNG",
            "encoding": CHARACTER_OUTPUT_ENCODING,
            "description": "カラー化したキャラ画像（API: POST /api/generate-character）",
        },
    }
