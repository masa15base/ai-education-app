"""問題バンク運用: CSV 検証・投入・カバレッジ集計。"""
from __future__ import annotations

import ast
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import db as dbmod
from .models import Question
from .quiz_options import four_string_options

RECOMMENDED_MIN_PER_LEVEL = 5
Mode = Literal["upsert", "replace"]


def _norm_subject(s: Optional[str]) -> str:
    return (s or "math").strip().lower()


def parse_options_cell(raw: Any) -> list[str]:
    if raw is None or (isinstance(raw, float) and str(raw) == "nan"):
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [p.strip() for p in s.split("|") if p.strip()]


def normalize_question_row(row: dict[str, Any]) -> dict[str, Any]:
    """1行を DB / API 向けに正規化。不正なら ValueError。"""
    qid = str(row.get("id") or "").strip()
    if not qid:
        raise ValueError("id が空です")
    if len(qid) > 50:
        raise ValueError(f"id が長すぎます: {qid}")

    subject = _norm_subject(str(row.get("subject") or "math"))
    try:
        level = int(row.get("level") or 1)
    except (TypeError, ValueError) as e:
        raise ValueError(f"level が不正です: {row.get('level')}") from e
    if level < 1 or level > 99:
        raise ValueError(f"level は 1〜99: {level}")

    text = str(row.get("question_text") or "").strip()
    if not text:
        raise ValueError(f"{qid}: question_text が空です")

    correct = str(row.get("correct_answer") or "").strip()
    if not correct:
        raise ValueError(f"{qid}: correct_answer が空です")

    options = parse_options_cell(row.get("options"))
    options = four_string_options(correct, options, seed=qid)
    if correct not in options:
        raise ValueError(f"{qid}: correct_answer が options に含まれません")

    hint = str(row.get("hint") or "").strip() or None
    image_url = row.get("image_url")
    audio_url = row.get("audio_url")
    if image_url is not None and str(image_url).strip() in ("", "nan", "None"):
        image_url = None
    else:
        image_url = str(image_url).strip() if image_url is not None else None
    if audio_url is not None and str(audio_url).strip() in ("", "nan", "None"):
        audio_url = None
    else:
        audio_url = str(audio_url).strip() if audio_url is not None else None

    return {
        "id": qid,
        "subject": subject,
        "level": level,
        "question_text": text,
        "options": options,
        "correct_answer": correct,
        "hint": hint,
        "image_url": image_url,
        "audio_url": audio_url,
    }


def load_questions_csv(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with p.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"id", "subject", "level", "question_text", "options", "correct_answer"}
        if not reader.fieldnames:
            raise ValueError("CSV にヘッダがありません")
        missing = required - {h.strip() for h in reader.fieldnames if h}
        if missing:
            raise ValueError(f"CSV ヘッダ不足: {sorted(missing)}")
        for i, raw in enumerate(reader, start=2):
            try:
                rows.append(normalize_question_row(raw))
            except ValueError as e:
                errors.append(f"L{i}: {e}")
    if errors:
        preview = "; ".join(errors[:8])
        more = f" …他{len(errors) - 8}件" if len(errors) > 8 else ""
        raise ValueError(f"CSV 検証エラー ({len(errors)}件): {preview}{more}")
    if not rows:
        raise ValueError("CSV に有効な行がありません")
    return rows


def _apply_row(db: Session, row: dict[str, Any]) -> str:
    """戻り値: inserted | updated"""
    existing = db.query(Question).filter(Question.id == row["id"]).first()
    opts = row["options"]
    if existing:
        existing.subject = row["subject"]
        existing.level = row["level"]
        existing.question_text = row["question_text"]
        existing.options = opts
        existing.correct_answer = row["correct_answer"]
        existing.hint = row["hint"]
        existing.image_url = row["image_url"]
        existing.audio_url = row["audio_url"]
        return "updated"
    db.add(
        Question(
            id=row["id"],
            subject=row["subject"],
            level=row["level"],
            question_text=row["question_text"],
            options=opts,
            correct_answer=row["correct_answer"],
            hint=row["hint"],
            image_url=row["image_url"],
            audio_url=row["audio_url"],
        )
    )
    return "inserted"


