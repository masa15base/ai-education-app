"""進化ステージに応じたキャラビジュアル生成・永続化。"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from .. import models
from .evolution_generator import generate_evolution_bundle
from .pixel_character_generator import image_to_data_url, resolve_stage

logger = logging.getLogger(__name__)

EVOLUTION_GENERATION_MODE = "character_dna_evolution"


def understanding_from_stats(stats: dict[str, Any]) -> dict[str, Any] | None:
    """保存済み DNA / image_understanding から再描画用 dict を組み立てる。"""
    stored = stats.get("image_understanding")
    if isinstance(stored, dict) and stored.get("character_dna"):
        return stored
    dna = stats.get("character_dna")
    if isinstance(dna, dict) and dna:
        return {"character_dna": dna, "source": "stored_character_dna"}
    return None


def render_stage_visuals(
    stats: dict[str, Any],
    *,
    stage: str | None = None,
    learning_level: int = 1,
    save_file: bool = False,
) -> dict[str, Any] | None:
    """
    character_dna から指定 stage のスプライトと進化プレビューを生成。
    戻り値: image_url, hero_preview_url, next_stage_preview_url, character_dna, image_understanding
    """
    understanding = understanding_from_stats(stats)
    if not understanding:
        return None

    stage_key = resolve_stage(stage, learning_level)
    if stage_key == "egg":
        stage_key = "baby"

    try:
        bundle = generate_evolution_bundle(
            understanding,
            stage_key=stage_key,
            save_file=save_file,
        )
    except Exception as exc:
        logger.warning("Evolution render failed for stage=%s: %s", stage_key, exc)
        return None

    current = bundle.get("current_display")
    if current is None:
        return None

    next_img = bundle.get("next_stage_preview")
    hero_img = bundle.get("final_hero_preview")
    meta = bundle.get("meta") or {}
    image_understanding = bundle.get("image_understanding") or understanding

    return {
        "image_url": image_to_data_url(current),
        "hero_preview_url": image_to_data_url(hero_img) if hero_img else None,
        "next_stage_preview_url": image_to_data_url(next_img) if next_img else None,
        "character_dna": meta.get("character_dna") or image_understanding.get("character_dna"),
        "image_understanding": image_understanding,
        "stage": meta.get("stage") or stage_key,
        "generation_mode": EVOLUTION_GENERATION_MODE,
    }


def apply_stage_visuals_to_character(
    uid: str,
    stats: dict[str, Any],
    db: Session,
    *,
    stage: str,
    learning_level: int = 1,
) -> dict[str, Any] | None:
    """UserCharacter.image_url と stats 内プレビュー URL を更新。"""
    visuals = render_stage_visuals(stats, stage=stage, learning_level=learning_level)
    if not visuals:
        return None

    char = (
        db.query(models.UserCharacter)
        .filter(models.UserCharacter.user_id == uid)
        .first()
    )
    if char and visuals.get("image_url"):
        char.image_url = visuals["image_url"]

    if visuals.get("character_dna"):
        stats["character_dna"] = visuals["character_dna"]
    if visuals.get("image_understanding"):
        stats["image_understanding"] = visuals["image_understanding"]
    if visuals.get("hero_preview_url"):
        stats["hero_preview_url"] = visuals["hero_preview_url"]
    if visuals.get("next_stage_preview_url"):
        stats["next_stage_preview_url"] = visuals["next_stage_preview_url"]

    return visuals
