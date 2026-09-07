"""
character_dna → 手描きピクセル配置のファミコン風 chibi（32×32）描画。

ベクター描画 + 量子化（pixel_character_renderer）より輪郭が崩れにくい。
"""
from __future__ import annotations

from typing import Any

from PIL import Image

from .base_character_generator import build_egg_sprite
from .character_dna import ACCENT_COLOR_RGB, HAIR_COLOR_RGB
from .evolution_preview_compose import frame_sprite_display
from .famicom_sprite_common import decorate_stage
from .famicom_sprite_generator import (
    COLOR_BY_NAME,
    SpriteSpec,
    build_sprite_spec,
    render_girl_sprite_32,
)

FAMICOM_DNA_RENDER_MODE = "famicom_dna_sprite"
SPRITE_SIZE = 32


def _hair_color_key(raw: str) -> str:
    key = str(raw or "dark_navy").lower()
    if key in COLOR_BY_NAME:
        return key
    return "dark_navy"


def build_sprite_spec_from_dna(character_dna: dict[str, Any]) -> SpriteSpec:
    """DNA locked_features → ファミコン spec（髪色・アクセント RGB を反映）。"""
    locked = character_dna.get("locked_features") or {}
    hair_key = _hair_color_key(locked.get("hair_color", "dark_navy"))
    hair_rgb = HAIR_COLOR_RGB.get(locked.get("hair_color", ""), COLOR_BY_NAME[hair_key])
    accent_key = str(locked.get("accent_color") or "mint_green")
    accent_rgb = ACCENT_COLOR_RGB.get(accent_key, ACCENT_COLOR_RGB["mint_green"])

    accessory_raw = str(locked.get("accessory") or "star")
    accessory = "mint_green_star" if accessory_raw == "star" else accessory_raw

    hair_style = str(locked.get("hair_style") or "short_bob")
    if hair_style not in ("short_bob", "short", "long", "twin_tail"):
        hair_style = "short_bob"

    spec_dict: dict[str, Any] = {
        "gender": "girl",
        "hair_style": hair_style if hair_style != "twin_tail" else "short_bob",
        "hair_color": hair_key,
        "bangs": "straight",
        "face_shape": "round",
        "eye_style": "dot",
        "mouth": "none",
        "cheeks": bool(locked.get("cheeks", True)),
        "accessory": accessory,
        "top_color": "blue",
        "ribbon_color": "orange",
        "skirt_color": "grey",
        "shoe_color": "brown",
        "_hair_rgb": hair_rgb,
        "_accent_rgb": accent_rgb,
    }
    base = build_sprite_spec(spec_dict)
    return SpriteSpec(
        gender=base.gender,
        hair_style=base.hair_style,
        hair_rgb=hair_rgb,
        bangs=base.bangs,
        face_shape=base.face_shape,
        eye_style=base.eye_style,
        mouth=base.mouth,
        cheeks=base.cheeks,
        accessory=base.accessory if accessory == "mint_green_star" else accessory,
        accent_rgb=accent_rgb,
        top_rgb=base.top_rgb,
        ribbon_rgb=base.ribbon_rgb,
        skirt_rgb=base.skirt_rgb,
        shoe_rgb=base.shoe_rgb,
        skin_rgb=base.skin_rgb,
        cheek_rgb=base.cheek_rgb,
    )


def _validate_dna_sprite(pixel: Image.Image, stage: str) -> dict[str, Any]:
    """DNA 反映時は色バリエーションを許容する軽量チェック。"""
    w, h = pixel.size
    if w < 16 or h < 16:
        return {"passed": False, "issues": ["sprite_too_small"], "stage": stage, "retried": False}
    px = pixel.load()
    white = (255, 255, 255)
    colored = sum(1 for y in range(h) for x in range(w) if px[x, y] != white)
    if colored < 40:
        return {"passed": False, "issues": ["sprite_too_empty"], "stage": stage, "retried": False}
    return {"passed": True, "issues": [], "stage": stage, "retried": False}


def render_famicom_stage_from_dna(
    character_dna: dict[str, Any],
    stage: str,
) -> tuple[Image.Image, Image.Image, Image.Image, dict[str, Any]]:
    """
    DNA から 32×32 ファミコン chibi を描画し、ステージ装飾 → 512px 表示。
    戻り値: (base_sprite, pixel_sprite, display, validation_result)
    """
    if stage == "egg":
        base = build_egg_sprite(SPRITE_SIZE)
        pixel = base
        display = frame_sprite_display(pixel, stage)
        return base, pixel, display, {"passed": True, "issues": [], "stage": stage}

    sprite_spec = build_sprite_spec_from_dna(character_dna)
    base = render_girl_sprite_32(sprite_spec)
    if stage in ("baby", "egg"):
        pixel = base
    else:
        pixel = decorate_stage(base, stage)
    display = frame_sprite_display(pixel, stage)

    result = _validate_dna_sprite(pixel, stage)
    return base, pixel, display, result
