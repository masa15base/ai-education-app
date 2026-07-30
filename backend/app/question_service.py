"""クイズ用: questions テーブルの読み出し・採点補助。"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from . import db as dbmod
from .models import Question


def _norm_subject(s: Optional[str]) -> str:
    return (s or "math").strip().lower()


def question_row_to_api(q: Question) -> dict[str, Any]:
    raw = q.options
    if isinstance(raw, str):
        try:
            opts = json.loads(raw)
        except Exception:
            opts = []
    elif raw is None:
        opts = []
    elif isinstance(raw, (list, tuple)):
        opts = list(raw)
    else:
        opts = []
    opts = [str(x) for x in opts]

    return {
        "id": q.id,
        "subject": q.subject or "math",
        "level": int(q.level or 1),
        "question_text": q.question_text or "",
        "options": opts,
        "correct_answer": (q.correct_answer or "").strip(),
        "hint": q.hint or "",
        "media": {
            "image_url": q.image_url,
            "audio_url": q.audio_url,
        },
    }


def list_questions_for_quiz(subject: str, level: int, limit: int) -> list[dict[str, Any]]:
    """
    同一 level の行から subject（大文字小文字無視）が一致するものを id 順で最大 limit 件。
    DB 未設定・0 件のときは空リスト（呼び出し側でフォールバック）。
    """
    lim = max(1, min(int(limit), 20))
    if dbmod.SessionLocal is None:
        return []

    subj = _norm_subject(subject)
    db: Session = dbmod.SessionLocal()
    try:
        rows = (
            db.query(Question)
            .filter(Question.level == level)
            .order_by(Question.id)
            .all()
        )
        matched = [r for r in rows if _norm_subject(r.subject) == subj]
        return [question_row_to_api(r) for r in matched[:lim]]
    finally:
        db.close()


def get_question_by_id(question_id: str) -> Optional[dict[str, Any]]:
    if not question_id or dbmod.SessionLocal is None:
        return None
    db = dbmod.SessionLocal()
    try:
        row = db.query(Question).filter(Question.id == question_id).first()
        return question_row_to_api(row) if row else None
    finally:
        db.close()


def questions_for_quiz(subject: str, level: int, limit: int) -> list[dict[str, Any]]:
    """
    questions テーブルを優先し、件数不足時は quiz_engine の動的問題で埋める。
    算数・英語も含む全教科共通。
    """
    from .quiz_engine import make_question, make_questions

    lim = max(1, min(int(limit), 20))
    db_rows = list_questions_for_quiz(subject, level, lim)
    if len(db_rows) >= lim:
        return db_rows[:lim]

    dynamic = make_questions(subject, level, lim)
    if not db_rows:
        return dynamic

    merged = list(db_rows)
    used_ids = {str(r.get("id")) for r in merged}
    for q in dynamic:
        if len(merged) >= lim:
            break
        qid = str(q.get("id") or "")
        if qid and qid not in used_ids:
            merged.append(q)
            used_ids.add(qid)

    # まだ足りない場合（ID 衝突など）はインデックスをずらして補充
    extra_i = lim + 1
    while len(merged) < lim and extra_i <= lim + 30:
        q = make_question(subject, level, extra_i)
        extra_i += 1
        qid = str(q.get("id") or "")
        if qid and qid not in used_ids:
            merged.append(q)
            used_ids.add(qid)

    return merged[:lim]
