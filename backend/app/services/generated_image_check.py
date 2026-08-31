"""
生成ピクセル画像の DNA 一致チェック。不一致時は strict 再描画を 1 回だけ行う。
"""
from __future__ import annotations

from typing import Any

from PIL import Image

from .character_dna import ACCENT_COLOR_RGB, HAIR_COLOR_RGB, stage_spec_to_render_spec
from .base_character_generator import generate_base_character
from .pixel_art_converter import convert_to_pixel_art, upscale_to_display, DISPLAY_SIZE

WHITE = (255, 255, 255)
_BG_THRESHOLD = 235


def _is_background(rgb: tuple[int, int, int]) -> bool:
    return rgb[0] >= _BG_THRESHOLD and rgb[1] >= _BG_THRESHOLD and rgb[2] >= _BG_THRESHOLD


def _dominant_non_bg_colors(img: Image.Image, max_samples: int = 800) -> list[tuple[int, int, int]]:
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    counts: dict[tuple[int, int, int], int] = {}
    step = max(1, (w * h) // max_samples)
    n = 0
    for y in range(0, h, max(1, int(step**0.5))):
        for x in range(0, w, max(1, int(step**0.5))):
            c = px[x, y]
            if _is_background(c):
                continue
            counts[c] = counts.get(c, 0) + 1
            n += 1
    return sorted(counts, key=counts.get, reverse=True)  # type: ignore[arg-type]


def _color_near(a: tuple[int, int, int], b: tuple[int, int, int], tol: int = 48) -> bool:
    return all(abs(a[i] - b[i]) <= tol for i in range(3))


def _count_eye_like_blobs(img: Image.Image) -> int:
    """顔中央付近の暗色ブロブ数（目の近似）。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    y0, y1 = int(h * 0.28), int(h * 0.52)
    x0, x1 = int(w * 0.22), int(w * 0.78)
    visited: set[tuple[int, int]] = set()
    blobs = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in visited:
                continue
            c = px[x, y]
            if _is_background(c) or sum(c) > 200:
                continue
            blobs += 1
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited or cx < x0 or cx >= x1 or cy < y0 or cy >= y1:
                    continue
                cc = px[cx, cy]
                if _is_background(cc) or sum(cc) > 200:
                    continue
                visited.add((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    stack.append((cx + dx, cy + dy))
    return blobs


def _white_background_ratio(img: Image.Image) -> float:
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    white = 0
    for y in range(h):
        for x in range(w):
            if _is_background(px[x, y]):
                white += 1
    return white / max(1, w * h)


def _center_symmetry_score(img: Image.Image) -> float:
    """正面近似: 左右の非背景ピクセル数の比。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    mid = w // 2
    left = right = 0
    for y in range(h):
        for x in range(w):
            if _is_background(px[x, y]):
                continue
            if x < mid:
                left += 1
            elif x > mid:
                right += 1
    if left + right == 0:
        return 0.0
    return min(left, right) / max(left, right)


def _connected_character_regions(
    img: Image.Image,
    *,
    ignore_top_fraction: float = 0.0,
) -> int:
    """非背景の連結成分数（1体想定）。小さなアクセント装飾は除外。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    seen: set[tuple[int, int]] = set()
    regions = 0
    min_size = max(12, (w * h) // 80)
    y_min = int(h * ignore_top_fraction) if ignore_top_fraction else 0
    for y in range(h):
        for x in range(w):
            if y < y_min or (x, y) in seen or _is_background(px[x, y]):
                continue
            stack = [(x, y)]
            size = 0
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen or cx < 0 or cy < 0 or cx >= w or cy >= h:
                    continue
                if cy < y_min or _is_background(px[cx, cy]):
                    continue
                seen.add((cx, cy))
                size += 1
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    stack.append((cx + dx, cy + dy))
            if size >= min_size:
                regions += 1
    return regions


def _skin_visible_ratio(img: Image.Image) -> float:
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    skin_like = 0
    total = 0
    y0, y1 = int(h * 0.22), int(h * 0.55)
    x0, x1 = int(w * 0.25), int(w * 0.75)
    for y in range(y0, y1):
        for x in range(x0, x1):
            total += 1
            r, g, b = px[x, y]
            if r > 240 and g > 220 and b > 200 and not _is_background((r, g, b)):
                skin_like += 1
    return skin_like / max(1, total)


def validate_generated_image(
    img: Image.Image,
    character_dna: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    """
    チェック項目:
    - 髪色 / 髪型（近似） / 目2つ / 白背景 / 正面 / 1体 / アクセント / 顔露出
    """
    locked = character_dna["locked_features"]
    issues: list[str] = []

    pixel = img
    if img.size[0] > 96:
        pixel = img.resize((64, 64), Image.Resampling.NEAREST)

    colors = _dominant_non_bg_colors(pixel)
    expected_hair = HAIR_COLOR_RGB.get(locked["hair_color"], HAIR_COLOR_RGB["dark_navy"])
    if colors and not any(_color_near(c, expected_hair, tol=55) for c in colors[:6]):
        issues.append("hair_color_mismatch")

    hair_style = locked["hair_style"]
    top_ink = 0
    px = pixel.convert("RGB").load()
    w, h = pixel.size
    for x in range(w):
        if not _is_background(px[x, int(h * 0.08)]):
            top_ink += 1
    if hair_style in ("short_bob", "long", "twin_tail") and top_ink < 2:
        issues.append("hair_style_mismatch")
    if hair_style == "short" and top_ink > w // 2:
        issues.append("hair_style_mismatch")

    eye_blobs = _count_eye_like_blobs(pixel)
    if stage not in ("egg", "baby") and eye_blobs < 2:
        issues.append("eye_count_not_two")

    if _white_background_ratio(pixel) < 0.45:
        issues.append("background_not_white")

    if _center_symmetry_score(pixel) < 0.35:
        issues.append("not_front_view")

    body_regions = _connected_character_regions(pixel, ignore_top_fraction=0.12)
    if body_regions > 3:
        issues.append("multiple_characters")

    accent_key = locked.get("accent_color", "mint_green")
    if (
        stage not in ("egg", "baby")
        and locked.get("accessory") == "star"
        and accent_key != "none"
    ):
        expected_accent = ACCENT_COLOR_RGB.get(accent_key, ACCENT_COLOR_RGB["mint_green"])
        if colors and not any(_color_near(c, expected_accent, tol=60) for c in colors[:8]):
            issues.append("accent_color_missing")

    if _skin_visible_ratio(pixel) < 0.04:
        issues.append("face_hidden")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "stage": stage,
    }


def render_stage_with_spec(
    stage_spec: dict[str, Any],
    *,
    sprite: int,
    max_colors: int,
    strict: bool = False,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    render_spec = stage_spec_to_render_spec(stage_spec, strict=strict)
    base = generate_base_character(render_spec, canvas_size=sprite)
    pixel = convert_to_pixel_art(
        base,
        sprite_size=sprite,
        max_colors=max_colors,
        character_design_spec=render_spec,
    )
    display = upscale_to_display(pixel, DISPLAY_SIZE)
    return base, pixel, display


def validate_and_retry_once(
    base: Image.Image,
    pixel: Image.Image,
    display: Image.Image,
    character_dna: dict[str, Any],
    stage_spec: dict[str, Any],
    *,
    sprite: int,
    max_colors: int,
) -> tuple[Image.Image, Image.Image, Image.Image, dict[str, Any]]:
    """不一致なら strict で 1 回だけ再生成。"""
    validation = validate_generated_image(display, character_dna, stage_spec["stage"])
    if validation["passed"]:
        validation["retried"] = False
        return base, pixel, display, validation

    base2, pixel2, new_display = render_stage_with_spec(
        stage_spec,
        sprite=sprite,
        max_colors=max_colors,
        strict=True,
    )
    validation_retry = validate_generated_image(new_display, character_dna, stage_spec["stage"])
    validation_retry["retried"] = True
    validation_retry["first_issues"] = validation.get("issues", [])
    return base2, pixel2, new_display, validation_retry
