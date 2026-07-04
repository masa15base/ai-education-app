"""
character_dna 固定テンプレートから進化ステージを生成。
Vision / 画像 AI にデザインは任せない。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .character_dna import (
    build_generation_prompt,
    build_stage_spec,
    signature_features_ja_from_dna,
    stage_spec_to_render_spec,
)
from .character_sprite_designer import STAGES_ORDER, next_stage_after
from .generated_image_check import render_stage_with_spec, validate_and_retry_once
from .pixel_art_converter import DISPLAY_SIZE

STAGE_PIXEL: dict[str, dict[str, int]] = {
    "egg": {"sprite": 32, "max_colors": 4},
    "baby": {"sprite": 48, "max_colors": 7},
    "child": {"sprite": 64, "max_colors": 9},
    "student": {"sprite": 64, "max_colors": 10},
    "hero": {"sprite": 64, "max_colors": 12},
}


def _dna_from_understanding(image_understanding: dict[str, Any]) -> dict[str, Any]:
    if "character_dna" in image_understanding:
        return image_understanding["character_dna"]
    from .character_dna import normalize_character_dna, rule_based_to_vision_result

    raw = image_understanding.get("raw_features") or {}
    analysis = image_understanding.get("analysis") or {}
    vr = rule_based_to_vision_result(raw, analysis)
    return normalize_character_dna(vr)


def _render_stage_pipeline(
    image_understanding: dict[str, Any],
    stage: str,
) -> tuple[Image.Image, Image.Image, Image.Image, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """(base, pixel, display, render_spec, stage_spec, validation_result)"""
    character_dna = _dna_from_understanding(image_understanding)
    stage_spec = build_stage_spec(character_dna, stage)
    cfg = STAGE_PIXEL.get(stage, STAGE_PIXEL["baby"])
    sprite = int(cfg["sprite"])
    max_colors = int(cfg["max_colors"])

    base, pixel, display = render_stage_with_spec(
        stage_spec, sprite=sprite, max_colors=max_colors, strict=False
    )
    base, pixel, display, validation = validate_and_retry_once(
        base,
        pixel,
        display,
        character_dna,
        stage_spec,
        sprite=sprite,
        max_colors=max_colors,
    )
    render_spec = stage_spec_to_render_spec(stage_spec, strict=validation.get("retried", False))
    return base, pixel, display, render_spec, stage_spec, validation


def generate_evolution_bundle(
    image_understanding: dict[str, Any],
    *,
    stage_key: str,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
    force_egg: bool = False,
) -> dict[str, Any]:
    _ = character_profile
    if force_egg:
        stage_key = "egg"
    else:
        stage_key = stage_key if stage_key in STAGES_ORDER else "baby"
        if stage_key == "egg":
            stage_key = "baby"

    character_dna = _dna_from_understanding(image_understanding)

    base_char, _, current_display, current_spec, current_stage_spec, validation = (
        _render_stage_pipeline(image_understanding, stage_key)
    )

    nxt = next_stage_after(stage_key)
    next_display: Image.Image | None = None
    next_stage_spec: dict[str, Any] | None = None
    if nxt and nxt != "egg":
        _, _, next_display, _, next_stage_spec, _ = _render_stage_pipeline(
            image_understanding, nxt
        )

    _, _, hero_display, hero_spec, hero_stage_spec, _ = _render_stage_pipeline(
        image_understanding, "hero"
    )

    saved_path: str | None = None
    if save_file and output_dir:
        import uuid

        from .pixel_character_generator import DEFAULT_OUTPUT_DIR

        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"pixel_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")
        hero_display.save(dest / f"pixel_hero_{tag}.png", format="PNG")
        if next_display is not None and nxt:
            next_display.save(dest / f"pixel_{nxt}_{tag}.png", format="PNG")

    generation_prompt = build_generation_prompt(character_dna, stage_key)

    meta: dict[str, Any] = {
        "stage": stage_key,
        "render_mode": "character_dna_fixed_template",
        "pipeline": [
            "vision_result_extraction",
            "normalize_character_dna",
            "build_stage_spec",
            "fixed_template_render",
            "pixel_art_conversion",
            "generated_image_check",
        ],
        "image_understanding": image_understanding,
        "vision_result": image_understanding.get("vision_result"),
        "character_dna": character_dna,
        "stage_spec": current_stage_spec,
        "generation_prompt": generation_prompt,
        "validation_result": validation,
        "understanding_source": image_understanding.get("source"),
        "vision_api_status": image_understanding.get("vision_api_status"),
        "character_design_spec": current_spec,
        "hero_character_design_spec": hero_spec,
        "next_stage": nxt,
        "signature_features": character_dna.get("signature_features", []),
        "signature_features_ja": signature_features_ja_from_dna(character_dna),
        "debug_notes": current_spec.get("debug_notes", []),
        "sprite_size": STAGE_PIXEL.get(stage_key, STAGE_PIXEL["baby"])["sprite"],
        "max_colors": STAGE_PIXEL.get(stage_key, STAGE_PIXEL["baby"])["max_colors"],
        "display_size": DISPLAY_SIZE,
        "saved_path": saved_path,
    }
    if next_stage_spec:
        meta["next_stage_spec"] = next_stage_spec

    return {
        "image_understanding": image_understanding,
        "character_design_spec": current_spec,
        "base_character_image": base_char,
        "current_display": current_display,
        "next_stage_preview": next_display,
        "final_hero_preview": hero_display,
        "current_stage_image": current_display,
        "meta": meta,
        "saved_path": saved_path,
    }
