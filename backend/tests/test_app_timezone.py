"""日付境界は JST（Asia/Tokyo）。"""
from __future__ import annotations

from datetime import datetime, timezone

from app.growth_service import app_day_bounds, app_day_keys, app_ymd, to_app_ymd


def test_app_day_bounds_jst_around_midnight():
    # UTC 2026-07-31 15:30 = JST 2026-08-01 00:30 → 日付は 8/1
    now = datetime(2026, 7, 31, 15, 30, tzinfo=timezone.utc)
    start, end, ymd = app_day_bounds(now)
    assert ymd == "2026-08-01"
    assert start == datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)


def test_app_day_bounds_before_jst_midnight_stays_previous_day():
    # UTC 2026-07-31 14:59 = JST 2026-07-31 23:59 → まだ 7/31
    now = datetime(2026, 7, 31, 14, 59, tzinfo=timezone.utc)
    _, _, ymd = app_day_bounds(now)
    assert ymd == "2026-07-31"


def test_to_app_ymd_and_keys():
    assert to_app_ymd(datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc)) == "2026-08-01"
    keys = app_day_keys(3, now=datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc))
    assert keys == ["2026-07-30", "2026-07-31", "2026-08-01"]
    assert app_ymd(datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)) == "2026-08-01"
