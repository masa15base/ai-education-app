"""クイズ用: questions テーブルの読み出し・採点補助。"""

from __future__ import annotations

from typing import Any, Optional

from . import db as dbmod
from .models import Question
from .question_bank import pick_questions_from_bank, question_orm_to_dict


def question_row_to_api(q: Question) -> dict[str, Any]:
    return question_orm_to_dict(q)


def list_questions_for_quiz(subject: str, level: int, limit: int) -> list[dict[str, Any]]:
    """
    同一 subject+level からランダムに最大 limit 件。
    DB 未設定・0 件のときは空リスト（呼び出し側でフォールバック）。
    """
    lim = max(1, min(int(limit), 20))
    return pick_questions_from_bank(subject, level, lim)


def get_question_by_id(question_id: str) -> Optional[dict[str, Any]]:
    if not question_id or dbmod.SessionLocal is None:
        return None
    db = dbmod.SessionLocal()
    try:
        row = db.query(Question).filter(Question.id == question_id).first()
        return question_orm_to_dict(row) if row else None
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

    extra_i = lim + 1
    while len(merged) < lim and extra_i <= lim + 30:
        q = make_question(subject, level, extra_i)
        extra_i += 1
        qid = str(q.get("id") or "")
        if qid and qid not in used_ids:
            merged.append(q)
            used_ids.add(qid)

    return merged[:lim]
