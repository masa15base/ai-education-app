"""5段階パイプラインのテスト。"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.services.image_understanding import understand_image
from app.services.pixel_character_generator import generate_character_sprite_bundle


def _cute_face_png() -> bytes:
    import io

    img = Image.new("RGB", (256, 256), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((70, 50, 186, 200), outline=(30, 30, 30), width=3)
    draw.ellipse((95, 95, 125, 125), fill=(30, 30, 30))
    draw.ellipse((145, 95, 175, 125), fill=(30, 30, 30))
    draw.arc((108, 130, 148, 155), 0, 180, fill=(30, 30, 30), width=2)
    draw.ellipse((88, 120, 98, 130), fill=(85, 221, 204))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_understanding_structure():
    u = understand_image(_cute_face_png())
    assert u["pipeline_step"] == "image_understanding"
    assert "character_dna" in u
    assert "vision_result" in u
    assert u["character_dna"]["base_identity"]["face_shape"] in ("round", "oval", "wide")


def test_pipeline_parts_compose():
    from app.services.parts_based_sprite_generator import compose_parts_sprite, upscale_sprite

    u = understand_image(_cute_face_png())
    from app.services.parts_based_sprite_generator import resolve_parts_dna

    sprite = compose_parts_sprite(resolve_parts_dna(u.get("character_dna")), "child")
    assert sprite.size == (48, 48)
    display = upscale_sprite(sprite)
    assert display.size == (512, 512)


def test_bundle_has_required_api_fields():
    bundle = generate_character_sprite_bundle(_cute_face_png(), stage="child", save_file=False)
    meta = bundle["meta"]
    mode = meta.get("generation_mode") or meta.get("render_mode")
    assert mode in ("character_dna_evolution", "character_dna_fixed_template", "famicom_sprite_spec")
    assert meta.get("image_understanding") is not None
    assert meta.get("validation_result", {}).get("passed") is True
    assert bundle.get("current_sprite") is not None or bundle.get("current_display") is not None
    if mode == "character_dna_evolution" or meta.get("render_mode") == "character_dna_fixed_template":
        assert bundle.get("character_dna") is not None
        assert bundle.get("final_hero_preview") is not None
        assert bundle.get("next_stage_preview") is not None
