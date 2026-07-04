"""歩数に応じた経験値付与（DB 上のキャラ状態で冪等）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import growth_service
from .models import UserCharacter
from .schemas import character_level_from_xp
from .steps_service import get_steps_today


def sync_steps_xp(db: Session, uid: str, goal_steps: int = 5000) -> dict:
    """
    当日 UTC の歩数と user_characters の steps_* 列からボーナス XP を計算し加算。
    戻り値: xp_gained, detail(list[str]), experience, level, display_name, image_url
    """
    _, _, ymd = growth_service.utc_day_bounds()
    steps, _ = get_steps_today(uid, ymd)

    char = db.query(UserCharacter).filter(UserCharacter.user_id == uid).first()
    if not char:
        char = UserCharacter(
            user_id=uid,
            display_name="みーちゃん",
            image_url=None,
            experience=0,
            steps_growth_ymd=None,
            steps_xp_paid_tier=0,
            steps_xp_goal_bonus=False,
        )
        db.add(char)
        db.flush()

    xp_add, detail, new_tier, new_goal = growth_service.compute_steps_xp_grant(
        steps,
        goal_steps,
        char.steps_growth_ymd,
        int(char.steps_xp_paid_tier or 0),
        bool(char.steps_xp_goal_bonus),
        ymd,
    )

    char.steps_growth_ymd = ymd
    char.steps_xp_paid_tier = new_tier
    char.steps_xp_goal_bonus = new_goal
    if xp_add > 0:
        char.experience = max(0, min(1_000_000, (char.experience or 0) + xp_add))

    db.commit()
    db.refresh(char)
    xp = int(char.experience or 0)
    return {
        "xp_gained": xp_add,
        "detail": detail,
        "experience": xp,
        "level": character_level_from_xp(xp),
        "display_name": char.display_name or "みーちゃん",
        "image_url": char.image_url,
    }
