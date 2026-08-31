"""generate-character DNA パイプライン（線画 + 元写真）。"""
from __future__ import annotations

import base64
import io
import json

from PIL import Image, ImageDraw

from app.image_preprocess_algo import build_binary_scribble
from app.services.image_understanding import understand_image
from app.services.pixel_character_generator import generate_character_sprite_bundle


def _cute_face_png() -> bytes:
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


def _preprocessed_line(color_png: bytes) -> bytes:
    """本番と同じ前処理で線画 bytes を得る。"""
    img = Image.open(io.BytesIO(color_png)).convert("RGB")
    line, _meta = build_binary_scribble(img)
    buf = io.BytesIO()
    line.save(buf, format="PNG")
    return buf.getvalue()


def test_understand_image_uses_rgb_source_for_accent():
    color = _cute_face_png()
    line = _preprocessed_line(color)
    with_rgb = understand_image(line, rgb_image_bytes=color)
    without_rgb = understand_image(line)
    assert with_rgb["character_dna"] is not None
    assert without_rgb["character_dna"] is not None
    assert with_rgb["raw_features"].get("has_content") is True


def test_generate_bundle_with_line_and_original():
    color = _cute_face_png()
    line = _preprocessed_line(color)
    bundle = generate_character_sprite_bundle(
        line,
        rgb_image_bytes=color,
        stage="child",
        save_file=False,
    )
    meta = bundle["meta"]
    assert meta.get("validation_result", {}).get("passed") is True
    assert bundle.get("character_dna") is not None
    assert meta.get("generation_mode") == "character_dna_evolution"
    assert bundle.get("next_stage_preview") is not None
    assert bundle.get("final_hero_preview") is not None


def test_api_generate_character_dna_mode(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    color = _cute_face_png()
    color_b64 = base64.b64encode(color).decode("ascii")
    line_b64 = base64.b64encode(_preprocessed_line(color)).decode("ascii")
    h = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    p = (
        base64.urlsafe_b64encode(json.dumps({"sub": "pytest-dna", "uid": "pytest-dna"}).encode())
        .decode()
        .rstrip("=")
    )
    client = TestClient(app)
    r = client.post(
        "/api/generate-character",
        json={
            "imageBase64": line_b64,
            "originalImageBase64": color_b64,
            "stage": "child",
        },
        headers={"Authorization": f"Bearer {h}.{p}.x"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("generation_mode") == "character_dna_evolution"
    assert body.get("character_dna") is not None
    assert body.get("next_stage_preview") is not None
    assert body.get("final_hero_preview") is not None
