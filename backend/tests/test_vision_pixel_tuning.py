"""DNA パイプラインの結合テスト。"""
from __future__ import annotations

from app.services.character_dna import build_stage_spec, normalize_character_dna, stage_spec_to_render_spec
from app.services.generated_image_check import validate_generated_image
from app.services.base_character_generator import generate_base_character
from app.services.pixel_art_converter import convert_to_pixel_art


def test_dna_render_and_validate():
    dna = normalize_character_dna(
        {
            "face_shape": "round",
            "hair_color": "dark_navy",
            "hair_style": "short_bob",
            "bangs": "center",
            "eye_shape": "large_round",
            "eye_count": 2,
            "mouth": "smile",
            "cheeks": True,
            "accent_color": "mint_green",
            "accessory": "star",
            "mood": "cheerful",
            "signature_features": [],
        }
    )
    stage_spec = build_stage_spec(dna, "child")
    render = stage_spec_to_render_spec(stage_spec)
    base = generate_base_character(render, canvas_size=64)
    pixel = convert_to_pixel_art(base, sprite_size=64, max_colors=9, character_design_spec=render)
    result = validate_generated_image(pixel, dna, "child")
    assert "issues" in result
    assert isinstance(result["passed"], bool)
