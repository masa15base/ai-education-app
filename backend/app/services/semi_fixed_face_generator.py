"""
半固定テンプレート方式の FC 顔アイコン生成。

元絵から色・目口位置・髪型ヒントを抽出し、
32×32 の決められた顔テンプレートに載せる（別キャラの全身合成はしない）。
"""
from __future__ import annotations

import colorsys
import io
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps

from ..image_preprocess_algo import build_binary_scribble
from .character_sprite_designer import STAGES_ORDER, next_stage_after, _dominant_accent_rgb
from .trace_pixelizer import (
    BLACK,
    BLUE,
    BROWN,
    DEFAULT_SPRITE_SIZE,
    DISPLAY_SIZE,
    GREEN,
    ORANGE,
    SKIN,
    WHITE,
    _add_exterior_outline,
    _decorate_stage,
    _snap_to_palette,
    _upscale_nearest,
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"

GENERATION_MODE = "semi_fixed_face"


@dataclass
class FaceHints:
    template: str = "girl_bob"
    hair_color: tuple[int, int, int] = BROWN
    skin_color: tuple[int, int, int] = SKIN
    accent_color: tuple[int, int, int] | None = GREEN
    has_star: bool = True
    has_cheeks: bool = True
    eye_y_shift: int = 0
    mouth_style: str = "smile"
    star_corner: str = "top_right"
    trace_ink_ratio: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)


def _luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _map_warm_to_hair(r: int, g: int, b: int) -> tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if v >= 0.55 and s >= 0.2:
        return ORANGE
    return BROWN


def _map_accent_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    if 0.48 <= h <= 0.72 and s >= 0.15:
        return BLUE
    return GREEN


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


def _region_ink_ratio(
    mask: list[list[bool]], x0: int, y0: int, x1: int, y1: int
) -> float:
    total = ink = 0
    h = len(mask)
    w = len(mask[0]) if mask else 0
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            total += 1
            if mask[y][x]:
                ink += 1
    return ink / max(1, total)


def _ink_centroid(
    mask: list[list[bool]], x0: int, y0: int, x1: int, y1: int
) -> tuple[float, float] | None:
    sx = sy = n = 0
    h = len(mask)
    w = len(mask[0]) if mask else 0
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            if mask[y][x]:
                sx += x
                sy += y
                n += 1
    if n < 3:
        return None
    return sx / n, sy / n


