"""
2D ベースキャラ → ファミコン風ドット絵変換。
手書き画像は入力しない（base_character_generator の出力のみ）。
"""
from __future__ import annotations

from typing import Any

from PIL import Image

WHITE_RGB: tuple[int, int, int] = (255, 255, 255)
DISPLAY_SIZE = 512


def _is_background(r: int, g: int, b: int) -> bool:
    return r > 235 and g > 235 and b > 235


def _palette_from_spec(spec: dict[str, Any]) -> list[tuple[int, int, int]]:
    pal = spec.get("palette") or {}
    colors: list[tuple[int, int, int]] = [WHITE_RGB]
    for key in (
        "outline",
        "hair",
        "hair_hi",
        "skin",
        "skin_shadow",
        "cheek",
        "eye_white",
        "eye_pupil",
        "accent",
        "shirt",
        "shirt_shadow",
        "gold",
        "cape",
        "glow",
    ):
        c = pal.get(key)
        if c and tuple(c) not in colors:
            colors.append(tuple(c))
    return colors[:16]


def _quantize(img: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    bg = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if _is_background(*px[x, y]):
                px[x, y] = WHITE_RGB
                bg[y][x] = True

    unique: list[tuple[int, int, int]] = [WHITE_RGB]
    for c in palette:
        if c != WHITE_RGB and c not in unique:
            unique.append(c)
    flat: list[int] = []
    for c in unique:
        flat.extend(c)
    while len(flat) < 768:
        flat.extend(WHITE_RGB)
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(flat[:768])
    q = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE).convert("RGB")
    out = q.load()
    for y in range(h):
        for x in range(w):
            if bg[y][x]:
                out[x, y] = WHITE_RGB
    return q


def _reinforce_outline(img: Image.Image, outline: tuple[int, int, int]) -> Image.Image:
    """縮小後の輪郭を補正。"""
    src = img.convert("RGB")
    w, h = src.size
    px = src.load()
    out = src.copy()
    opx = out.load()
    for y in range(h):
        for x in range(w):
            if not _is_background(*px[x, y]):
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not _is_background(*px[nx, ny]):
                    opx[x, y] = outline
                    break
    return out


def convert_to_pixel_art(
    base_character: Image.Image,
    *,
    sprite_size: int = 32,
    max_colors: int = 8,
    character_design_spec: dict[str, Any] | None = None,
) -> Image.Image:
    """
    2D キャラを sprite_size に縮小し、色数制限・輪郭補正を行う。
  手書きの直接縮小は行わない。
    """
    spec = character_design_spec or {}
    palette = _palette_from_spec(spec)[: max(3, max_colors)]
    outline = tuple(spec.get("palette", {}).get("outline", (34, 34, 34)))

    src = base_character.convert("RGB")
    if src.size == (sprite_size, sprite_size):
        # 既にスプライト解像度で描画済み → 縮小せず量子化のみ
        pixel = src
    else:
        smooth = src.resize((sprite_size, sprite_size), Image.Resampling.LANCZOS)
        pixel = smooth.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)
    pixel = _quantize(pixel, palette)
    pixel = _reinforce_outline(pixel, outline)
    return pixel


def upscale_to_display(
    pixel_sprite: Image.Image, display_size: int = DISPLAY_SIZE
) -> Image.Image:
    """ドットスプライトを NEAREST で 512px に拡大。"""
    return pixel_sprite.resize((display_size, display_size), Image.Resampling.NEAREST)
