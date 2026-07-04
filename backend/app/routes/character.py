from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..character_growth import sync_steps_xp
from ..growth_stats_store import record_activity
from . import character_growth_routes
from ..db import get_db
from ..deps import get_current_uid

router = APIRouter(tags=["character"])
router.include_router(character_growth_routes.router)


def _row_to_out(row: models.UserCharacter) -> schemas.CharacterOut:
    return schemas.CharacterOut(
        display_name=row.display_name,
        image_url=row.image_url,
        experience=row.experience,
        level=schemas.character_level_from_xp(row.experience),
    )


@router.get("", response_model=schemas.CharacterOut)
def get_character(uid: str = Depends(get_current_uid), db: Session = Depends(get_db)):
    row = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Character not saved yet")
    return _row_to_out(row)


@router.put("", response_model=schemas.CharacterOut)
def put_character(
    body: schemas.CharacterUpsert,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    row = db.query(models.UserCharacter).filter(models.UserCharacter.user_id == uid).first()
    had_image = bool(row and row.image_url)
    if row:
        row.display_name = body.display_name.strip()
        row.image_url = body.image_url
        row.experience = body.experience
    else:
        row = models.UserCharacter(
            user_id=uid,
            display_name=body.display_name.strip(),
            image_url=body.image_url,
            experience=body.experience,
            steps_growth_ymd=None,
            steps_xp_paid_tier=0,
            steps_xp_goal_bonus=False,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    if body.image_url and not had_image:
        record_activity(
            uid,
            {
                "activity_type": "character_born",
                "hero_preview_url": body.hero_preview_url,
                "next_stage_preview_url": body.next_stage_preview_url,
            },
        )
    return _row_to_out(row)


@router.post("/sync-steps-xp", response_model=schemas.SyncStepsXpOut)
def post_sync_steps_xp(
    body: schemas.SyncStepsXpIn | None = None,
    uid: str = Depends(get_current_uid),
    db: Session = Depends(get_db),
):
    goal = body.goal_steps if body else 5000
    return sync_steps_xp(db, uid, goal)
