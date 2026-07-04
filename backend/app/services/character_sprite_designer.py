"""
手書き線画の視覚特徴を抽象化し、ファミコン風スプライトの設計仕様を生成する。
元画像を縮小せず、パーツ構成として再設計する。
"""
from __future__ import annotations

import colorsys
from typing import Any

from PIL import Image, ImageOps

STAGES_ORDER: tuple[str, ...] = ("egg", "baby", "child", "student", "hero")


def _ensure_black_ink_on_white(line_img: Image.Image) -> Image.Image:
    g = line_img.convert("L")
    hist = g.histogram()
    total = max(1, sum(hist))
    mean_l = sum(i * hist[i] for i in range(256)) / total
    if mean_l < 128:
        return ImageOps.invert(g)
    return g


def _ink_mask(g: Image.Image, threshold: int = 200) -> list[list[bool]]:
    w, h = g.size
    px = g.load()
    return [[px[x, y] < threshold for x in range(w)] for y in range(h)]


def _bbox_from_mask(mask: list[list[bool]]) -> tuple[int, int, int, int] | None:
    h = len(mask)
    if not h:
        return None
    w = len(mask[0])
    ys, xs = [], []
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                ys.append(y)
                xs.append(x)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _region_ink_ratio(
    mask: list[list[bool]], x0: int, y0: int, x1: int, y1: int
) -> float:
    total = 0
    ink = 0
    for y in range(y0, y1):
        if y < 0 or y >= len(mask):
            continue
        for x in range(x0, x1):
            if x < 0 or x >= len(mask[0]):
                continue
            total += 1
            if mask[y][x]:
                ink += 1
    return ink / max(1, total)


def _dominant_accent_rgb(rgb: Image.Image) -> tuple[int, int, int] | None:
    """線画以外の彩度のある色（緑系アクセント等）を検出。"""
    px = rgb.convert("RGB").load()
    w, h = rgb.size
    buckets: dict[tuple[int, int, int], int] = {}
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if r > 240 and g > 240 and b > 240:
                continue
            if r < 40 and g < 40 and b < 40:
                continue
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s < 0.18 or v < 0.25:
                continue
            key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
            buckets[key] = buckets.get(key, 0) + 1
    if not buckets:
        return None
    return max(buckets, key=buckets.get)


def _eye_size_score(mask: list[list[bool]], fx0: int, fy0: int, fx1: int, fy1: int) -> float:
    """顔上半分のインク密度から目の大きさを推定。"""
    fh = max(1, fy1 - fy0)
    eye_y1 = fy0 + int(fh * 0.55)
    ratio = _region_ink_ratio(mask, fx0, fy0, fx1, eye_y1)
    if ratio > 0.12:
        return 1.0
    if ratio > 0.07:
        return 0.65
    return 0.35


def extract_visual_features(
    line_img: Image.Image, rgb_source: Image.Image | None = None
) -> dict[str, Any]:
    from .image_understanding import understand_image_from_pil

    return understand_image_from_pil(line_img, rgb_source)["raw_features"]


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _hex_to_rgb(h: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    s = (h or "").strip().lstrip("#")
    if len(s) != 6:
        return fallback
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError:
        return fallback


def design_character_sprite(features: dict[str, Any], stage: str) -> dict[str, Any]:
    """後方互換: character_design_spec を返す。"""
    from .character_design_spec import build_character_design_spec, build_image_analysis

    stage = stage if stage in STAGES_ORDER else "baby"
    understanding = {
        "raw_features": features,
        "analysis": build_image_analysis(features),
    }
    return build_character_design_spec(understanding, stage=stage)


def _stage_decor(stage: str) -> str | None:
    return {
        "egg": "egg",
        "baby": "sprout",
        "child": "sprout",
        "student": "study",
        "hero": "hero",
    }.get(stage)


def next_stage_after(stage: str) -> str | None:
    try:
        i = STAGES_ORDER.index(stage)
    except ValueError:
        return "baby"
    if i >= len(STAGES_ORDER) - 1:
        return None
    return STAGES_ORDER[i + 1]


def parse_palette_color(design: dict[str, Any], key: str) -> tuple[int, int, int]:
    pal = design.get("palette") or {}
    if key in pal:
        return tuple(pal[key])
    return _hex_to_rgb((design.get("main_colors") or ["#222222"])[0], (34, 34, 34))
