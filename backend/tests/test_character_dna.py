"""character_dna 正規化・ステージ設計。"""
from __future__ import annotations

from app.services.character_dna import (
    build_generation_prompt,
    build_stage_spec,
    normalize_character_dna,
    stage_spec_to_render_spec,
)


def test_normalize_unknown_defaults():
    dna = normalize_character_dna({"face_shape": "unknown", "hair_color": "unknown"})
    assert dna["base_identity"]["face_shape"] == "round"
    assert dna["locked_features"]["hair_color"] == "dark_navy"
    assert "locked_features" in dna


def test_locked_features_preserved_across_stages():
    vision = {
        "face_shape": "oval",
        "hair_color": "brown",
        "hair_style": "long",
        "bangs": "side",
        "eye_shape": "large_round",
        "eye_count": 2,
        "mouth": "smile",
        "cheeks": True,
        "accent_color": "pink",
        "accessory": "ribbon",
        "mood": "cheerful",
        "signature_features": ["oval face"],
    }
    dna = normalize_character_dna(vision)
    baby = build_stage_spec(dna, "baby")
    hero = build_stage_spec(dna, "hero")
    assert baby["locked_features"] == hero["locked_features"]
    assert baby["stage_rules"]["star_placement"] == "above_head"
    assert hero["stage_rules"]["stage_decor"] == "hero"


def test_generation_prompt_has_constraints():
    dna = normalize_character_dna({})
    p = build_generation_prompt(dna, "child")
    assert "front view only" in p
    assert "no different hairstyle" in p
    assert "hair_color:" in p


def test_stage_spec_render_locked_colors():
    dna = normalize_character_dna(
        {
            "hair_color": "brown",
            "accent_color": "pink",
            "accessory": "star",
            "hair_style": "short_bob",
            "face_shape": "round",
            "bangs": "center",
            "eye_shape": "large_round",
            "eye_count": 2,
            "mouth": "smile",
            "cheeks": True,
            "mood": "cute",
            "signature_features": [],
        }
    )
    spec = stage_spec_to_render_spec(build_stage_spec(dna, "baby"))
    assert spec["palette"]["hair"] == (90, 60, 40)
    assert spec["accessories"]["star"] is True
