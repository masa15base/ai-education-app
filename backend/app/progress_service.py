"""進捗の保存・一覧（DB が無いときはメモリにフォールバック）。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func as sqla_func

from .db import SessionLocal
from . import growth_service
from .models import ProgressEntry, QuizAnswerLog, UserCharacter
from .schemas import character_level_from_xp

_memory: dict[str, list[dict]] = {}


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now(timezone.utc).isoformat()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def append_progress(uid: str, subject: str, level: int, score: int) -> dict:
    """進捗を1件追加。DB 利用可能なら INSERT。"""
    row = {
        "uid": uid,
        "subject": subject,
        "level": level,
        "score": score,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if SessionLocal is None:
        _memory.setdefault(uid, []).insert(0, row)
        return row

    db = SessionLocal()
    try:
        ent = ProgressEntry(
            user_id=uid,
            subject=subject,
            level=level,
            score=score,
            gained_xp=0,
        )
        db.add(ent)
        db.commit()
        db.refresh(ent)
        row["updated_at"] = _iso(ent.created_at)
        return row
    finally:
        db.close()


def save_quiz_session(
    uid: str,
    subject: str,
    level: int,
    score_percent: int,
    details: list[dict],
    *,
    skip_xp: bool = False,
) -> dict:
    """
    クイズ完了時: 解答ログ + 進捗 + 経験値（日次上限）を DB に保存。
    DB 無し時は進捗メモリのみ（経験値は付与しない）。

    戻り値: gained_xp, experience, level（DB 無しまたは gained=0 で level None 可）
    """
    correct_n = sum(1 for d in details if d.get("correct"))
    n = max(1, len(details))
    raw = growth_service.compute_quiz_session_xp_raw(correct_n, n, level)

    if SessionLocal is None:
        append_progress(uid, subject, level, score_percent)
        return {"gained_xp": 0, "experience": None, "level": None}

    db = SessionLocal()
    try:
        day_start, day_end, _ = growth_service.utc_day_bounds()
        day_start_n = day_start.astimezone(timezone.utc).replace(tzinfo=None)
        day_end_n = day_end.astimezone(timezone.utc).replace(tzinfo=None)
        current_sum = (
            db.query(sqla_func.coalesce(sqla_func.sum(ProgressEntry.gained_xp), 0))
            .filter(
                ProgressEntry.user_id == uid,
                ProgressEntry.created_at >= day_start_n,
                ProgressEntry.created_at < day_end_n,
            )
            .scalar()
        )
        already = int(current_sum or 0)
        room = max(0, growth_service.QUIZ_XP_DAILY_CAP - already)
        gained = 0 if skip_xp else min(raw, room)

        for d in details:
            db.add(
                QuizAnswerLog(
                    user_id=uid,
                    subject=subject,
                    level=level,
                    question_index=int(d["question_index"]),
                    question_id=str(d["question_id"]),
                    selected_answer=str(d["selected_answer"]),
                    correct=bool(d["correct"]),
                )
            )
        db.add(
            ProgressEntry(
                user_id=uid,
                subject=subject,
                level=level,
                score=score_percent,
                gained_xp=gained,
            )
        )

        char = db.query(UserCharacter).filter(UserCharacter.user_id == uid).first()
        if char:
            char.experience = max(0, min(1_000_000, (char.experience or 0) + gained))
        else:
            char = UserCharacter(
                user_id=uid,
                display_name="みーちゃん",
                image_url=None,
                experience=gained,
                steps_growth_ymd=None,
                steps_xp_paid_tier=0,
                steps_xp_goal_bonus=False,
            )
            db.add(char)

        db.commit()
        db.refresh(char)
        xp = int(char.experience or 0)
        return {
            "gained_xp": gained,
            "experience": xp,
            "level": character_level_from_xp(xp),
        }
    finally:
        db.close()


def list_progress(uid: str, subject: Optional[str] = None) -> tuple[list[dict], int]:
    """一覧と total。"""
    if SessionLocal is None:
        items = list(_memory.get(uid, []))
        if subject:
            items = [i for i in items if i.get("subject") == subject]
        return items, len(items)

    db = SessionLocal()
    try:
        q = (
            db.query(ProgressEntry)
            .filter(ProgressEntry.user_id == uid)
            .order_by(ProgressEntry.created_at.desc())
        )
        if subject:
            q = q.filter(ProgressEntry.subject == subject)
        rows = q.all()
        items = [
            {
                "uid": uid,
                "subject": r.subject,
                "level": r.level,
                "score": r.score,
                "gained_xp": int(r.gained_xp or 0),
                "updated_at": _iso(r.created_at),
            }
            for r in rows
        ]
        return items, len(items)
    finally:
        db.close()


def latest_progress_entry_today_utc(uid: str) -> dict | None:
    """JST 当日の最新 ProgressEntry（無ければ None）。"""
    if SessionLocal is None:
        return None
    day_start, day_end, _ = growth_service.utc_day_bounds()
    day_start_n = day_start.astimezone(timezone.utc).replace(tzinfo=None)
    day_end_n = day_end.astimezone(timezone.utc).replace(tzinfo=None)
    db = SessionLocal()
    try:
        row = (
            db.query(ProgressEntry)
            .filter(
                ProgressEntry.user_id == uid,
                ProgressEntry.created_at >= day_start_n,
                ProgressEntry.created_at < day_end_n,
            )
            .order_by(ProgressEntry.created_at.desc())
            .first()
        )
        if not row:
            return None
        return {
            "subject": row.subject,
            "level": row.level,
            "score": row.score,
            "gained_xp": int(row.gained_xp or 0),
            "updated_at": _iso(row.created_at),
        }
    finally:
        db.close()
