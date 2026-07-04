"""character_growth サービスと API のテスト。"""
from __future__ import annotations

from app.services.character_growth import (
    build_character_status,
    calculate_exp,
    default_stats,
    determine_character_stage,
    get_next_evolution_requirement,
)


def test_calculate_exp_quiz_answer():
    assert calculate_exp({"activity_type": "quiz_answer", "is_correct": True}) == 15
    assert calculate_exp({"activity_type": "quiz_answer", "is_correct": False}) == 5


def test_calculate_exp_steps():
    assert calculate_exp({"activity_type": "steps", "steps": 2500}) == 20
    assert (
        calculate_exp(
            {"activity_type": "steps", "steps": 1000, "goal_reached": True}
        )
        == 40
    )


def test_determine_stage_progression():
    stats = {**default_stats(), "has_character_image": True}
    assert determine_character_stage(stats, 0) == "baby"

    stats["quiz_correct_count"] = 5
    assert determine_character_stage(stats, 100) == "child"

    stats["quiz_correct_count"] = 20
    stats["total_steps"] = 10_000
    assert determine_character_stage(stats, 300) == "student"

    stats["quiz_correct_count"] = 50
    stats["quiz_streak_days"] = 7
    stats["total_steps"] = 50_000
    assert determine_character_stage(stats, 700) == "hero"


def test_next_evolution_remaining():
    stats = {**default_stats(), "has_character_image": True, "quiz_correct_count": 3}
    nxt = get_next_evolution_requirement(stats, 50)
    assert nxt["next_stage"] == "child"
    assert nxt["remaining_character_exp"] == 50
    assert nxt["remaining_quiz_correct_count"] == 2


def test_build_character_status_message():
    stats = {
        **default_stats(),
        "has_character_image": True,
        "quiz_correct_count": 5,
    }
    body = build_character_status(
        stats,
        character_id="u1",
        display_name="ぴょん",
        image_url=None,
        character_exp=120,
        daily_steps=6000,
        quiz_today=False,
    )
    assert body["stage"] == "child"
    assert body["home_action"] in (
        "idle",
        "walking",
        "cheering",
        "sleeping",
        "studying",
        "celebrating",
    )
    assert isinstance(body["message"], str) and len(body["message"]) > 0
