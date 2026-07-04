"""成長（経験値）ルール — クイズ日次上限・歩数マイルストーン（サーバー UTC で歩数と揃える）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

QUIZ_XP_DAILY_CAP = 80
STEPS_CHUNK_XP = 2
STEPS_MAX_PAID_CHUNKS = 8
STEPS_GOAL_BONUS_XP = 12


def utc_day_bounds() -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    ymd = start.strftime("%Y-%m-%d")
    return start, end, ymd


def compute_quiz_session_xp_raw(score: int, question_count: int, level: int) -> int:
    n = max(1, question_count)
    pct = min(1.0, max(0.0, score / n))
    base = 8
    bonus = round(22 * pct)
    diff = 1 + 0.12 * max(0, level - 1)
    return int(round((base + bonus) * diff))


def compute_steps_xp_grant(
    steps: int,
    goal: int,
    state_ymd: str | None,
    paid_tier: int,
    goal_bonus_paid: bool,
    today_ymd: str,
) -> tuple[int, list[str], int, bool]:
    """
    戻り値: (xp_to_add, detail_messages, new_paid_tier, new_goal_bonus_paid)
    state_ymd が today と違えば tier / goal をリセット。
    """
    if state_ymd != today_ymd:
        paid_tier = 0
        goal_bonus_paid = False

    s = max(0, int(steps))
    g = max(1000, int(goal))
    current_tier = min(STEPS_MAX_PAID_CHUNKS, s // 1000)

    xp = 0
    detail: list[str] = []

    if current_tier > paid_tier:
        delta = current_tier - paid_tier
        add = delta * STEPS_CHUNK_XP
        xp += add
        detail.append(f"1000歩×{delta} … +{add} XP")
        paid_tier = current_tier

    if s >= g and not goal_bonus_paid:
        xp += STEPS_GOAL_BONUS_XP
        detail.append(f"目標{g:,}歩達成！ +{STEPS_GOAL_BONUS_XP} XP")
        goal_bonus_paid = True

    return xp, detail, paid_tier, goal_bonus_paid
