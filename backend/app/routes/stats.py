"""学習統計サマリー（保護者ダッシュボード／成長記録）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db_optional
from ..deps import get_optional_uid
from ..progress_service import list_progress
from ..schemas import StatsCharacterBrief, StatsSummary, StatsTimelineItem, character_level_from_xp
from ..steps_service import get_steps_today

router = APIRouter(tags=["stats"])


def _parse_dt(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    if isinstance(v, str) and v.strip():
        try:
            s = v.replace("Z", "+00:00")
            d = datetime.fromisoformat(s)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def _to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _stats_from_memory(uid: str, timeline_limit: int) -> StatsSummary:
    items_raw, total = list_progress(uid)
    parsed: list[tuple[datetime, dict]] = []
    for it in items_raw:
        dt = _parse_dt(it.get("updated_at"))
        if dt is None:
            continue
        parsed.append((dt, it))

    parsed.sort(key=lambda x: x[0], reverse=True)

    week_boundary = datetime.now(timezone.utc) - timedelta(days=7)
    in_week = [(d, row) for d, row in parsed if d >= week_boundary]
    quiz_sessions_week = len(in_week)
    average_score_week = (
        round(sum(int(row.get("score") or 0) for _, row in in_week) / len(in_week), 1)
        if in_week
        else 0.0
    )

    timeline: list[StatsTimelineItem] = []
    for dt, it in parsed[:timeline_limit]:
        timeline.append(
            StatsTimelineItem(
                created_at=_to_utc_iso(dt),
                subject=str(it.get("subject") or ""),
                level=int(it.get("level") or 1),
                score=int(it.get("score") or 0),
                kind="quiz_session",
            )
        )

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    st, st_src = get_steps_today(uid, day)
    return StatsSummary(
        database_configured=False,
        quiz_sessions_week=quiz_sessions_week,
        quiz_sessions_total=total,
        average_score_week=average_score_week,
        answers_count_week=0,
        answer_accuracy_week=None,
        character=None,
        timeline=timeline,
        steps_goal=5000,
        steps_today=st,
        steps_ymd=day,
        steps_source=st_src,
    )


@router.get("/summary", response_model=StatsSummary)
def stats_summary(
    uid: str | None = Depends(get_optional_uid),
    db: Session | None = Depends(get_db_optional),
    timeline_limit: int = Query(30, ge=1, le=100),
):
    if not uid:
        return StatsSummary(
            database_configured=db is not None,
            timeline=[],
            steps_today=None,
            steps_ymd=None,
            steps_source=None,
        )

    if db is None:
        return _stats_from_memory(uid, timeline_limit)

    week_ago = datetime.utcnow() - timedelta(days=7)

    prog_all = (
        db.query(models.ProgressEntry)
        .filter(models.ProgressEntry.user_id == uid)
        .all()
    )
    sessions_week = [p for p in prog_all if p.created_at and p.created_at >= week_ago]
    quiz_sessions_week = len(sessions_week)
    average_score_week = (
        round(sum(p.score for p in sessions_week) / len(sessions_week), 1)
        if sessions_week
        else 0.0
    )

    prog_rows_sorted = sorted(
        (p for p in prog_all if p.created_at),
        key=lambda p: p.created_at,
        reverse=True,
    )[:timeline_limit]
    timeline = []
    for p in prog_rows_sorted:
        raw_dt = p.created_at
        if raw_dt is None:
            continue
        if raw_dt.tzinfo is None:
            raw_dt = raw_dt.replace(tzinfo=timezone.utc)
        timeline.append(
            StatsTimelineItem(
                created_at=_to_utc_iso(raw_dt),
                subject=p.subject or "",
                level=p.level,
                score=p.score,
                kind="quiz_session",
            )
        )

    logs_all = (
        db.query(models.QuizAnswerLog)
        .filter(models.QuizAnswerLog.user_id == uid)
        .all()
    )
    logs_week = [l for l in logs_all if l.created_at and l.created_at >= week_ago]
    answers_count_week = len(logs_week)
    correct_week = sum(1 for l in logs_week if l.correct)
    answer_accuracy_week = (
        round((correct_week / len(logs_week)) * 100, 1) if logs_week else None
    )

    char_row = db.query(models.UserCharacter).filter_by(user_id=uid).first()
    character = None
    if char_row:
        xp = char_row.experience or 0
        character = StatsCharacterBrief(
            display_name=char_row.display_name or "まなとも",
            experience=xp,
            level=character_level_from_xp(xp),
            image_url=char_row.image_url,
        )

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    st, st_src = get_steps_today(uid, day)
    return StatsSummary(
        database_configured=True,
        quiz_sessions_week=quiz_sessions_week,
        quiz_sessions_total=len(prog_all),
        average_score_week=average_score_week,
        answers_count_week=answers_count_week,
        answer_accuracy_week=answer_accuracy_week,
        character=character,
        timeline=timeline,
        steps_goal=5000,
        steps_today=st,
        steps_ymd=day,
        steps_source=st_src,
    )
