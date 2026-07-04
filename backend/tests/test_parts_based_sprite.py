"""パーツ合成スプライト生成。"""
from __future__ import annotations

from app.services.parts_based_sprite_generator import (
    MVP_PARTS_DNA,
    STAGE_CANVAS,
    compose_parts_sprite,
    generate_parts_bundle_from_bytes,
    resolve_parts_dna,
    upscale_sprite,
)
from tests.test_image_pipeline import _cute_face_png


def test_stage_canvas_sizes():
    assert STAGE_CANVAS["baby"] == 32
    assert STAGE_CANVAS["child"] == 48
    assert STAGE_CANVAS["hero"] == 64


def test_compose_white_background():
    sprite = compose_parts_sprite(MVP_PARTS_DNA, "baby")
    assert sprite.size == (32, 32)
    assert sprite.getpixel((0, 0)) == (255, 255, 255)


def test_upscale_nearest():
    sprite = compose_parts_sprite(MVP_PARTS_DNA, "child")
    display = upscale_sprite(sprite)
    assert display.size == (512, 512)


def test_bundle_generation_mode(monkeypatch):
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    bundle = generate_parts_bundle_from_bytes(_cute_face_png(), stage="child", save_file=False)
    assert bundle["meta"]["generation_mode"] == "parts_based_sprite"
    assert bundle["meta"]["render_mode"] == "parts_based_sprite"
    assert bundle["current_display"].size == (512, 512)


def test_mvp_dna_locked():
    dna = resolve_parts_dna({"locked_features": {"hair_style": "long"}})
    assert dna["hair_style"] == "short_bob"
    assert dna["accessory"] == "star"
