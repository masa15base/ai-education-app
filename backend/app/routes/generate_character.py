"""手書きイラストからキャラ画像生成（ファミコン風ドットスプライト・Replicate 不要）。"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..character_local_gen import generate_character_image
from ..growth_stats_store import get_character_exp, get_stats
from ..rate_limit import require_generate_rate_limit
from ..services.character_growth import determine_character_stage
from ..services.pixel_character_generator import resolve_stage
from ..security_settings import max_generate_image_base64_chars

router = APIRouter(tags=["character"])

_MAX_B64 = max_generate_image_base64_chars()


class GenerateCharacterBody(BaseModel):
    imageBase64: str = Field(
        ...,
        min_length=8,
        max_length=_MAX_B64,
        description="前処理済み PNG の base64（data URL 可）",
    )
    prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="互換用（未使用・パーツ合成のみ）",
    )
    learning_level: int = Field(default=1, ge=1, le=99)
    stage: str | None = Field(
        default=None,
        description="egg | baby | child | student | hero（未指定時は成長ステージまたは learning_level）",
    )
    display_name: str | None = Field(default=None, max_length=100)


@router.get("/generate-character/capabilities")
def generate_character_capabilities() -> dict:
    """Vision 連携の有効状態（秘密は返さない）。"""
    from ..services.vision_client import is_character_vision_enabled, vision_model_name

    return {
        "generation_mode": "character_dna_evolution",
        "image_generation_ai_enabled": False,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "character_vision_enabled": is_character_vision_enabled(),
        "character_vision_model": vision_model_name(),
    }


@router.post("/generate-character")
def generate_character(
    body: GenerateCharacterBody,
    _uid: str = Depends(require_generate_rate_limit),
):
    try:
        profile = {"display_name": body.display_name or "mascot"}
        stage = body.stage
        if not stage:
            try:
                stats = get_stats(_uid)
                stage = determine_character_stage(stats, get_character_exp(_uid))
            except Exception:
                stage = resolve_stage(None, body.learning_level)
            if stage == "egg":
                stage = resolve_stage(None, body.learning_level)
                if stage == "egg":
                    stage = "baby"
        data_url, meta = generate_character_image(
            body.imageBase64,
            learning_level=body.learning_level,
            stage=stage,
            character_profile=profile,
        )
    except ValueError as e:
        msg = str(e)
        if "quality check failed" in msg:
            raise HTTPException(status_code=422, detail=msg) from e
        raise HTTPException(status_code=400, detail=f"character image build failed: {e}") from e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"character image build failed: {e}",
        ) from e
    return {
        "image": data_url,
        "generation_mode": meta.get("generation_mode", "famicom_sprite_spec"),
        "validation_result": meta.get("validation_result"),
        "current_stage_image": meta.get("current_stage_image") or data_url,
        "current_stage_image_url": meta.get("current_stage_image_url") or data_url,
        "next_stage_preview": meta.get("next_stage_preview"),
        "next_stage_image_url": meta.get("next_stage_image_url"),
        "final_hero_preview": meta.get("final_hero_preview"),
        "final_hero_image_url": meta.get("final_hero_image_url"),
        "character_dna": meta.get("character_dna"),
        "parts_dna": meta.get("parts_dna"),
        "vision_result": meta.get("vision_result"),
        "signature_features_ja": meta.get("signature_features_ja", []),
        "image_understanding": meta.get("image_understanding"),
        "understanding_source": (meta.get("image_understanding") or {}).get("source"),
        "vision_api_status": (meta.get("image_understanding") or {}).get("vision_api_status"),
        "stage": meta.get("stage"),
        "next_stage": meta.get("next_stage"),
        "generation_mode": meta.get("generation_mode"),
        "image_understanding": meta.get("image_understanding") or bundle.get("image_understanding"),
        "sprite_size": meta.get("sprite_size"),
        "pipeline": meta.get("pipeline"),
        "render_mode": meta.get("render_mode"),
        "saved_path": meta.get("saved_path"),
    }
