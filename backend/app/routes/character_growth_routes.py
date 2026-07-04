"""キャラクター成長ステータス・活動記録 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..deps import get_current_uid
from ..growth_stats_store import fetch_home_status, record_activity
from ..growth_service import utc_day_bounds
from ..progress_service import latest_progress_entry_today_utc
from ..steps_service import get_steps_today

router = APIRouter(tags=["character"])


def _assert_self(uid: str, path_user_id: str) -> None:
    if uid != path_user_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's character")


@router.get("/status/{user_id}", response_model=schemas.CharacterStatusOut)
def get_character_status(
    user_id: str,
    uid: str = Depends(get_current_uid),
):
    _assert_self(uid, user_id)
    record_activity(uid, {"activity_type": "login"})
    _, _, ymd = utc_day_bounds()
    steps, _ = get_steps_today(uid, ymd)
    latest = latest_progress_entry_today_utc(uid)
    quiz_today = latest is not None
    score = int(latest["score"]) if latest else None
    body = fetch_home_status(
        uid,
        daily_steps=steps,
        quiz_today=quiz_today,
        last_quiz_score=score,
    )
    return body


@router.get("/status", response_model=schemas.CharacterStatusOut)
def get_character_status_self(uid: str = Depends(get_current_uid)):
    return get_character_status(uid, uid)


@router.post("/activity", response_model=schemas.CharacterActivityOut)
def post_character_activity(
    body: schemas.CharacterActivityIn,
    uid: str = Depends(get_current_uid),
):
    if body.user_id and body.user_id != uid:
        raise HTTPException(status_code=403, detail="user_id mismatch")

    activity = {
        "activity_type": body.activity_type,
        "is_correct": body.is_correct,
        "steps": body.steps,
        "correct_count": body.correct_count,
        "total_count": body.total_count,
        "goal_reached": body.goal_reached,
        "total_steps": body.total_steps,
    }
    result = record_activity(uid, activity)

    _, _, ymd = utc_day_bounds()
    steps, _ = get_steps_today(uid, ymd)
    latest = latest_progress_entry_today_utc(uid)
    status = fetch_home_status(
        uid,
        daily_steps=steps,
        quiz_today=latest is not None,
        last_quiz_score=int(latest["score"]) if latest else None,
    )

    return schemas.CharacterActivityOut(
        exp_gained=result.get("exp_gained", 0),
        stage=result.get("stage", "egg"),
        evolved=bool(result.get("evolved")),
        previous_stage=result.get("previous_stage"),
        character_exp=int(result.get("character_exp") or 0),
        status=schemas.CharacterStatusOut(**status),
    )
