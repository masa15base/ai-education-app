"""famicom_rpg_sprite（非推奨）の単体テスト。"""
from __future__ import annotations

from pathlib import Path

import io

from PIL import Image

from app.services.famicom_rpg_generator import (
    GENERATION_MODE,
    RpgCharacterHints,
    compose_rpg_sprite,
    generate_rpg_evolution_bundle,
    generate_rpg_sprite_from_bytes,
)
from app.services.famicom_sprite_common import SKIN, WHITE
from app.services.famicom_sprite_generator import validate_fixed_girl_sprite, build_sprite_spec
from app.services.sprite_quality_check import validate_famicom_sprite
from app.services.trace_pixelizer import trace_pixelize_line_art
from app.image_preprocess_algo import build_binary_scribble
from tests.test_image_pipeline import _cute_face_png


def test_rpg_sprite_renders_32x32():
    sprite, _, _validation, meta = generate_rpg_sprite_from_bytes(_cute_face_png())
    assert meta["generation_mode"] == GENERATION_MODE
    assert sprite.size == (32, 32)
    assert SKIN in {sprite.getpixel((x, y)) for y in range(32) for x in range(32)}


def test_fixed_spec_sprite_passes_quality():
    from app.services.famicom_sprite_generator import render_girl_sprite_32

    sprite = render_girl_sprite_32(build_sprite_spec())
    result = validate_fixed_girl_sprite(sprite, build_sprite_spec())
    assert result.passed, result.issues


def test_line_trace_fails_quality_check():
    """旧 trace 系の出力は固定少女 spec の品質判定で失敗する。"""
    rgb = Image.open(io.BytesIO(_cute_face_png())).convert("RGB")
    line, _ = build_binary_scribble(rgb, famicom_pixels=False)
    noisy = trace_pixelize_line_art(line, rgb, sprite_size=32)
    result = validate_famicom_sprite(noisy)
    assert not result.passed


def test_rpg_evolution_bundle_fails_fixed_girl_quality():
    """非推奨 RPG パスは固定少女 spec の品質判定を通らない。"""
    import pytest

    with pytest.raises(ValueError, match="quality check failed"):
        generate_rpg_evolution_bundle(_cute_face_png(), stage_key="child", save_file=False)


def test_test_image_webp_if_present():
    p = Path(__file__).resolve().parents[2] / "Test画像.webp"
    if not p.is_file():
        return
    sprite, _, _validation, _ = generate_rpg_sprite_from_bytes(p.read_bytes())
    assert sprite.size == (32, 32)
    assert sprite.getpixel((0, 0)) == WHITE


def test_girl_and_boy_distinct():
    girl = compose_rpg_sprite(RpgCharacterHints(gender="girl", hair_style="bob"))
    boy = compose_rpg_sprite(RpgCharacterHints(gender="boy", hair_style="short"))
    assert list(girl.getdata()) != list(boy.getdata())
