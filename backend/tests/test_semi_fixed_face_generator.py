"""半固定テンプレート顔アイコン生成のテスト。"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from app.services.semi_fixed_face_generator import (
    GENERATION_MODE,
    compose_semi_fixed_face,
    extract_face_hints,
    generate_semi_fixed_evolution_bundle,
    semi_fixed_face_from_bytes,
)
from app.services.trace_pixelizer import BLACK, FAMICOM_PALETTE, GREEN, WHITE
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


def test_generation_mode_constant():
    assert GENERATION_MODE == "semi_fixed_face"


def test_semi_fixed_produces_32px_palette_sprite():
    sprite, hints, meta = semi_fixed_face_from_bytes(_face_with_mint_star_png())
    assert sprite.size == (32, 32)
    assert meta["generation_mode"] == "semi_fixed_face"
    assert hints.template in ("girl_bob", "boy_short", "round_neutral")
    colors = {sprite.getpixel((x, y)) for y in range(32) for x in range(32)}
    assert len(colors) <= 8
    assert all(c in set(FAMICOM_PALETTE.values()) for c in colors)
    assert BLACK in colors
    assert sprite.getpixel((0, 0)) == WHITE


def test_evolution_bundle():
    bundle = generate_semi_fixed_evolution_bundle(
        _cute_face_png(),
        stage_key="child",
        save_file=False,
    )
    assert bundle["meta"]["generation_mode"] == "semi_fixed_face"
    assert bundle["current_display"].size == (512, 512)
    assert bundle["next_stage_preview"] is not None
    assert bundle["final_hero_preview"] is not None


def test_compose_templates_distinct():
    from app.services.semi_fixed_face_generator import FaceHints

    girl = compose_semi_fixed_face(FaceHints(template="girl_bob"))
    boy = compose_semi_fixed_face(FaceHints(template="boy_short"))
    assert list(girl.getdata()) != list(boy.getdata())


def test_extract_picks_template_from_ink():
    from app.image_preprocess_algo import build_binary_scribble

    rgb = Image.open(io.BytesIO(_cute_face_png())).convert("RGB")
    line, _ = build_binary_scribble(rgb, famicom_pixels=False)
    hints = extract_face_hints(rgb, line)
    assert hints.template in ("girl_bob", "boy_short", "round_neutral")
