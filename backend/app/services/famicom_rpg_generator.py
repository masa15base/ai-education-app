"""
元画像を参考にファミコンRPG風 32×32 正面向きキャラを生成する。

trace_pixelize / line_trace は使用しない。
固定 chibi テンプレ + 元画像から抽出した髪色・性別・服色を反映。
"""
from __future__ import annotations

import colorsys
import io
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from ..image_preprocess_algo import build_binary_scribble
from .character_sprite_designer import STAGES_ORDER, next_stage_after, _dominant_accent_rgb
from .famicom_sprite_common import (
    BLACK,
    BLUE,
    BROWN,
    DEFAULT_SPRITE_SIZE,
    DISPLAY_SIZE,
    GREEN,
    ORANGE,
    SKIN,
    WHITE,
    add_exterior_outline,
    decorate_stage,
    snap_to_palette,
    upscale_nearest,
)
from .sprite_quality_check import SpriteValidationResult, validate_famicom_sprite

GENERATION_MODE = "famicom_rpg_sprite"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"

RPG_FEATURES_JA: list[str] = [
    "元画像を参考にしたFC風キャラ",
    "32×32 正面向き",
    "髪型・服色を反映",
]


@dataclass
class RpgCharacterHints:
    gender: str = "girl"
    hair_style: str = "bob"
    hair_color: tuple[int, int, int] = BROWN
    outfit_color: tuple[int, int, int] = BLUE
    skin_color: tuple[int, int, int] = SKIN
    accent_color: tuple[int, int, int] | None = None
    mouth_style: str = "smile"
    has_cheeks: bool = True
    extras: dict[str, Any] = field(default_factory=dict)


def _luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _ink_mask(line: Image.Image, threshold: int = 185) -> list[list[bool]]:
    g = line.convert("L")
    px = g.load()
    w, h = g.size
    return [[px[x, y] < threshold for x in range(w)] for y in range(h)]


def _bbox_from_mask(mask: list[list[bool]]) -> tuple[int, int, int, int] | None:
    ys, xs = [], []
    for y, row in enumerate(mask):
        for x, on in enumerate(row):
            if on:
                ys.append(y)
                xs.append(x)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _region_ink_ratio(mask: list[list[bool]], x0: int, y0: int, x1: int, y1: int) -> float:
    total = ink = 0
    h = len(mask)
    w = len(mask[0]) if mask else 0
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            total += 1
            if mask[y][x]:
                ink += 1
    return ink / max(1, total)


