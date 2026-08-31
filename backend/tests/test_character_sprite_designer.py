"""character_sprite_designer / 再構築描画のテスト。"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.services.character_sprite_designer import (
    design_character_sprite,
    extract_visual_features,
    next_stage_after,
)
from app.services.famicom_sprite_common import DISPLAY_SIZE
from app.services.pixel_character_generator import (
    generate_character_sprite_bundle,
)
from app.services.pixel_character_renderer import render_sprite_from_design


def _cute_face_png() -> bytes:
    img = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((70, 50, 186, 200), outline=(30, 30, 30), width=3)
    draw.ellipse((95, 95, 125, 125), fill=(30, 30, 30))
    draw.ellipse((145, 95, 175, 125), fill=(30, 30, 30))
    draw.arc((108, 130, 148, 155), 0, 180, fill=(30, 30, 30), width=2)
    draw.ellipse((88, 120, 98, 130), fill=(85, 221, 204))
    draw.ellipse((172, 120, 182, 130), fill=(85, 221, 204))
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_and_design_sprite():
    raw = Image.open(__import__("io").BytesIO(_cute_face_png()))
    features = extract_visual_features(raw.convert("L"), raw.convert("RGB"))
    assert features["has_content"] is True
    assert features["face_shape"] in ("round", "wide", "oval")
    design = design_character_sprite(features, "child")
    assert design["eyes"]["type"] in ("large_round", "medium_round")
    assert design["hair"]["style"] == "short_bob"
    assert design["character_type"] == "cute_girl"


def test_render_not_black_blob():
    features = extract_visual_features(
        Image.open(__import__("io").BytesIO(_cute_face_png())).convert("L")
    )
    design = design_character_sprite(features, "baby")
    sprite = render_sprite_from_design(design, 32)
    px = sprite.load()
    white = sum(1 for y in range(32) for x in range(32) if px[x, y] == (255, 255, 255))
    assert white > 32 * 32 * 0.35


def test_bundle_uses_dna_evolution_sprite():
    bundle = generate_character_sprite_bundle(
        _cute_face_png(),
        character_profile={"display_name": "テスト"},
        stage="baby",
        save_file=False,
    )
    assert bundle["current_display"].size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert bundle.get("character_dna") is not None
    assert bundle["final_hero_preview"] is not None
    assert bundle["meta"]["render_mode"] == "character_dna_fixed_template"
    assert bundle["meta"].get("generation_mode") == "character_dna_evolution"
    assert next_stage_after("baby") == "child"
