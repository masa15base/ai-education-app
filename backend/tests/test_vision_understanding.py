"""Vision schema 抽出 + character_dna パイプライン。"""
from __future__ import annotations

from app.services.character_dna import normalize_character_dna
from app.services.image_understanding import understand_image
from app.services.vision_client import extract_vision_result_schema
from tests.test_image_pipeline import _cute_face_png


def test_vision_disabled_without_flag(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    from app.services.vision_client import is_character_vision_enabled

    assert is_character_vision_enabled() is False


def test_extract_vision_schema_only():
    parsed = extract_vision_result_schema(
        {
            "face_shape": "oval",
            "hair_color": "brown",
            "hair_style": "ponytail",
            "extra_field": "ignored",
        }
    )
    assert parsed["face_shape"] == "oval"
    assert "extra_field" not in parsed


def test_understand_image_has_character_dna(monkeypatch):
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    u = understand_image(_cute_face_png())
    assert "character_dna" in u
    assert "vision_result" in u
    assert u["character_dna"]["locked_features"]["eye_shape"] == "large_round"


def test_understand_image_vision_mocked(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "1")

    def fake_vision(_image_bytes: bytes):
        return {
            "face_shape": "round",
            "hair_color": "blonde",
            "hair_style": "short_bob",
            "bangs": "center",
            "eye_shape": "large_round",
            "eye_count": 2,
            "mouth": "smile",
            "cheeks": True,
            "accent_color": "yellow",
            "accessory": "star",
            "mood": "energetic",
            "signature_features": ["blonde hair"],
        }, None

    monkeypatch.setattr("app.services.vision_client.fetch_vision_result", fake_vision)
    u = understand_image(_cute_face_png())
    assert u["source"] == "vision_api"
    assert u["vision_result"]["hair_color"] == "blonde"
    dna = normalize_character_dna(u["vision_result"])
    assert dna["locked_features"]["hair_color"] == "blonde"
