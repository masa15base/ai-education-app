"""famicom_sprite_spec 固定少女スプライト生成と品質判定。"""
from __future__ import annotations

from app.services.famicom_sprite_common import DISPLAY_SIZE, WHITE
from app.services.famicom_sprite_generator import (
    COLOR_BY_NAME,
    FIXED_MVP_CHARACTER_SPEC,
    GENERATION_MODE,
    NPC_PALETTE_8,
    build_sprite_spec,
    generate_spec_sprite_bundle,
    generate_sprite_from_spec,
    render_girl_sprite_32,
    validate_fixed_girl_sprite,
)


def test_palette_matches_spec_sheet():
    assert len(NPC_PALETTE_8) == 8
    assert COLOR_BY_NAME["dark_navy"] == (0x1E, 0x21, 0x40)
    assert COLOR_BY_NAME["blue"] == (0x2B, 0x7B, 0xFF)
    assert COLOR_BY_NAME["orange"] == (0xE1, 0x64, 0x0A)
    assert COLOR_BY_NAME["grey"] == (0x80, 0x80, 0x80)
    assert COLOR_BY_NAME["skin"] == (0xF4, 0xD8, 0xC0)
    assert COLOR_BY_NAME["cheek_pink"] == (0xFF, 0xB6, 0xB6)
    assert COLOR_BY_NAME["mint_green"] == (0x4E, 0xDC, 0xB0)


def test_fixed_character_spec_values():
    assert FIXED_MVP_CHARACTER_SPEC["gender"] == "girl"
    assert FIXED_MVP_CHARACTER_SPEC["hair_color"] == "dark_navy"
    assert FIXED_MVP_CHARACTER_SPEC["accessory"] == "mint_green_star"
    assert FIXED_MVP_CHARACTER_SPEC["eye_style"] == "dot"
    assert FIXED_MVP_CHARACTER_SPEC["ribbon_color"] == "orange"
    assert FIXED_MVP_CHARACTER_SPEC["skirt_color"] == "grey"
    assert FIXED_MVP_CHARACTER_SPEC["shoe_color"] == "brown"


def test_build_sprite_spec_from_fixed_values():
    spec = build_sprite_spec()
    assert spec.gender == "girl"
    assert spec.hair_style == "short_bob"
    assert spec.hair_rgb == COLOR_BY_NAME["dark_navy"]
    assert spec.accent_rgb == COLOR_BY_NAME["mint_green"]
    assert spec.top_rgb == COLOR_BY_NAME["blue"]
    assert spec.ribbon_rgb == COLOR_BY_NAME["orange"]
    assert spec.skirt_rgb == COLOR_BY_NAME["grey"]
    assert spec.shoe_rgb == COLOR_BY_NAME["brown"]


def test_render_girl_sprite_32_passes_validation():
    spec = build_sprite_spec()
    sprite = render_girl_sprite_32(spec)
    assert sprite.size == (32, 32)
    assert sprite.getpixel((0, 0)) == WHITE
    result = validate_fixed_girl_sprite(sprite, spec)
    assert result.passed, result.issues
    assert result.metrics["ribbon_orange_pixels"] >= 2
    assert result.metrics["skirt_grey_pixels"] >= 12
    assert result.metrics["shoe_brown_pixels"] >= 4


def test_generate_sprite_from_spec_upscales_to_512():
    sprite, display, _spec, validation, meta = generate_sprite_from_spec()
    assert validation.passed
    assert sprite.size == (32, 32)
    assert display.size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert meta["generation_mode"] == GENERATION_MODE
    assert len(meta["palette"]) == 8


def test_generate_spec_sprite_bundle():
    bundle = generate_spec_sprite_bundle(b"unused-image-bytes", save_file=False)
    assert bundle["current_sprite"].size == (32, 32)
    assert bundle["current_display"].size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert bundle["meta"]["render_mode"] == GENERATION_MODE
    assert bundle["meta"]["validation_result"]["passed"] is True
    assert bundle["next_stage_preview"] is None
    assert bundle["final_hero_preview"] is None