def _dominant_warm_in_region(rgb: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    w, h = rgb.size
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    px = rgb.load()
    buckets: dict[tuple[int, int, int], int] = {}
    for y in range(y0, y1, 3):
        for x in range(x0, x1, 3):
            r, g, b = px[x, y]
            if _luminance(r, g, b) > 230 or _luminance(r, g, b) < 40:
                continue
            hh, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s < 0.12:
                continue
            if 0.02 <= hh <= 0.18 or hh >= 0.92:
                key = ORANGE if v >= 0.55 and s >= 0.2 else BROWN
                buckets[key] = buckets.get(key, 0) + 1
    return max(buckets, key=buckets.get) if buckets else BROWN


def _dominant_cool_in_region(rgb: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    w, h = rgb.size
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    px = rgb.load()
    buckets: dict[tuple[int, int, int], int] = {BLUE: 0}
    for y in range(y0, y1, 3):
        for x in range(x0, x1, 3):
            r, g, b = px[x, y]
            hh, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s >= 0.18 and 0.48 <= hh <= 0.72 and v >= 0.2:
                buckets[BLUE] = buckets.get(BLUE, 0) + 1
    return BLUE if buckets.get(BLUE, 0) > 0 else BLUE


def extract_rpg_hints(rgb: Image.Image, line: Image.Image) -> RpgCharacterHints:
    if line.size != rgb.size:
        line = line.resize(rgb.size, Image.Resampling.NEAREST)
    hints = RpgCharacterHints()
    mask = _ink_mask(line)
    bbox = _bbox_from_mask(mask)
    w, h = rgb.size

    if bbox:
        x0, y0, x1, y1 = bbox
        fw, fh = x1 - x0, y1 - y0
        aspect = fw / max(1, fh)
        side_l = _region_ink_ratio(mask, x0, y0, x0 + fw // 4, y0 + int(fh * 0.5))
        side_r = _region_ink_ratio(mask, x1 - fw // 4, y0, x1, y0 + int(fh * 0.5))
        top = _region_ink_ratio(mask, x0, y0, x1, y0 + int(fh * 0.32))

        if aspect > 0.92 and top > 0.04 and side_l + side_r < 0.07:
            hints.gender = "boy"
            hints.hair_style = "short"
        elif side_l + side_r > top * 1.1 and side_l + side_r > 0.06:
            hints.gender = "girl"
            hints.hair_style = "bob"
        else:
            hints.gender = "girl"
            hints.hair_style = "long" if fh > fw * 1.05 else "bob"

        hair_box = (x0, y0, x1, min(h, y0 + int(fh * 0.48)))
        body_box = (x0, y0 + int(fh * 0.45), x1, y1)
        hints.hair_color = _dominant_warm_in_region(rgb, hair_box)
        hints.outfit_color = _dominant_cool_in_region(rgb, body_box)

        mouth_ratio = _region_ink_ratio(mask, x0 + fw // 4, y0 + int(fh * 0.52), x1 - fw // 4, y1)
        hints.mouth_style = "smile" if mouth_ratio > 0.012 else "neutral"
        hints.has_cheeks = hints.mouth_style == "smile"
    else:
        hints.gender = "girl"
        hints.hair_style = "bob"

    accent = _dominant_accent_rgb(rgb)
    if accent:
        ah, acs, _ = colorsys.rgb_to_hsv(accent[0] / 255, accent[1] / 255, accent[2] / 255)
        if acs >= 0.35:
            hints.accent_color = GREEN if ah < 0.48 else BLUE

    hints.extras = {"bbox": bbox}
    return hints


def _px(img: Image.Image, x: int, y: int, c: tuple[int, int, int]) -> None:
    if 0 <= x < img.size[0] and 0 <= y < img.size[1]:
        img.putpixel((x, y), c)


def _fill_ellipse(img: Image.Image, cx: int, cy: int, rx: int, ry: int, fill: tuple[int, int, int]) -> None:
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / max(1, rx)) ** 2 + ((y - cy) / max(1, ry)) ** 2 <= 1.05:
                _px(img, x, y, fill)


def _stroke_ellipse(img: Image.Image, cx: int, cy: int, rx: int, ry: int) -> None:
    for y in range(cy - ry - 1, cy + ry + 2):
        for x in range(cx - rx - 1, cx + rx + 2):
            dx = (x - cx) / max(1, rx)
            dy = (y - cy) / max(1, ry)
            d = dx * dx + dy * dy
            if 0.82 <= d <= 1.2:
                _px(img, x, y, BLACK)


def _draw_eyes(img: Image.Image, y: int) -> None:
    for ex in (11, 20):
        _px(img, ex, y, BLACK)
        _px(img, ex + 1, y, BLACK)
        _px(img, ex, y + 1, WHITE)


def _draw_mouth(img: Image.Image, y: int, style: str) -> None:
    if style == "smile":
        for dx in (-1, 0, 1):
            _px(img, 16 + dx, y, BLACK)
    else:
        _px(img, 15, y, BLACK)
        _px(img, 16, y, BLACK)


def _draw_body_girl(img: Image.Image, outfit: tuple[int, int, int]) -> None:
    for y in range(22, 30):
        for x in range(10, 22):
            _px(img, x, y, outfit)
    for x in range(9, 23):
        _px(img, x, 21, BLACK)
    for x in (9, 22):
        for y in range(21, 30):
            _px(img, x, y, BLACK)
    _px(img, 9, 29, BLACK)
    _px(img, 22, 29, BLACK)


def _draw_body_boy(img: Image.Image, outfit: tuple[int, int, int]) -> None:
    for y in range(22, 30):
        for x in range(10, 22):
            _px(img, x, y, outfit)
    for x in range(9, 23):
        _px(img, x, 21, BLACK)
    for x in (9, 22):
        for y in range(21, 30):
            _px(img, x, y, BLACK)
    _px(img, 16, 23, ORANGE)
    _px(img, 16, 24, ORANGE)


def _compose_girl(img: Image.Image, hints: RpgCharacterHints, s: int) -> None:
    hc = hints.hair_color
    _fill_ellipse(img, s // 2, 10, 11, 9, hc)
    if hints.hair_style == "long":
        for y in range(8, 24):
            _px(img, 7, y, hc)
            _px(img, 8, y, hc)
            _px(img, s - 8, y, hc)
            _px(img, s - 9, y, hc)
    for x in range(8, 24):
        _px(img, x, 8, hc)
        _px(img, x, 9, hc)
    _fill_ellipse(img, s // 2, 15, 7, 7, hints.skin_color)
    _stroke_ellipse(img, s // 2, 15, 7, 7)
    _draw_eyes(img, 13)
    if hints.has_cheeks:
        _px(img, 10, 17, ORANGE)
        _px(img, 21, 17, ORANGE)
    _draw_mouth(img, 18, hints.mouth_style)
    _draw_body_girl(img, hints.outfit_color)


def _compose_boy(img: Image.Image, hints: RpgCharacterHints, s: int) -> None:
    hc = hints.hair_color
    for x in range(9, 23):
        for y in range(4, 10):
            if abs(x - s // 2) <= 7 - (y - 4):
                _px(img, x, y, hc)
    _fill_ellipse(img, s // 2, 15, 7, 7, hints.skin_color)
    _stroke_ellipse(img, s // 2, 15, 7, 7)
    _draw_eyes(img, 13)
    _draw_mouth(img, 18, hints.mouth_style)
    _draw_body_boy(img, hints.outfit_color)


def compose_rpg_sprite(hints: RpgCharacterHints, sprite_size: int = DEFAULT_SPRITE_SIZE) -> Image.Image:
    s = max(16, min(32, sprite_size))
    img = Image.new("RGB", (s, s), WHITE)
    if hints.gender == "boy":
        _compose_boy(img, hints, s)
    else:
        _compose_girl(img, hints, s)
    if hints.accent_color:
        _px(img, s - 4, 3, hints.accent_color)
        _px(img, s - 3, 2, hints.accent_color)
        _px(img, s - 2, 3, hints.accent_color)
    out = snap_to_palette(img)
    return add_exterior_outline(out)


def generate_rpg_sprite_from_bytes(
    image_bytes: bytes,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> tuple[Image.Image, RpgCharacterHints, SpriteValidationResult, dict[str, Any]]:
    rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    line, preprocess_meta = build_binary_scribble(rgb, max_edge=512, famicom_pixels=False)
    hints = extract_rpg_hints(rgb, line)
    sprite = compose_rpg_sprite(hints, sprite_size=sprite_size)
    validation = validate_famicom_sprite(sprite)
    meta: dict[str, Any] = {
        "generation_mode": GENERATION_MODE,
        "render_mode": GENERATION_MODE,
        "sprite_size": sprite.size[0],
        "display_size": DISPLAY_SIZE,
        "preprocess": preprocess_meta,
        "character_hints": {
            "gender": hints.gender,
            "hair_style": hints.hair_style,
            "hair_color": hints.hair_color,
            "outfit_color": hints.outfit_color,
            "mouth_style": hints.mouth_style,
        },
        "validation_result": {
            "passed": validation.passed,
            "issues": validation.issues,
            "metrics": validation.metrics,
        },
        "pipeline": [
            "reference_image_analysis",
            "rpg_chibi_template_compose",
            "quality_validation",
            "nearest_upscale_512",
        ],
    }
    return sprite, hints, validation, meta


def generate_rpg_evolution_bundle(
    image_bytes: bytes,
    *,
    stage_key: str,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
    force_egg: bool = False,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> dict[str, Any]:
    _ = character_profile
    if force_egg:
        stage_key = "egg"
    else:
        stage_key = stage_key if stage_key in STAGES_ORDER else "baby"
        if stage_key == "egg":
            stage_key = "baby"

    base_sprite, hints, validation, base_meta = generate_rpg_sprite_from_bytes(
        image_bytes, sprite_size=sprite_size
    )
    if not validation.passed:
        raise ValueError(
            "sprite quality check failed: " + "; ".join(validation.issues)
        )

    current_sprite = decorate_stage(base_sprite, stage_key)
    current_display = upscale_nearest(current_sprite)

    nxt = next_stage_after(stage_key)
    next_display = None
    if nxt and nxt != "egg":
        next_sprite = decorate_stage(base_sprite, nxt)
        next_display = upscale_nearest(next_sprite)

    hero_sprite = decorate_stage(base_sprite, "hero")
    hero_display = upscale_nearest(hero_sprite)

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"rpg_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")

    understanding = {
        "source": GENERATION_MODE,
        "raw_features": base_meta.get("character_hints", {}),
        "vision_api_status": "skipped",
        "render_mode": GENERATION_MODE,
    }

    meta: dict[str, Any] = {
        **base_meta,
        "stage": stage_key,
        "next_stage": nxt,
        "signature_features_ja": RPG_FEATURES_JA,
        "image_understanding": understanding,
        "vision_result": None,
        "character_dna": None,
        "parts_dna": None,
        "saved_path": saved_path,
    }

    return {
        "image_understanding": understanding,
        "character_dna": None,
        "parts_dna": None,
        "current_sprite": current_sprite,
        "current_display": current_display,
        "next_stage_preview": next_display,
        "final_hero_preview": hero_display,
        "current_stage_image": current_display,
        "meta": meta,
        "saved_path": saved_path,
    }


__all__ = [
    "GENERATION_MODE",
    "RpgCharacterHints",
    "compose_rpg_sprite",
    "extract_rpg_hints",
    "generate_rpg_evolution_bundle",
    "generate_rpg_sprite_from_bytes",
]
