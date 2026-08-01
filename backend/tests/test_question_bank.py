"""問題バンク運用の単体テスト。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.question_bank import (
    RECOMMENDED_MIN_PER_LEVEL,
    load_questions_csv,
    normalize_question_row,
)
from app.quiz_options import four_string_options

client = TestClient(app)

CSV_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "questions_level_10_final.csv"


def test_normalize_pads_to_four_options():
    row = normalize_question_row(
        {
            "id": "t-1",
            "subject": "math",
            "level": 1,
            "question_text": "1+1?",
            "options": json.dumps(["2", "3"]),
            "correct_answer": "2",
            "hint": "hint",
        }
    )
    assert len(row["options"]) == 4
    assert "2" in row["options"]


def test_four_string_options_includes_correct():
    opts = four_string_options("いぬ", ["ねこ", "とり"], seed="x")
    assert len(opts) == 4
    assert "いぬ" in opts
    assert all("選択肢" not in o for o in opts)


def test_four_string_options_replaces_placeholder_and_numeric_pad():
    opts = four_string_options("8", ["9", "7", "（選択肢4）"], seed="math-4-001")
    assert len(opts) == 4
    assert "8" in opts
    assert all("選択肢" not in o for o in opts)
    assert all(o.lstrip("-").isdigit() for o in opts)


def test_seed_csv_loads_and_covers_levels():
    assert CSV_PATH.is_file(), CSV_PATH
    rows = load_questions_csv(CSV_PATH)
    assert len(rows) == 100
    for r in rows:
        assert len(r["options"]) == 4
        assert r["correct_answer"] in r["options"]
        assert all("選択肢" not in o for o in r["options"]), r
    math_l1 = [r for r in rows if r["subject"] == "math" and r["level"] == 1]
    eng_l1 = [r for r in rows if r["subject"] == "english" and r["level"] == 1]
    assert len(math_l1) >= RECOMMENDED_MIN_PER_LEVEL
    assert len(eng_l1) >= RECOMMENDED_MIN_PER_LEVEL


def test_bank_stats_endpoint_without_db():
    r = client.get("/api/questions/bank-stats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "database_configured" in body
    assert "recommended_min_per_level" in body
    assert body["recommended_min_per_level"] == 5
    assert "gaps" in body
    assert "total" in body


def test_import_dry_run_from_csv():
    from app.question_bank import import_questions

    rows = load_questions_csv(CSV_PATH)
    summary = import_questions(rows, mode="upsert", dry_run=True)
    assert summary["dry_run"] is True
    assert summary["total_rows"] == 100
    assert summary["inserted"] == 0
