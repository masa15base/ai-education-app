"""動的クイズの共通ロジック（GET /api/questions と採点で同一のルールを使う）。"""
from __future__ import annotations

from .english_vocab import english_question_parts
from .math_dynamic import math_question_parts


def make_question(subject: str, level: int, idx: int) -> dict:
    """
    idx: 1 始まり（レベル内の問題番号）
    id はサーバ・クライアントで再計算可能な決定的な値。
    """
    subj = (subject or "math").lower()
    qid = f"{subj}-{level}-{idx}"
    if subj == "math":
        text, correct, options, hint = math_question_parts(level, idx)
    else:
        _w, correct, options, hint, text = english_question_parts(level, idx)
    return {
        "id": qid,
        "subject": subject,
        "level": level,
        "question_text": text,
        "options": options,
        "correct_answer": correct,
        "hint": hint,
        "media": {"image_url": None, "audio_url": None},
    }


def make_questions(subject: str, level: int, limit: int = 5) -> list[dict]:
    try:
        limit = max(1, min(int(limit), 10))
    except Exception:
        limit = 5
    return [make_question(subject, level, i) for i in range(1, limit + 1)]


def grade_answers(
    subject: str,
    level: int,
    answer_rows: list[tuple[int, str]],
) -> tuple[int, int, list[dict]]:
    """
    answer_rows: (question_index 1-based, selected_answer)
    返り値: (正解数, 問題数, 詳細リスト)
    """
    details: list[dict] = []
    correct_n = 0
    for q_idx, selected in answer_rows:
        q = make_question(subject, level, q_idx)
        ok = (selected or "").strip() == (q["correct_answer"] or "").strip()
        if ok:
            correct_n += 1
        details.append(
            {
                "question_index": q_idx,
                "question_id": q["id"],
                "selected_answer": selected,
                "correct_answer": q["correct_answer"],
                "correct": ok,
                "hint": q["hint"],
            }
        )
    return correct_n, len(answer_rows), details
