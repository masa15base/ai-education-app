"""evolution_preview_compose のフレーミング・ヒント文言テスト。"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.services.evolution_preview_compose import (
    crop_to_content,
    frame_sprite_display,
    frame_sprite_preview,
    preview_meta_for_stage,
    stage_label_ja,
    stage_preview_hint_ja,
)


def _tiny_sprite() -> Image.Image:
    img = Image.new("RGB", (32, 32), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([12, 8, 20, 24], fill=(77, 141, 245), outline=(0, 0, 0))
    return img


def test_stage_labels_and_hints():
    assert stage_label_ja("child") == "こども"
    assert stage_preview_hint_ja("student") == "学生帽と本を持つ"
    meta = preview_meta_for_stage("hero")
    assert meta["stage_label_ja"] == "ヒーロー"
    assert "マント" in meta["preview_hint_ja"]


def test_crop_to_content_trims_whitespace():
    sprite = _tiny_sprite()
    cropped = crop_to_content(sprite, pad=1)
    assert cropped.size[0] < 32
    assert cropped.size[1] < 32


def test_frame_sprite_preview_scales_up():
    sprite = _tiny_sprite()
    framed = frame_sprite_preview(sprite, "child", canvas=192, min_scale=5)
    assert framed.size == (192, 192)
    # 背景色（child）が使われている
    assert framed.getpixel((0, 0)) == (255, 248, 225)


def test_frame_sprite_display_reaches_512():
    sprite = _tiny_sprite()
    display = frame_sprite_display(sprite, "hero", canvas=192, display_size=512)
    assert display.size == (512, 512)