def import_questions(
    rows: Iterable[dict[str, Any]],
    *,
    mode: Mode = "upsert",
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    DB に投入。SessionLocal が無い場合は ValueError。
    mode=replace は全削除後に挿入。upsert は id 単位で更新/追加。
    """
    normalized = [normalize_question_row(dict(r)) for r in rows]
    ids = [r["id"] for r in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("投入データ内で id が重複しています")

    summary: dict[str, Any] = {
        "mode": mode,
        "dry_run": dry_run,
        "total_rows": len(normalized),
        "inserted": 0,
        "updated": 0,
        "deleted": 0,
        "by_subject_level": _count_map(normalized),
    }

    if dry_run:
        return summary

    if dbmod.SessionLocal is None:
        raise ValueError("データベース未設定（JAWSDB_URL）")

    db = dbmod.SessionLocal()
    try:
        if mode == "replace":
            summary["deleted"] = db.query(Question).delete()
            for row in normalized:
                _apply_row(db, row)
                summary["inserted"] += 1
        else:
            for row in normalized:
                action = _apply_row(db, row)
                if action == "inserted":
                    summary["inserted"] += 1
                else:
                    summary["updated"] += 1
        db.commit()
        summary["by_subject_level"] = bank_coverage_counts(db)
        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _count_map(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, int], int] = defaultdict(int)
    for r in rows:
        counts[(_norm_subject(r["subject"]), int(r["level"]))] += 1
    return [
        {"subject": s, "level": lv, "count": c}
        for (s, lv), c in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1]))
    ]


def bank_coverage_counts(db: Session | None = None) -> list[dict[str, Any]]:
    own = False
    if db is None:
        if dbmod.SessionLocal is None:
            return []
        db = dbmod.SessionLocal()
        own = True
    try:
        rows = (
            db.query(Question.subject, Question.level, func.count(Question.id))
            .group_by(Question.subject, Question.level)
            .all()
        )
        out = []
        for subj, level, cnt in rows:
            out.append(
                {
                    "subject": _norm_subject(subj),
                    "level": int(level or 1),
                    "count": int(cnt),
                }
            )
        out.sort(key=lambda r: (r["subject"], r["level"]))
        return out
    finally:
        if own:
            db.close()


def bank_stats() -> dict[str, Any]:
    if dbmod.SessionLocal is None:
        return {
            "database_configured": False,
            "total": 0,
            "by_subject_level": [],
            "gaps": [],
            "recommended_min_per_level": RECOMMENDED_MIN_PER_LEVEL,
            "ready_for_quiz": False,
        }

    db = dbmod.SessionLocal()
    try:
        total = db.query(func.count(Question.id)).scalar() or 0
        coverage = bank_coverage_counts(db)
        subjects = sorted({c["subject"] for c in coverage} | {"math", "english"})
        levels = range(1, 11)
        gap_list: list[dict[str, Any]] = []
        for subj in subjects:
            for lv in levels:
                found = next(
                    (c for c in coverage if c["subject"] == subj and c["level"] == lv),
                    None,
                )
                cnt = found["count"] if found else 0
                if cnt < RECOMMENDED_MIN_PER_LEVEL:
                    gap_list.append(
                        {
                            "subject": subj,
                            "level": lv,
                            "count": cnt,
                            "needed": RECOMMENDED_MIN_PER_LEVEL - cnt,
                        }
                    )
        return {
            "database_configured": True,
            "total": int(total),
            "by_subject_level": coverage,
            "gaps": gap_list,
            "recommended_min_per_level": RECOMMENDED_MIN_PER_LEVEL,
            "ready_for_quiz": int(total) >= RECOMMENDED_MIN_PER_LEVEL,
        }
    finally:
        db.close()


def question_orm_to_dict(q: Question) -> dict[str, Any]:
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
    correct = (q.correct_answer or "").strip()
    qid = str(q.id or "q")
    opts = four_string_options(correct, opts, seed=qid)
    return {
        "id": q.id,
        "subject": q.subject or "math",
        "level": int(q.level or 1),
        "question_text": q.question_text or "",
        "options": opts,
        "correct_answer": correct,
        "hint": q.hint or "",
        "media": {
            "image_url": q.image_url,
            "audio_url": q.audio_url,
        },
    }


def pick_questions_from_bank(subject: str, level: int, limit: int) -> list[dict[str, Any]]:
    """DB からランダムに最大 limit 件（dict）。未設定なら空。"""
    lim = max(1, min(int(limit), 20))
    if dbmod.SessionLocal is None:
        return []
    subj = _norm_subject(subject)
    db = dbmod.SessionLocal()
    try:
        rows = (
            db.query(Question)
            .filter(Question.level == level)
            .filter(func.lower(Question.subject) == subj)
            .all()
        )
        if not rows:
            return []
        if len(rows) <= lim:
            random.shuffle(rows)
            picked = rows
        else:
            picked = random.sample(rows, lim)
        return [question_orm_to_dict(r) for r in picked]
    finally:
        db.close()
