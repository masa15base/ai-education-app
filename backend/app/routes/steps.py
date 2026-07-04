"""歩数 API（手入力・端末同期のスケッチ。HealthKit 等は将来差し替え）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..deps import get_current_uid, get_optional_uid
from ..schemas import StepsPutIn, StepsPutOut, StepsTodayOut
from ..growth_stats_store import record_activity
from ..steps_service import get_steps_today, set_steps_today

DEFAULT_STEPS_GOAL = 5000

router = APIRouter(tags=["steps"])


def _ymd_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@router.get("/today", response_model=StepsTodayOut)
def steps_today(uid: str | None = Depends(get_optional_uid)):
    day = _ymd_utc()
    if not uid:
        return StepsTodayOut(
            authenticated=False,
            today_ymd=day,
            steps=None,
            source="none",
            hint="ログインすると、この端末と同じ日付の歩数をサーバーに保存できます。未ログイン時はブラウザのデモ記録のみです。",
        )
    n, src = get_steps_today(uid, day)
    return StepsTodayOut(
        authenticated=True,
        today_ymd=day,
        steps=n,
        source=src,
        hint=None,
    )


@router.put("/today", response_model=StepsPutOut)
def steps_today_put(body: StepsPutIn, uid: str = Depends(get_current_uid)):
    day = _ymd_utc()
    prev, _ = get_steps_today(uid, day)
    n, src = set_steps_today(uid, body.steps, day)
    delta = max(0, int(n) - int(prev or 0))
    if delta > 0 or n > 0:
        record_activity(
            uid,
            {
                "activity_type": "steps",
                "steps": delta,
                "goal_reached": int(n) >= DEFAULT_STEPS_GOAL,
            },
        )
    return StepsPutOut(today_ymd=day, steps=n, source=src)
