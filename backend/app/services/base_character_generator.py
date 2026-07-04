"""
character_design_spec → 2D デフォルメキャラ（高解像度）生成。
手書き画像はここでは使わない。
"""
from __future__ import annotations

from typing import Any

from PIL import Image

from PIL import ImageDraw

from .character_design_spec import COLOR_MAP
from .pixel_character_renderer import render_sprite_from_spec

BASE_CANVAS_SIZE = 256
WHITE_RGB = (255, 255, 255)


def build_egg_sprite(canvas_size: int = 32) -> Image.Image:
    outline = COLOR_MAP["outline"]
    shell = (245, 245, 240)
    spot = (72, 168, 88)
    canvas = Image.new("RGB", (canvas_size, canvas_size), WHITE_RGB)
    draw = ImageDraw.Draw(canvas)
    cx, cy = canvas_size // 2, int(canvas_size * 0.52)
    rx, ry = int(canvas_size * 0.28), int(canvas_size * 0.34)
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=shell, outline=outline, width=2)
    for ox, oy in ((-4, -6), (3, 2), (-2, 8)):
        s = max(canvas_size / 32, 1)
        draw.ellipse(
            (
                int(cx + ox * s - 2),
                int(cy + oy * s - 2),
                int(cx + ox * s + 2),
                int(cy + oy * s + 2),
            ),
            fill=spot,
        )
    return canvas


def generate_base_character(
    character_design_spec: dict[str, Any],
    *,
    canvas_size: int = BASE_CANVAS_SIZE,
) -> Image.Image:
    """
    設計書に基づき 2D chibi キャラを描画する（ドット化前）。
    """
    if character_design_spec.get("stage") == "egg":
        return build_egg_sprite(canvas_size)

    spec = {**character_design_spec}
    return render_sprite_from_spec(spec, canvas_size)
