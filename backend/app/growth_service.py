"""成長（経験値）ルール — クイズ日次上限・歩数マイルストーン（日付は JST）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

QUIZ_XP_DAILY_CAP = 80
STEPS_CHUNK_XP = 2
STEPS_MAX_PAID_CHUNKS = 8
STEPS_GOAL_BONUS_XP = 12

APP_TZ = ZoneInfo("Asia/Tokyo")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def app_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime, str]:
    """JST 暦日の [start, end) を UTC aware datetime で返す。ymd は JST の YYYY-MM-DD。"""
    now_utc = _as_utc(now or datetime.now(timezone.utc))
    local = now_utc.astimezone(APP_TZ)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    ymd = start_local.strftime("%Y-%m-%d")
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), ymd


def app_ymd(now: datetime | None = None) -> str:
    return app_day_bounds(now)[2]


def app_day_keys(days: int = 7, now: datetime | None = None) -> list[str]:
    """直近 days 日分の JST 日付キー（古い→新しい）。"""
    _, _, today = app_day_bounds(now)
    base = datetime.strptime(today, "%Y-%m-%d").date()
    return [(base - timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(days - 1, -1, -1)]


def to_app_ymd(dt: datetime) -> str:
    """タイムスタンプを JST 暦日の YYYY-MM-DD に変換。"""
    return _as_utc(dt).astimezone(APP_TZ).strftime("%Y-%m-%d")


def utc_day_bounds() -> tuple[datetime, datetime, str]:
    """互換 alias。実体は JST 暦日境界。"""
    return app_day_bounds()


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
