"""ファミコン DNA レンダラーの品質テスト。"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from app.services.character_dna import MANATOMO_DEFAULT_VISION, normalize_character_dna
from app.services.evolution_generator import generate_evolution_bundle
from app.services.famicom_dna_renderer import render_famicom_stage_from_dna
from app.services.famicom_sprite_common import BLACK, DISPLAY_SIZE, WHITE
from app.services.image_understanding import understand_image
from app.services.pixel_character_generator import generate_character_sprite_bundle


def _cute_face_png() -> bytes:
    img = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((70, 50, 186, 200), outline=(30, 30, 30), width=3)
    draw.ellipse((95, 95, 125, 125), fill=(30, 30, 30))
    draw.ellipse((145, 95, 175, 125), fill=(30, 30, 30))
    draw.arc((108, 130, 148, 155), 0, 180, fill=(30, 30, 30), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _face_black_ratio(display: Image.Image) -> float:
    """顔付近の黒ピクセル比率（ベクター量子化アーティファクト検知）。"""
    small = display.resize((32, 32))
    px = small.load()
    black = total = 0
    for y in range(8, 16):
        for x in range(10, 22):
            total += 1
            if px[x, y] == BLACK:
                black += 1
    return black / max(1, total)


def test_famicom_dna_render_full_body_not_face_blob():
    dna = normalize_character_dna(MANATOMO_DEFAULT_VISION)
    _, pixel, display, validation = render_famicom_stage_from_dna(dna, "baby")
    assert validation["passed"] is True
    assert pixel.size == (32, 32)
    assert display.size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert _face_black_ratio(display) < 0.35


def test_evolution_bundle_uses_famicom_renderer():
    u = understand_image(_cute_face_png())
    bundle = generate_evolution_bundle(u, stage_key="baby", save_file=False)
    meta = bundle["meta"]
    assert meta["render_mode"] == "famicom_dna_sprite"
    assert bundle["current_display"].size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert _face_black_ratio(bundle["current_display"]) < 0.35
    assert bundle.get("next_stage_preview") is not None
    assert bundle.get("final_hero_preview") is not None


def test_generate_bundle_clean_chibi():
    bundle = generate_character_sprite_bundle(_cute_face_png(), stage="child", save_file=False)
    display = bundle["current_display"]
    assert display.size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert _face_black_ratio(display) < 0.35
    corners = [display.getpixel((0, 0)), display.getpixel((511, 511))]
    for c in corners:
        assert c == WHITE or c[0] > 240