def _dominant_warm_in_region(rgb: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    w, h = rgb.size
    x0, y0, x1, y1 = box
    x0 = max(0, min(w, x0))
    y0 = max(0, min(h, y0))
    x1 = max(x0 + 1, min(w, x1))
    y1 = max(y0 + 1, min(h, y1))
    px = rgb.load()
    buckets: dict[tuple[int, int, int], int] = {}
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b = px[x, y]
            if _luminance(r, g, b) > 230 or _luminance(r, g, b) < 45:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s < 0.12:
                continue
            if 0.02 <= h <= 0.18 or h >= 0.92:
                key = _map_warm_to_hair(r, g, b)
                buckets[key] = buckets.get(key, 0) + 1
    if not buckets:
        return BROWN
    return max(buckets, key=buckets.get)


def extract_face_hints(rgb: Image.Image, line: Image.Image) -> FaceHints:
    """元絵 + 線画からテンプレート用ヒントを抽出。"""
    if line.size != rgb.size:
        line = line.resize(rgb.size, Image.Resampling.NEAREST)
    w, h = rgb.size
    mask = _ink_mask(line)
    bbox = _bbox_from_mask(mask)
    hints = FaceHints()

    if bbox:
        x0, y0, x1, y1 = bbox
        fw, fh = x1 - x0, y1 - y0
        hints.trace_ink_ratio = _region_ink_ratio(mask, x0, y0, x1, y1)

        side_l = _region_ink_ratio(mask, x0, y0, x0 + fw // 4, y0 + int(fh * 0.55))
        side_r = _region_ink_ratio(mask, x1 - fw // 4, y0, x1, y0 + int(fh * 0.55))
        top = _region_ink_ratio(mask, x0, y0, x1, y0 + int(fh * 0.35))

        if side_l + side_r > top * 1.2 and side_l + side_r > 0.08:
            hints.template = "girl_bob"
        elif top > 0.06 and side_l + side_r < 0.06:
            hints.template = "boy_short"
        else:
            hints.template = "round_neutral"

        eye_y0 = y0 + int(fh * 0.25)
        eye_y1 = y0 + int(fh * 0.55)
        left_c = _ink_centroid(mask, x0, eye_y0, x0 + fw // 2, eye_y1)
        right_c = _ink_centroid(mask, x0 + fw // 2, eye_y0, x1, eye_y1)
        if left_c and right_c:
            avg_eye_y = (left_c[1] + right_c[1]) / 2
            face_mid_y = y0 + fh * 0.42
            shift = int(round((avg_eye_y - face_mid_y) / max(1, fh * 0.08)))
            hints.eye_y_shift = max(-1, min(1, shift))

        mouth_ratio = _region_ink_ratio(
            mask, x0 + fw // 4, y0 + int(fh * 0.55), x1 - fw // 4, y1
        )
        hints.mouth_style = "smile" if mouth_ratio > 0.015 else "neutral"

        hair_box = (x0, y0, x1, min(h, y0 + int(fh * 0.5)))
        hints.hair_color = _dominant_warm_in_region(rgb, hair_box)
    else:
        hints.template = "girl_bob"

    accent = _dominant_accent_rgb(rgb)
    if accent:
        hints.accent_color = _map_accent_rgb(accent)
        hints.has_star = hints.accent_color == GREEN
    else:
        hints.has_star = False
        hints.accent_color = None

    hints.has_cheeks = hints.mouth_style == "smile"
    hints.extras = {
        "template_reason": hints.template,
        "bbox": bbox,
    }
    return hints


def _px(img: Image.Image, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < img.size[0] and 0 <= y < img.size[1]:
        img.putpixel((x, y), color)


def _fill_ellipse_pixels(
    img: Image.Image,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    fill: tuple[int, int, int],
) -> None:
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / max(1, rx)) ** 2 + ((y - cy) / max(1, ry)) ** 2 <= 1.0:
                _px(img, x, y, fill)


def _stroke_ellipse_pixels(
    img: Image.Image,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    color: tuple[int, int, int] = BLACK,
) -> None:
    for y in range(cy - ry - 1, cy + ry + 2):
        for x in range(cx - rx - 1, cx + rx + 2):
            dx = (x - cx) / max(1, rx)
            dy = (y - cy) / max(1, ry)
            d = dx * dx + dy * dy
            if 0.82 <= d <= 1.18:
                _px(img, x, y, color)


def _draw_eyes(img: Image.Image, left_x: int, right_x: int, y: int, large: bool) -> None:
    if large:
        for ex in (left_x, right_x):
            _px(img, ex, y, BLACK)
            _px(img, ex + 1, y, BLACK)
            _px(img, ex, y + 1, WHITE)
    else:
        for ex in (left_x, right_x):
            _px(img, ex, y, BLACK)


def _draw_mouth(img: Image.Image, cx: int, y: int, style: str) -> None:
    if style == "smile":
        for dx in (-1, 0, 1):
            _px(img, cx + dx, y, BLACK)
        _px(img, cx - 1, y - 1, BLACK)
        _px(img, cx + 1, y - 1, BLACK)
    elif style == "neutral":
        _px(img, cx, y, BLACK)
        _px(img, cx + 1, y, BLACK)


def _draw_star(img: Image.Image, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    pts = [
        (cx, cy - 2),
        (cx + 1, cy),
        (cx + 2, cy - 1),
        (cx + 1, cy + 1),
        (cx + 2, cy + 2),
        (cx, cy + 1),
        (cx - 2, cy + 2),
        (cx - 1, cy + 1),
        (cx - 2, cy - 1),
        (cx - 1, cy),
    ]
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        draw = ImageDraw.Draw(img)
        draw.line([x0, y0, x1, y1], fill=BLACK)
    for x, y in pts[::2]:
        _px(img, x, y, color)


def _compose_girl_bob(img: Image.Image, hints: FaceHints, s: int) -> None:
    hc = hints.hair_color
    _fill_ellipse_pixels(img, s // 2, 11, 11, 10, hc)
    _fill_ellipse_pixels(img, s // 2, 18, 8, 9, hints.skin_color)
    _stroke_ellipse_pixels(img, s // 2, 18, 8, 9)
    for x in range(9, 24):
        _px(img, x, 11, hc)
        _px(img, x, 12, hc)
    eye_y = 16 + hints.eye_y_shift
    _draw_eyes(img, 11, 20, eye_y, large=True)
    if hints.has_cheeks:
        _px(img, 9, 20, ORANGE)
        _px(img, 22, 20, ORANGE)
    _draw_mouth(img, s // 2, 22, hints.mouth_style)


def _compose_boy_short(img: Image.Image, hints: FaceHints, s: int) -> None:
    hc = hints.hair_color
    for x in range(10, 23):
        for y in range(6, 11):
            if abs(x - s // 2) <= 6 - (y - 6):
                _px(img, x, y, hc)
    _fill_ellipse_pixels(img, s // 2, 18, 8, 9, hints.skin_color)
    _stroke_ellipse_pixels(img, s // 2, 18, 8, 9)
    eye_y = 16 + hints.eye_y_shift
    _draw_eyes(img, 12, 20, eye_y, large=False)
    _draw_mouth(img, s // 2, 22, hints.mouth_style)


def _compose_round_neutral(img: Image.Image, hints: FaceHints, s: int) -> None:
    hc = hints.hair_color
    _fill_ellipse_pixels(img, s // 2, 12, 10, 8, hc)
    _fill_ellipse_pixels(img, s // 2, 18, 9, 9, hints.skin_color)
    _stroke_ellipse_pixels(img, s // 2, 18, 9, 9)
    eye_y = 16 + hints.eye_y_shift
    _draw_eyes(img, 11, 20, eye_y, large=True)
    _draw_mouth(img, s // 2, 22, hints.mouth_style)


def compose_semi_fixed_face(hints: FaceHints, sprite_size: int = DEFAULT_SPRITE_SIZE) -> Image.Image:
    """ヒント + テンプレート → 32×32 顔アイコン。"""
    s = max(16, min(32, sprite_size))
    img = Image.new("RGB", (s, s), WHITE)
    composers = {
        "girl_bob": _compose_girl_bob,
        "boy_short": _compose_boy_short,
        "round_neutral": _compose_round_neutral,
    }
    composers.get(hints.template, _compose_girl_bob)(img, hints, s)

    if hints.has_star and hints.accent_color:
        _draw_star(img, s - 5, 4, hints.accent_color)

    img = _snap_to_palette(img)
    return _add_exterior_outline(img)


def semi_fixed_face_from_bytes(
    image_bytes: bytes,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> tuple[Image.Image, FaceHints, dict[str, Any]]:
    rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    line, preprocess_meta = build_binary_scribble(rgb, max_edge=512, famicom_pixels=False)
    hints = extract_face_hints(rgb, line)
    sprite = compose_semi_fixed_face(hints, sprite_size=sprite_size)
    meta = {
        "generation_mode": GENERATION_MODE,
        "render_mode": GENERATION_MODE,
        "sprite_size": sprite.size[0],
        "template": hints.template,
        "hair_color": hints.hair_color,
        "accent_color": hints.accent_color,
        "mouth_style": hints.mouth_style,
        "eye_y_shift": hints.eye_y_shift,
        "preprocess": preprocess_meta,
        "pipeline": [
            "binary_scribble_extract",
            "face_hint_extraction",
            "semi_fixed_template_compose",
            "8_color_quantize",
            "1px_black_outline",
            "nearest_upscale_512",
        ],
    }
    return sprite, hints, meta


SEMI_FIXED_FEATURES_JA: list[str] = [
    "元の絵から色と形のヒントを反映",
    "32×32 顔アイコンテンプレ",
    "8色・1px黒アウトライン",
]


def generate_semi_fixed_evolution_bundle(
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

    base_sprite, hints, base_meta = semi_fixed_face_from_bytes(
        image_bytes,
        sprite_size=sprite_size,
    )

    current_sprite = _decorate_stage(base_sprite, stage_key)
    current_display = _upscale_nearest(current_sprite, DISPLAY_SIZE)

    nxt = next_stage_after(stage_key)
    next_display = None
    if nxt and nxt != "egg":
        next_sprite = _decorate_stage(base_sprite, nxt)
        next_display = _upscale_nearest(next_sprite, DISPLAY_SIZE)

    hero_sprite = _decorate_stage(base_sprite, "hero")
    hero_display = _upscale_nearest(hero_sprite, DISPLAY_SIZE)

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"semiface_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")
        hero_display.save(dest / f"semiface_hero_{tag}.png", format="PNG")
        if next_display is not None and nxt:
            next_display.save(dest / f"semiface_{nxt}_{tag}.png", format="PNG")

    understanding = {
        "source": GENERATION_MODE,
        "raw_features": {
            "template": hints.template,
            "mouth_style": hints.mouth_style,
            "has_star": hints.has_star,
            "hair_color_rgb": hints.hair_color,
        },
        "vision_api_status": "skipped",
        "render_mode": GENERATION_MODE,
    }

    meta: dict[str, Any] = {
        **base_meta,
        "stage": stage_key,
        "next_stage": nxt,
        "signature_features_ja": SEMI_FIXED_FEATURES_JA,
        "image_understanding": understanding,
        "face_hints": {
            "template": hints.template,
            "mouth_style": hints.mouth_style,
            "eye_y_shift": hints.eye_y_shift,
            "has_star": hints.has_star,
        },
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
    "FaceHints",
    "GENERATION_MODE",
    "compose_semi_fixed_face",
    "extract_face_hints",
    "generate_semi_fixed_evolution_bundle",
    "semi_fixed_face_from_bytes",
]
