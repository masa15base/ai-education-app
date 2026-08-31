"""Replicate なしで手書き線画をファミコン風ドットキャラ（data URL）にする。"""
from __future__ import annotations

from .services.pixel_character_generator import (
    GENERATION_MODE,
    analyze_features,
    generate_character_sprite_bundle,
    generate_pixel_character,
    generate_pixel_character_from_bytes,
    image_to_data_url,
    resolve_stage,
)


def _decode_image_bytes(image_base64: str) -> bytes:
    import base64

    raw = (image_base64 or "").strip()
    if "," in raw:
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def generate_character_image(
    image_base64: str,
    *,
    original_image_base64: str | None = None,
    learning_level: int = 1,
    stage: str | None = None,
    character_profile: dict | None = None,
    output_dir: str | None = None,
    save_file: bool = True,
) -> tuple[str, dict]:
    """
    前処理済み線画 base64 → 512x512 ファミコン風 PNG data URL。
    original_image_base64 があれば髪色・服色抽出に使用。
    戻り値: (data_url, meta)
    """
    profile = dict(character_profile or {})
    img_bytes = _decode_image_bytes(image_base64)
    rgb_bytes = (
        _decode_image_bytes(original_image_base64)
        if original_image_base64
        else None
    )
    bundle = generate_character_sprite_bundle(
        img_bytes,
        rgb_image_bytes=rgb_bytes,
        character_profile=profile,
        stage=stage,
        learning_level=learning_level,
        output_dir=output_dir,
        save_file=save_file,
    )
    display = bundle["current_display"]
    sprite_preview = bundle.get("current_sprite")
    meta = {
        **bundle["meta"],
        "saved_path": bundle.get("saved_path"),
        "generation_mode": bundle["meta"].get("generation_mode", GENERATION_MODE),
        "validation_result": bundle["meta"].get("validation_result"),
        "image_understanding": bundle.get("image_understanding"),
        "character_dna": bundle.get("character_dna"),
        "parts_dna": bundle["meta"].get("parts_dna"),
        "current_stage_image": image_to_data_url(display),
        "current_stage_image_url": image_to_data_url(display),
        "next_stage_preview": image_to_data_url(bundle["next_stage_preview"])
        if bundle.get("next_stage_preview")
        else None,
        "next_stage_image_url": image_to_data_url(bundle["next_stage_preview"])
        if bundle.get("next_stage_preview")
        else None,
        "final_hero_preview": image_to_data_url(bundle["final_hero_preview"])
        if bundle.get("final_hero_preview")
        else None,
        "final_hero_image_url": image_to_data_url(bundle["final_hero_preview"])
        if bundle.get("final_hero_preview")
        else None,
        "signature_features_ja": bundle["meta"].get("signature_features_ja", []),
        "vision_result": bundle["meta"].get("vision_result"),
        "sprite_preview_url": image_to_data_url(sprite_preview) if sprite_preview else None,
    }
    return image_to_data_url(display), meta


def build_character_data_url(
    image_base64: str,
    *,
    learning_level: int = 1,
    stage: str | None = None,
    display_name: str | None = None,
) -> str:
    """既存 API 互換: data URL のみ返す。"""
    data_url, _ = generate_character_image(
        image_base64,
        learning_level=learning_level,
        stage=stage,
        character_profile={"display_name": display_name or "mascot"},
    )
    return data_url


__all__ = [
    "analyze_features",
    "build_character_data_url",
    "generate_character_image",
    "generate_pixel_character",
]
