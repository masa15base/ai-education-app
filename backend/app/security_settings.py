"""本番向けセキュリティフラグ・リソース上限。"""
from __future__ import annotations

import os


def is_production_hardened() -> bool:
    """
    True のとき:
    - Firebase ID トークンは Admin SDK でのみ検証（未検証 JWT フォールバック禁止）
    - OpenAPI /docs を無効化（main で参照）
    """
    v = os.getenv("MANATOMO_PRODUCTION", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    env = os.getenv("ENV", "").strip().lower()
    return env in ("production", "prod")


def max_preprocess_image_bytes() -> int:
    return int(os.getenv("MAX_PREPROCESS_IMAGE_BYTES", str(8 * 1024 * 1024)))


def max_generate_image_base64_chars() -> int:
    """data URL 兼ねる base64 文字列の上限（おおよそ 8MiB 相当）。"""
    return int(os.getenv("MAX_GENERATE_IMAGE_BASE64_CHARS", str(12_000_000)))
