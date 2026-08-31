"""pixel_character_generator / prompt_builder のテスト。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.famicom_sprite_common import DISPLAY_SIZE
from app.services.famicom_sprite_generator import GENERATION_MODE
from app.services.pixel_character_generator import (
    analyze_features,
    generate_pixel_character,
    generate_pixel_character_from_bytes,
    resolve_stage,
)
from app.services.prompt_builder import build_famicom_character_prompt


def _sample_line_png_bytes() -> bytes:
    img = Image.new("L", (256, 256), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse((80, 60, 176, 200), outline=0, width=4)
    draw.line((128, 90, 128, 170), fill=0, width=3)
    buf = __import__("io").BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_resolve_stage_from_level():
    assert resolve_stage(None, 1) == "baby"
    assert resolve_stage(None, 8) == "child"
    assert resolve_stage(None, 15) == "student"
    assert resolve_stage(None, 30) == "hero"
    assert resolve_stage("adult", 1) == "hero"
    assert resolve_stage("egg", 1) == "egg"
    assert resolve_stage("student", 1) == "student"


def test_generate_fixed_spec_sprite_bundle():
    bundle = __import__(
        "app.services.pixel_character_generator",
        fromlist=["generate_character_sprite_bundle"],
    ).generate_character_sprite_bundle(
        _sample_line_png_bytes(),
        stage="egg",
        character_profile={"display_name": "egg"},
        save_file=False,
    )
    assert bundle["meta"]["stage"] == "baby"
    render_mode = bundle["meta"]["render_mode"]
    assert render_mode in (GENERATION_MODE, "character_dna_fixed_template")
    display = bundle["current_display"]
    assert display.size == (DISPLAY_SIZE, DISPLAY_SIZE)


def test_generate_pixel_character_from_bytes_sizes():
    display, meta, path = generate_pixel_character_from_bytes(
        _sample_line_png_bytes(),
        character_profile={"display_name": "ぴょんた"},
        learning_level=12,
        save_file=False,
    )
    assert display.size == (DISPLAY_SIZE, DISPLAY_SIZE)
    assert meta["sprite_size"] == 32
    assert meta["stage"] == "baby"
    assert meta.get("validation_result", {}).get("passed") is True
    assert path is None


def test_generate_pixel_character_saves_file():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "line.png"
        src.write_bytes(_sample_line_png_bytes())
        features = analyze_features(Image.open(src))
        out = generate_pixel_character(
            str(src),
            features,
            {"display_name": "test"},
            "child",
            6,
            tmp,
        )
        assert Path(out).exists()
        saved = Image.open(out)
        assert saved.size == (DISPLAY_SIZE, DISPLAY_SIZE)


def test_build_famicom_character_prompt_includes_tags():
    p = build_famicom_character_prompt(stage="baby", display_name="ミー")
    assert "Famicom" in p
    assert "32x32" in p
    assert "no 3D" in p
    assert "ミー" in p


def test_output_has_white_background_not_black():
    """白線・黒背景の入力でも出力背景は白であること。"""
    img = Image.new("L", (128, 128), 0)
    draw = ImageDraw.Draw(img)
    draw.ellipse((32, 24, 96, 104), outline=255, width=3)
    buf = __import__("io").BytesIO()
    img.save(buf, format="PNG")
    display, _, _ = generate_pixel_character_from_bytes(
        buf.getvalue(),
        learning_level=3,
        save_file=False,
    )
    px = display.load()
    corners = [px[0, 0], px[511, 0], px[0, 511], px[511, 511]]
    for r, g, b in corners:
        assert r > 200 and g > 200 and b > 200, (r, g, b)
    hist = display.convert("L").histogram()
    blackish = sum(hist[:16])
    assert blackish < display.size[0] * display.size[1] * 0.5
