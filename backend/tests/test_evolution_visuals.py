"""進化ビジュアル生成・apply_activity 連携。"""
from __future__ import annotations

import base64
import json

import pytest

from app.growth_stats_store import apply_activity, apply_activity_memory, record_activity
from app.services.character_dna import MANATOMO_DEFAULT_VISION, normalize_character_dna
from app.services.evolution_visual_service import (
    EVOLUTION_GENERATION_MODE,
    render_stage_visuals,
    understanding_from_stats,
)


def _minimal_dna() -> dict:
    return normalize_character_dna(MANATOMO_DEFAULT_VISION)


def test_understanding_from_stored_dna():
    stats = {"character_dna": _minimal_dna()}
    out = understanding_from_stats(stats)
    assert out is not None
    assert out["character_dna"]["locked_features"]


def test_render_stage_visuals_returns_urls():
    stats = {"character_dna": _minimal_dna()}
    visuals = render_stage_visuals(stats, stage="baby", learning_level=1)
    assert visuals is not None
    assert visuals["image_url"].startswith("data:image/png;base64,")
    assert visuals["generation_mode"] == EVOLUTION_GENERATION_MODE
    assert visuals.get("hero_preview_url")
    assert visuals.get("next_stage_preview_url")


def test_apply_activity_evolution_updates_image(monkeypatch, tmp_path):
    from app.db import Base, SessionLocal, engine
    from app import models  # noqa: F401

    if engine is None:
        pytest.skip("DB engine unavailable")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = "pytest-evolution-visual"
    try:
        db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).delete()
        db.query(models.UserCharacterGrowthStats).filter(
            models.UserCharacterGrowthStats.user_id == uid
        ).delete()
        db.add(
            models.UserCharacter(
                user_id=uid,
                display_name="テスト",
                image_url="data:image/png;base64,old",
                experience=100,
            )
        )
        db.add(
            models.UserCharacterGrowthStats(
                user_id=uid,
                stage="baby",
                has_character_image=True,
                character_dna=_minimal_dna(),
                quiz_correct_count=4,
            )
        )
        db.commit()

        result = apply_activity(
            uid,
            {
                "activity_type": "quiz_complete",
                "correct_count": 1,
                "total_count": 1,
                "level": 1,
                "skip_exp": True,
            },
            db,
        )
        db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
        char = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
        assert result["evolved"] is True
        assert result["stage"] == "child"
        assert char.image_url.startswith("data:image/png;base64,")
        assert char.image_url != "data:image/png;base64,old"
        assert result.get("image_url") == char.image_url
    finally:
        db.close()


def test_generate_character_returns_evolution_or_spec(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setenv("CHARACTER_VISION_ENABLED", "0")
    client = TestClient(app)

    h = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    p = (
        base64.urlsafe_b64encode(json.dumps({"sub": "pytest-evo-gen", "uid": "pytest-evo-gen"}).encode())
        .decode()
        .rstrip("=")
    )
    headers = {"Authorization": f"Bearer {h}.{p}.x"}

    r = client.post(
        "/api/generate-character",
        json={
            "imageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "stage": "baby",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("generation_mode") in ("character_dna_evolution", "famicom_sprite_spec")
    assert body["image"].startswith("data:image/png;base64,")


def test_character_born_stores_dna_memory():
    uid = "mem-dna-user"
    dna = _minimal_dna()
    record_activity(
        uid,
        {
            "activity_type": "character_born",
            "character_dna": dna,
            "hero_preview_url": "data:image/png;base64,hero",
            "next_stage_preview_url": "data:image/png;base64,next",
        },
    )
    result = apply_activity_memory(
        uid,
        {
            "activity_type": "quiz_complete",
            "correct_count": 5,
            "total_count": 5,
            "level": 1,
        },
    )
    assert result["stats"].get("character_dna") == dna
