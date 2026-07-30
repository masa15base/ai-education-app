"""user_character_growth_stats の読み書き（DB / メモリフォールバック）。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from . import models
from .db import SessionLocal

logger = logging.getLogger(__name__)
from .growth_service import utc_day_bounds
from .services.character_growth import (
    build_character_status,
    calculate_exp,
    default_stats,
    determine_character_stage,
)

_memory: dict[str, dict[str, Any]] = {}


def _handle_db_unavailable(exc: Exception) -> None:
    """JawsDB 上限などで DB が使えないとき、以降はメモリのみに切り替える。"""
    from .db import disable_database

    logger.warning("Database unavailable (%s); using memory fallback.", exc)
    disable_database()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row: models.UserCharacterGrowthStats) -> dict[str, Any]:
    return {
        "stage": row.stage or "egg",
        "quiz_correct_count": int(row.quiz_correct_count or 0),
        "quiz_total_count": int(row.quiz_total_count or 0),
        "quiz_streak_days": int(row.quiz_streak_days or 0),
        "total_steps": int(row.total_steps or 0),
        "login_streak_days": int(row.login_streak_days or 0),
        "last_quiz_ymd": row.last_quiz_ymd,
        "last_login_ymd": row.last_login_ymd,
        "has_character_image": bool(row.has_character_image),
        "excited_until": row.excited_until.isoformat() if row.excited_until else None,
        **_preview_from_memory(row.user_id),
    }


def _preview_from_memory(uid: str) -> dict[str, Any]:
    mem = _memory.get(uid, {})
    return {
        "hero_preview_url": mem.get("hero_preview_url"),
        "next_stage_preview_url": mem.get("next_stage_preview_url"),
    }


def set_preview_urls(
    uid: str,
    *,
    hero_preview_url: str | None = None,
    next_stage_preview_url: str | None = None,
) -> None:
    slot = _memory.setdefault(uid, {})
    if hero_preview_url:
        slot["hero_preview_url"] = hero_preview_url
    if next_stage_preview_url:
        slot["next_stage_preview_url"] = next_stage_preview_url


def get_stats(uid: str, db: Session | None = None) -> dict[str, Any]:
    if db is not None:
        row = (
            db.query(models.UserCharacterGrowthStats)
            .filter(models.UserCharacterGrowthStats.user_id == uid)
            .first()
        )
        if row:
            return {**default_stats(), **_row_to_dict(row)}
        return {**default_stats(), **_preview_from_memory(uid)}

    if SessionLocal is None:
        return {**default_stats(), **_memory.get(uid, {})}

    session = SessionLocal()
    try:
        return get_stats(uid, session)
    except OperationalError as exc:
        _handle_db_unavailable(exc)
        return {**default_stats(), **_preview_from_memory(uid)}
    finally:
        session.close()


def _save_stats(uid: str, stats: dict[str, Any], db: Session) -> None:
    row = (
        db.query(models.UserCharacterGrowthStats)
        .filter(models.UserCharacterGrowthStats.user_id == uid)
        .first()
    )
    excited = stats.get("excited_until")
    excited_dt = None
    if excited:
        if isinstance(excited, datetime):
            excited_dt = excited
        else:
            try:
                excited_dt = datetime.fromisoformat(str(excited).replace("Z", "+00:00"))
            except Exception:
                excited_dt = None

    if row:
        row.stage = stats.get("stage", "egg")
        row.quiz_correct_count = int(stats.get("quiz_correct_count") or 0)
        row.quiz_total_count = int(stats.get("quiz_total_count") or 0)
        row.quiz_streak_days = int(stats.get("quiz_streak_days") or 0)
        row.total_steps = int(stats.get("total_steps") or 0)
        row.login_streak_days = int(stats.get("login_streak_days") or 0)
        row.last_quiz_ymd = stats.get("last_quiz_ymd")
        row.last_login_ymd = stats.get("last_login_ymd")
        row.has_character_image = bool(stats.get("has_character_image"))
        row.excited_until = excited_dt
    else:
        db.add(
            models.UserCharacterGrowthStats(
                user_id=uid,
                stage=stats.get("stage", "egg"),
                quiz_correct_count=int(stats.get("quiz_correct_count") or 0),
                quiz_total_count=int(stats.get("quiz_total_count") or 0),
                quiz_streak_days=int(stats.get("quiz_streak_days") or 0),
                total_steps=int(stats.get("total_steps") or 0),
                login_streak_days=int(stats.get("login_streak_days") or 0),
                last_quiz_ymd=stats.get("last_quiz_ymd"),
                last_login_ymd=stats.get("last_login_ymd"),
                has_character_image=bool(stats.get("has_character_image")),
                excited_until=excited_dt,
            )
        )
    if stats.get("hero_preview_url") or stats.get("next_stage_preview_url"):
        set_preview_urls(
            uid,
            hero_preview_url=stats.get("hero_preview_url"),
            next_stage_preview_url=stats.get("next_stage_preview_url"),
        )


def _update_quiz_streak(stats: dict[str, Any], ymd: str) -> None:
    last = stats.get("last_quiz_ymd")
    if not last:
        stats["quiz_streak_days"] = 1
    else:
        try:
            last_d = datetime.strptime(last, "%Y-%m-%d").date()
            cur_d = datetime.strptime(ymd, "%Y-%m-%d").date()
            delta = (cur_d - last_d).days
            if delta == 0:
                pass
            elif delta == 1:
                stats["quiz_streak_days"] = int(stats.get("quiz_streak_days") or 0) + 1
            else:
                stats["quiz_streak_days"] = 1
        except ValueError:
            stats["quiz_streak_days"] = 1
    stats["last_quiz_ymd"] = ymd


def _update_login_streak(stats: dict[str, Any], ymd: str) -> None:
    last = stats.get("last_login_ymd")
    if not last:
        stats["login_streak_days"] = 1
    else:
        try:
            last_d = datetime.strptime(last, "%Y-%m-%d").date()
            cur_d = datetime.strptime(ymd, "%Y-%m-%d").date()
            delta = (cur_d - last_d).days
            if delta == 0:
                pass
            elif delta == 1:
                stats["login_streak_days"] = int(stats.get("login_streak_days") or 0) + 1
            else:
                stats["login_streak_days"] = 1
        except ValueError:
            stats["login_streak_days"] = 1
    stats["last_login_ymd"] = ymd


def apply_activity(
    uid: str,
    activity: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    """
    EXP 加算・stats 更新・進化判定。
    戻り値: { stats, exp_gained, stage, evolved, previous_stage }
    """
    _, _, ymd = utc_day_bounds()
    stats = {**default_stats(), **get_stats(uid, db)}
    prev_stage = determine_character_stage(stats, _char_exp(db, uid))

    t = (activity.get("activity_type") or "").strip()
    # skip_exp: クイズ完了で progress 側が既に XP 付与した場合の二重加算防止
    if activity.get("skip_exp"):
        exp_gained = 0
    else:
        exp_gained = calculate_exp(activity)
        if t == "login" and stats.get("last_login_ymd") == ymd:
            exp_gained = 0

    char = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
    if char and exp_gained > 0:
        char.experience = max(0, min(1_000_000, (char.experience or 0) + exp_gained))

    if t == "quiz_answer":
        stats["quiz_total_count"] = int(stats.get("quiz_total_count") or 0) + 1
        if activity.get("is_correct"):
            stats["quiz_correct_count"] = int(stats.get("quiz_correct_count") or 0) + 1
        _update_quiz_streak(stats, ymd)
    elif t == "quiz_complete":
        correct = int(activity.get("correct_count") or 0)
        total = int(activity.get("total_count") or 0)
        stats["quiz_correct_count"] = int(stats.get("quiz_correct_count") or 0) + correct
        stats["quiz_total_count"] = int(stats.get("quiz_total_count") or 0) + total
        _update_quiz_streak(stats, ymd)
    elif t == "login":
        _update_login_streak(stats, ymd)
    elif t == "steps":
        if activity.get("total_steps") is not None:
            stats["total_steps"] = max(
                int(stats.get("total_steps") or 0),
                int(activity["total_steps"]),
            )
        else:
            stats["total_steps"] = int(stats.get("total_steps") or 0) + int(
                activity.get("steps") or 0
            )
    elif t == "character_born":
        stats["has_character_image"] = True
        if activity.get("hero_preview_url"):
            stats["hero_preview_url"] = activity["hero_preview_url"]
        if activity.get("next_stage_preview_url"):
            stats["next_stage_preview_url"] = activity["next_stage_preview_url"]
        set_preview_urls(
            uid,
            hero_preview_url=stats.get("hero_preview_url"),
            next_stage_preview_url=stats.get("next_stage_preview_url"),
        )

    character_exp = _char_exp(db, uid)
    new_stage = determine_character_stage(stats, character_exp)
    stats["stage"] = new_stage
    evolved = new_stage != prev_stage
    if evolved:
        stats["excited_until"] = (_utc_now() + timedelta(hours=12)).isoformat()

    _save_stats(uid, stats, db)
    db.commit()

    return {
        "stats": stats,
        "exp_gained": exp_gained,
        "stage": new_stage,
        "evolved": evolved,
        "previous_stage": prev_stage,
        "character_exp": character_exp,
    }


def _char_exp(db: Session, uid: str) -> int:
    row = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
    return int(row.experience or 0) if row else 0


def get_character_exp(uid: str) -> int:
    if SessionLocal is None:
        return int(_memory.get(uid, {}).get("character_exp") or 0)
    db = SessionLocal()
    try:
        return _char_exp(db, uid)
    except OperationalError as exc:
        _handle_db_unavailable(exc)
        return int(_memory.get(uid, {}).get("character_exp") or 0)
    finally:
        db.close()


def apply_activity_memory(uid: str, activity: dict[str, Any]) -> dict[str, Any]:
    stats = {**default_stats(), **_memory.get(uid, {})}
    ymd = _utc_now().strftime("%Y-%m-%d")
    prev_stage = determine_character_stage(stats, int(stats.get("character_exp") or 0))
    t = (activity.get("activity_type") or "").strip()
    if activity.get("skip_exp"):
        exp_gained = 0
    else:
        exp_gained = calculate_exp(activity)
        if t == "login" and stats.get("last_login_ymd") == ymd:
            exp_gained = 0

    if t == "quiz_complete":
        stats["quiz_correct_count"] = int(stats.get("quiz_correct_count") or 0) + int(
            activity.get("correct_count") or 0
        )
        stats["quiz_total_count"] = int(stats.get("quiz_total_count") or 0) + int(
            activity.get("total_count") or 0
        )
        _update_quiz_streak(stats, ymd)
    elif t == "character_born":
        stats["has_character_image"] = True
        if activity.get("hero_preview_url"):
            stats["hero_preview_url"] = activity["hero_preview_url"]
        if activity.get("next_stage_preview_url"):
            stats["next_stage_preview_url"] = activity["next_stage_preview_url"]

    character_exp = int(stats.get("character_exp") or 0) + exp_gained
    stats["character_exp"] = character_exp
    new_stage = determine_character_stage(stats, character_exp)
    stats["stage"] = new_stage
    _memory[uid] = stats
    return {
        "stats": stats,
        "exp_gained": exp_gained,
        "stage": new_stage,
        "evolved": new_stage != prev_stage,
        "previous_stage": prev_stage,
        "character_exp": character_exp,
    }


def record_activity(uid: str, activity: dict[str, Any]) -> dict[str, Any]:
    if SessionLocal is None:
        return apply_activity_memory(uid, activity)
    db = SessionLocal()
    try:
        return apply_activity(uid, activity, db)
    except OperationalError as exc:
        _handle_db_unavailable(exc)
        return apply_activity_memory(uid, activity)
    finally:
        db.close()


def fetch_home_status(
    uid: str,
    *,
    daily_steps: int = 0,
    steps_goal: int = 5000,
    quiz_today: bool = False,
    last_quiz_score: int | None = None,
) -> dict[str, Any]:
    if SessionLocal is None:
        stats = {**default_stats(), **_memory.get(uid, {})}
        exp = int(stats.get("character_exp") or 0)
        return build_character_status(
            stats,
            character_id=uid,
            display_name="みーちゃん",
            image_url=None,
            character_exp=exp,
            daily_steps=daily_steps,
            steps_goal=steps_goal,
            quiz_today=quiz_today,
            last_quiz_score=last_quiz_score,
            hero_preview_url=stats.get("hero_preview_url"),
            next_stage_preview_url=stats.get("next_stage_preview_url"),
        )

    db = SessionLocal()
    try:
        char = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
        stats = get_stats(uid, db)
        exp = int(char.experience or 0) if char else 0
        return build_character_status(
            stats,
            character_id=uid,
            display_name=char.display_name if char else "みーちゃん",
            image_url=char.image_url if char else None,
            character_exp=exp,
            daily_steps=daily_steps,
            steps_goal=steps_goal,
            quiz_today=quiz_today,
            last_quiz_score=last_quiz_score,
            hero_preview_url=stats.get("hero_preview_url"),
            next_stage_preview_url=stats.get("next_stage_preview_url"),
        )
    except OperationalError as exc:
        _handle_db_unavailable(exc)
        return fetch_home_status(
            uid,
            daily_steps=daily_steps,
            steps_goal=steps_goal,
            quiz_today=quiz_today,
            last_quiz_score=last_quiz_score,
        )
    finally:
        db.close()
