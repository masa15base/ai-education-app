"""trace_pixelize（構図保持・FC 8色仕様）のテスト。"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from app.services.trace_pixelizer import (
    BLACK,
    DEFAULT_SPRITE_SIZE,
    FAMICOM_PALETTE,
    GREEN,
    MAX_PALETTE_COLORS,
    WHITE,
    generate_trace_evolution_bundle,
    trace_pixelize_character,
    trace_pixelize_from_bytes,
    trace_pixelize_pil,
)
from tests.test_image_pipeline import _cute_face_png


def _face_with_mint_star_png() -> bytes:
    img = Image.new("RGB", (200, 220), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 40, 150, 160], outline=(30, 30, 40), width=3)
    draw.ellipse([75, 85, 95, 105], fill=(30, 30, 40))
    draw.ellipse([105, 85, 125, 105], fill=(30, 30, 40))
    draw.arc([80, 115, 120, 140], 20, 160, fill=(30, 30, 40), width=2)
    draw.polygon(
        [(165, 30), (172, 48), (190, 48), (176, 58), (182, 76), (165, 66), (148, 76), (154, 58), (140, 48), (158, 48)],
        fill=(85, 221, 204),
        outline=(20, 20, 30),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_default_sprite_size_is_32():
    assert DEFAULT_SPRITE_SIZE == 32
    assert len(FAMICOM_PALETTE) == MAX_PALETTE_COLORS


def test_trace_pixelize_famicom_palette_and_outline():
    sprite, display, meta = trace_pixelize_from_bytes(_face_with_mint_star_png())
    assert sprite.size == (32, 32)
    assert display.size == (512, 512)
    assert meta["generation_mode"] == "trace_pixelize"
    assert meta["max_colors"] == 8
    assert display.getpixel((0, 0)) == WHITE
    colors = {sprite.getpixel((x, y)) for y in range(32) for x in range(32)}
    assert len(colors) <= 8
    assert all(c in set(FAMICOM_PALETTE.values()) for c in colors)
    assert BLACK in colors
    assert GREEN in colors


def test_trace_evolution_same_base():
    bundle = generate_trace_evolution_bundle(
        _cute_face_png(),
        stage_key="baby",
        save_file=False,
    )
    assert bundle["meta"]["sprite_size"] == 32
    cur = bundle["current_display"]
    hero = bundle["final_hero_preview"]
    assert cur.size == (512, 512)
    assert hero is not None


def test_trace_pixelize_character_saves_file(tmp_path):
    src = tmp_path / "input.png"
    src.write_bytes(_face_with_mint_star_png())
    out = trace_pixelize_character(str(src), str(tmp_path / "out"))
    assert out.endswith(".png")


def test_no_mass_face_fill():
    img = Image.new("RGB", (120, 120), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 100, 100], outline=(20, 20, 30), width=2)
    sprite, _ = trace_pixelize_pil(img, sprite_size=32)
    colors = list(sprite.getdata())
    black = sum(1 for p in colors if p == BLACK)
    white = sum(1 for p in colors if p == WHITE)
    assert white > black * 2
