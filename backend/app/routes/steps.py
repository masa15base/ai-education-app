"""歩数 API（手入力・端末同期のスケッチ。HealthKit 等は将来差し替え）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_current_uid, get_optional_uid
from ..growth_service import app_day_keys, app_ymd
from ..schemas import (
    StepsPutIn,
    StepsPutOut,
    StepsSyncDeviceIn,
    StepsSyncDeviceDayOut,
    StepsSyncDeviceOut,
    StepsTodayOut,
    StepsWeekDayOut,
    StepsWeekOut,
)
from ..growth_stats_store import record_activity
from ..steps_service import get_steps_today, list_steps_week, merge_steps_for_day, set_steps_today

DEFAULT_STEPS_GOAL = 5000

router = APIRouter(tags=["steps"])


@router.get("/today", response_model=StepsTodayOut)
def steps_today(uid: str | None = Depends(get_optional_uid)):
    day = app_ymd()
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
    day = app_ymd()
    prev, _ = get_steps_today(uid, day)
    n, src = set_steps_today(uid, body.steps, day, source="manual")
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


@router.post("/sync-from-device", response_model=StepsSyncDeviceOut)
def steps_sync_from_device(body: StepsSyncDeviceIn, uid: str = Depends(get_current_uid)):
    """ネイティブアプリ（Health Connect / HealthKit）から歩数をマージ同期。"""
    day = app_ymd()
    synced: list[StepsSyncDeviceDayOut] = []
    total_delta = 0
    today_steps, _ = get_steps_today(uid, day)

    for entry in body.days:
        merged, delta = merge_steps_for_day(
            uid,
            entry.steps,
            entry.ymd,
            source=body.source,
        )
        synced.append(
            StepsSyncDeviceDayOut(date=entry.ymd, steps=merged, delta_applied=delta)
        )
        if entry.ymd == day:
            total_delta = delta
            today_steps = merged

    if total_delta > 0:
        record_activity(
            uid,
            {
                "activity_type": "steps",
                "steps": total_delta,
                "goal_reached": int(today_steps) >= DEFAULT_STEPS_GOAL,
            },
        )

    return StepsSyncDeviceOut(
        source=body.source,
        today_ymd=day,
        today_steps=int(today_steps),
        delta_applied=total_delta,
        synced_days=synced,
    )


@router.get("/week", response_model=StepsWeekOut)
def steps_week(uid: str | None = Depends(get_optional_uid)):
    day = app_ymd()
    if not uid:
        empty_days = [
            StepsWeekDayOut(date=d, steps=0, goal_reached=False)
            for d in app_day_keys(7)
        ]
        return StepsWeekOut(
            authenticated=False,
            today_ymd=day,
            goal_steps=DEFAULT_STEPS_GOAL,
            source="none",
            days=empty_days,
        )

    rows, src = list_steps_week(uid, goal_steps=DEFAULT_STEPS_GOAL)
    return StepsWeekOut(
        authenticated=True,
        today_ymd=day,
        goal_steps=DEFAULT_STEPS_GOAL,
        source=src,
        days=[StepsWeekDayOut(**row) for row in rows],
    )
