"""image_preprocess_algo のユニットテスト。"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.image_preprocess_algo import (
    ALGORITHM_ID,
    _estimate_threshold,
    _otsu_threshold,
    build_binary_scribble,
)


def _white_with_black_stroke() -> Image.Image:
    img = Image.new("RGB", (400, 400), (250, 248, 245))
    draw = ImageDraw.Draw(img)
    draw.line((80, 200, 320, 200), fill=(20, 20, 20), width=6)
    draw.ellipse((140, 100, 260, 280), outline=(15, 15, 15), width=5)
    return img


def test_otsu_on_bimodal_histogram():
    hist = [0] * 256
    hist[10] = 500
    hist[240] = 4500
    t = _otsu_threshold(hist, 5000)
    assert 5 <= t <= 50


def test_build_binary_scribble_produces_pixel_meta():
    out, meta = build_binary_scribble(_white_with_black_stroke())
    assert out.mode == "L"
    assert out.size == (512, 512)
    assert meta["algorithm"] == ALGORITHM_ID
    assert meta["renderStyle"] == "famicom_nearest"
    assert meta["hasContent"] is True
    assert 0 < meta["inkRatio"] < 0.5
    assert 32 <= meta["pixelGrid"] <= 512
    assert meta["thresholdMethod"] == "otsu_blend"


def test_build_binary_scribble_smooth_mode():
    out, meta = build_binary_scribble(
        _white_with_black_stroke(),
        famicom_pixels=False,
    )
    assert out.size == (512, 512)
    assert meta["renderStyle"] == "smooth"
    assert "pixelGrid" not in meta


def test_estimate_threshold_clamped():
    white = Image.new("L", (64, 64), 245)
    t = _estimate_threshold(white)
    assert 85 <= t <= 195
