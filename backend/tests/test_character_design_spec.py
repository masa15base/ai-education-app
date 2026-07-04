"""character_design_spec のテスト。"""
from __future__ import annotations

from app.services.character_design_spec import (
    build_character_design_spec,
    build_image_analysis,
    signature_features_for_ui,
)
from app.services.character_sprite_designer import extract_visual_features
from app.services.pixel_character_generator import generate_character_sprite_bundle
def _cute_face_png() -> bytes:
    from PIL import Image, ImageDraw
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


def test_build_character_design_spec_defaults():
    raw = {"has_content": False}
    understanding = {"raw_features": raw, "analysis": build_image_analysis(raw)}
    spec = build_character_design_spec(understanding, stage="child")
    assert spec["character_type"] == "cute_girl"
    assert spec["hair"]["style"] == "short_bob"
    assert spec["eyes"]["type"] in ("large_round", "medium_round")
    assert spec["accessories"]["star"] is True
    assert len(spec["debug_notes"]) >= 1


def test_signature_features_ja():
    raw = {}
    spec = build_character_design_spec(
        {"raw_features": raw, "analysis": build_image_analysis(raw)}, stage="baby"
    )
    ja = signature_features_for_ui(spec)
    assert "丸い顔" in ja
    assert "大きな目" in ja


def test_bundle_includes_design_spec():
    from PIL import Image
    import io

    raw = Image.open(io.BytesIO(_cute_face_png()))
    features = extract_visual_features(raw.convert("L"), raw.convert("RGB"))
    bundle = generate_character_sprite_bundle(
        _cute_face_png(),
        stage="child",
        save_file=False,
    )
    assert bundle["meta"]["render_mode"] == "famicom_sprite_spec"
    assert bundle["meta"].get("generation_mode") == "famicom_sprite_spec"
    assert "signature_features_ja" in bundle["meta"]
    analysis = build_image_analysis(features)
    assert analysis["smile_likely"] is True
