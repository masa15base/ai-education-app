"""
キャラクター生成オーケストレーター。

famicom_sprite_spec: 固定 character_spec から 32×32 少女 chibi を描画（自動判定なし）。
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image

from .famicom_sprite_generator import (
    GENERATION_MODE,
    generate_spec_sprite_bundle,
)

STAGE_SPRITE_SIZE: dict[str, int] = {
    "egg": 16,
    "baby": 32,
    "child": 32,
    "student": 32,
    "hero": 32,
}

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "static" / "generated"
)


def resolve_stage(stage: str | None, learning_level: int) -> str:
    if stage == "adult":
        stage = "hero"
    if stage in STAGE_SPRITE_SIZE:
        return stage
    lv = max(1, int(learning_level))
    if lv <= 4:
        return "baby"
    if lv <= 10:
        return "child"
    if lv <= 20:
        return "student"
    return "hero"


def analyze_features(
    line_img: Image.Image,
    rgb_source: Image.Image | None = None,
) -> dict[str, Any]:
    from .image_understanding import understand_image_from_pil

    return understand_image_from_pil(line_img, rgb_source)["raw_features"]


def generate_character_sprite_bundle(
    image_bytes: bytes,
    *,
    character_profile: dict | None = None,
    stage: str | None = None,
    learning_level: int = 1,
    output_dir: str | Path | None = None,
    save_file: bool = True,
) -> dict[str, Any]:
    _ = (stage, learning_level)
    return generate_spec_sprite_bundle(
        image_bytes,
        character_profile=character_profile,
        save_file=save_file,
        output_dir=output_dir,
    )


def generate_pixel_character_from_bytes(
    image_bytes: bytes,
    *,
    character_profile: dict | None = None,
    stage: str | None = None,
    learning_level: int = 1,
    output_dir: str | Path | None = None,
    save_file: bool = True,
) -> tuple[Image.Image, dict[str, Any], str | None]:
    bundle = generate_character_sprite_bundle(
        image_bytes,
        character_profile=character_profile,
        stage=stage,
        learning_level=learning_level,
        output_dir=output_dir,
        save_file=save_file,
    )
    return bundle["current_display"], bundle["meta"], bundle.get("saved_path")


def generate_pixel_character(
    processed_image_path: str,
    features: dict,
    character_profile: dict,
    stage: str,
    learning_level: int,
    output_dir: str,
) -> str:
    with open(processed_image_path, "rb") as f:
        data = f.read()
    _, meta, saved_path = generate_pixel_character_from_bytes(
        data,
        character_profile=character_profile,
        stage=stage,
        learning_level=learning_level,
        output_dir=output_dir,
        save_file=True,
    )
    return saved_path or meta.get("saved_path") or ""


def image_to_data_url(img: Image.Image) -> str:
    import base64

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


__all__ = ["GENERATION_MODE", "generate_character_sprite_bundle", "image_to_data_url", "resolve_stage"]
