"""今日の歩数（手入力・デモ用）。DB 無し時はプロセス内メモリ。日付キーは JST。"""

from __future__ import annotations

from . import db as dbmod
from .growth_service import app_day_keys, app_ymd
from .models import DailyStep


def _ymd_today() -> str:
    return app_ymd()


def _day_keys(days: int = 7) -> list[str]:
    return app_day_keys(days)


# 互換（routes から参照される旧名）
_ymd_utc = _ymd_today
_day_keys_utc = _day_keys


_memory: dict[str, int] = {}


def _key(uid: str, ymd: str) -> str:
    return f"{uid}|{ymd}"


def get_steps_today(uid: str, ymd: str | None = None) -> tuple[int, str]:
    """戻り値: (steps, source) source は database | memory"""
    day = ymd or _ymd_today()
    if dbmod.SessionLocal is None:
        return _memory.get(_key(uid, day), 0), "memory"

    db = dbmod.SessionLocal()
    try:
        row = (
            db.query(DailyStep)
            .filter(DailyStep.user_id == uid, DailyStep.step_date == day)
            .first()
        )
        if row is None:
            return 0, "database"
        return int(row.steps or 0), "database"
    finally:
        db.close()


def set_steps_today(uid: str, steps: int, ymd: str | None = None) -> tuple[int, str]:
    day = ymd or _ymd_today()
    steps = max(0, min(999_999, int(steps)))

    if dbmod.SessionLocal is None:
        _memory[_key(uid, day)] = steps
        return steps, "memory"

    db = dbmod.SessionLocal()
    try:
        row = (
            db.query(DailyStep)
            .filter(DailyStep.user_id == uid, DailyStep.step_date == day)
            .first()
        )
        if row is None:
            row = DailyStep(user_id=uid, step_date=day, steps=steps)
            db.add(row)
        else:
            row.steps = steps
        db.commit()
        db.refresh(row)
        return int(row.steps), "database"
    finally:
        db.close()


def list_steps_week(
    uid: str,
    *,
    days: int = 7,
    goal_steps: int = 5000,
) -> tuple[list[dict[str, object]], str]:
    """直近 days 日分の歩数。戻り値: ([{date, steps, goal_reached}, ...], source)"""
    keys = _day_keys(days)
    goal_steps = max(1000, int(goal_steps))

    if dbmod.SessionLocal is None:
        rows = [
            {
                "date": day,
                "steps": int(_memory.get(_key(uid, day), 0)),
                "goal_reached": int(_memory.get(_key(uid, day), 0)) >= goal_steps,
            }
            for day in keys
        ]
        return rows, "memory"

    db = dbmod.SessionLocal()
    try:
        db_rows = (
            db.query(DailyStep)
            .filter(
                DailyStep.user_id == uid,
                DailyStep.step_date.in_(keys),
            )
            .all()
        )
        by_day = {r.step_date: int(r.steps or 0) for r in db_rows}
        rows = [
            {
                "date": day,
                "steps": by_day.get(day, 0),
                "goal_reached": by_day.get(day, 0) >= goal_steps,
            }
            for day in keys
        ]
        return rows, "database"
    finally:
        db.close()
