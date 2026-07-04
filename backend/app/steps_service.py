"""今日の歩数（手入力・デモ用）。DB 無し時はプロセス内メモリ。"""

from __future__ import annotations

from datetime import datetime, timezone

from . import db as dbmod
from .models import DailyStep


def _ymd_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


_memory: dict[str, int] = {}


def _key(uid: str, ymd: str) -> str:
    return f"{uid}|{ymd}"


def get_steps_today(uid: str, ymd: str | None = None) -> tuple[int, str]:
    """戻り値: (steps, source) source は database | memory"""
    day = ymd or _ymd_utc()
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
    day = ymd or _ymd_utc()
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
