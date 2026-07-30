"""動的クイズの採点・記録。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import db as dbmod
from ..deps import get_optional_uid
from ..question_service import get_question_by_id
from ..growth_stats_store import record_activity
from ..progress_service import latest_progress_entry_today_utc, save_quiz_session
from ..quiz_engine import make_question

router = APIRouter(tags=["quiz"])


class AnswerItem(BaseModel):
    question_index: int = Field(ge=1, le=20)
    selected_answer: str
    question_id: str | None = Field(default=None, max_length=120)


class QuizVerifyBody(BaseModel):
    subject: str
    level: int = Field(ge=1, le=99)
    question_index: int = Field(ge=1, le=20)
    selected_answer: str
    question_id: str | None = Field(default=None, max_length=120)


class QuizFinishBody(BaseModel):
    subject: str
    level: int = Field(ge=1, le=99)
    answers: list[AnswerItem]


def _grade_one_answer(subject: str, level: int, a: AnswerItem) -> dict:
    """DB に行があればその正解。無ければ quiz_engine（動的 id や DB 未投入時の互換）。"""
    if a.question_id and dbmod.SessionLocal is not None:
        qd = get_question_by_id(a.question_id)
        if qd:
            ca = qd["correct_answer"]
            ok = (a.selected_answer or "").strip() == (ca or "").strip()
            return {
                "question_index": a.question_index,
                "question_id": qd["id"],
                "selected_answer": a.selected_answer,
                "correct_answer": ca,
                "correct": ok,
                "hint": qd.get("hint", ""),
            }
    q = make_question(subject, level, a.question_index)
    ok = (a.selected_answer or "").strip() == (q["correct_answer"] or "").strip()
    return {
        "question_index": a.question_index,
        "question_id": q["id"],
        "selected_answer": a.selected_answer,
        "correct_answer": q["correct_answer"],
        "correct": ok,
        "hint": q["hint"],
    }


@router.post("/verify")
def verify_one(body: QuizVerifyBody):
    if body.question_id and dbmod.SessionLocal is not None:
        qd = get_question_by_id(body.question_id)
        if qd:
            ok = body.selected_answer.strip() == qd["correct_answer"].strip()
            return {
                "correct": ok,
                "correct_answer": qd["correct_answer"],
                "hint": qd["hint"],
                "question_id": qd["id"],
            }
    q = make_question(body.subject, body.level, body.question_index)
    ok = body.selected_answer.strip() == q["correct_answer"].strip()
    return {
        "correct": ok,
        "correct_answer": q["correct_answer"],
        "hint": q["hint"],
        "question_id": q["id"],
    }


@router.get("/session-today")
def quiz_session_today(uid: str | None = Depends(get_optional_uid)):
    """ログイン時: UTC 当日にクイズ進捗があれば true と直近1件。"""
    if not uid:
        return {"has_session_today": False, "latest": None}
    latest = latest_progress_entry_today_utc(uid)
    return {"has_session_today": latest is not None, "latest": latest}


@router.post("/complete")
def complete_quiz(
    body: QuizFinishBody,
    uid: str | None = Depends(get_optional_uid),
):
    if not body.answers:
        raise HTTPException(status_code=400, detail="answers is required")
    details = [_grade_one_answer(body.subject, body.level, a) for a in body.answers]
    correct_n = sum(1 for d in details if d["correct"])
    n = len(details)
    pct = round((correct_n / n) * 100) if n else 0

    growth_result = None
    rewards: dict = {"gained_xp": 0, "experience": None, "level": None}

    if uid:
        # XP 一本化: progress（日次上限）が唯一の付与元。growth はカウント・連続日数のみ。
        rewards = save_quiz_session(
            uid, body.subject, body.level, pct, details, skip_xp=False
        )
        db_mode = rewards.get("experience") is not None
        growth_result = record_activity(
            uid,
            {
                "activity_type": "quiz_complete",
                "correct_count": correct_n,
                "total_count": n,
                "level": body.level,
                # DB あり: progress が既に UserCharacter.experience を更新済み
                # DB なし（メモリ）: growth 側で同式の XP を付与
                "skip_exp": db_mode,
            },
        )
        if db_mode:
            # FE / growth レスポンスも progress の付与値に揃える
            progress_xp = int(rewards.get("gained_xp") or 0)
            growth_result = {**growth_result, "exp_gained": progress_xp}

    display_xp = (
        int((growth_result or {}).get("exp_gained") or 0)
        if growth_result
        else 0
    )
    if uid and rewards.get("experience") is not None:
        display_xp = int(rewards.get("gained_xp") or 0)

    out: dict = {
        "score_percent": pct,
        "correct": correct_n,
        "total": n,
        "details": details,
        "saved": bool(uid),
        "gained_xp": display_xp,
    }
    if uid:
        out["experience"] = rewards.get("experience")
        out["level"] = rewards.get("level")
        if out["experience"] is None and growth_result:
            out["experience"] = growth_result.get("character_exp")
            from ..schemas import character_level_from_xp

            exp = int(out["experience"] or 0)
            out["level"] = character_level_from_xp(exp)
    if growth_result:
        out["growth"] = {
            "exp_gained": int(growth_result.get("exp_gained") or 0),
            "stage": growth_result.get("stage"),
            "evolved": growth_result.get("evolved"),
            "previous_stage": growth_result.get("previous_stage"),
        }
    return out
