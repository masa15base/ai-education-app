"""固定少女 spec スプライトの品質判定。"""
from __future__ import annotations

from PIL import Image

from .famicom_sprite_generator import (
    SpriteValidationResult,
    build_sprite_spec,
    validate_fixed_girl_sprite,
)


def validate_famicom_sprite(img: Image.Image) -> SpriteValidationResult:
    return validate_fixed_girl_sprite(img, build_sprite_spec())


__all__ = ["SpriteValidationResult", "validate_famicom_sprite", "validate_fixed_girl_sprite"]
