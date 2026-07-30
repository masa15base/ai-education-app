"""/api/questions の出題元（DB 優先 → 動的フォールバック）を確認。"""

from fastapi.testclient import TestClient

from app.main import app
from app.growth_service import compute_quiz_session_xp_raw
from app.services.character_growth import calculate_exp

client = TestClient(app)


def test_questions_math_prefers_db_when_enough(monkeypatch):
    """算数でも DB に十分な件数があれば DB を返す。"""

    def fake_db(subject: str, level: int, limit: int):
        return [
            {
                "id": "math-db-1",
                "subject": "math",
                "level": 1,
                "question_text": "DB question 1",
                "options": ["a", "b", "c", "d"],
                "correct_answer": "a",
                "hint": "db",
                "media": {"image_url": None, "audio_url": None},
            },
            {
                "id": "math-db-2",
                "subject": "math",
                "level": 1,
                "question_text": "DB question 2",
                "options": ["a", "b", "c", "d"],
                "correct_answer": "b",
                "hint": "db",
                "media": {"image_url": None, "audio_url": None},
            },
        ]

    called = {"fallback": 0}

    def fake_fallback(subject: str, level: int, limit: int):
        called["fallback"] += 1
        return []

    monkeypatch.setattr("app.question_service.list_questions_for_quiz", fake_db)
    monkeypatch.setattr("app.quiz_engine.make_questions", fake_fallback)

    r = client.get("/api/questions?subject=math&level=1&limit=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 2
    assert body[0]["id"] == "math-db-1"
    assert body[0]["question_text"] == "DB question 1"
    assert called["fallback"] == 0


def test_questions_english_pads_with_dynamic(monkeypatch):
    """英語で DB が不足なら動的問題で埋める。"""

    def fake_db(subject: str, level: int, limit: int):
        return [
            {
                "id": "eng-db-1",
                "subject": "english",
                "level": 1,
                "question_text": "DB only one",
                "options": ["a", "b", "c", "d"],
                "correct_answer": "a",
                "hint": "db",
                "media": {"image_url": None, "audio_url": None},
            }
        ]

    monkeypatch.setattr("app.question_service.list_questions_for_quiz", fake_db)

    r = client.get("/api/questions?subject=english&level=1&limit=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 2
    assert body[0]["id"] == "eng-db-1"
    assert body[1]["id"] != "eng-db-1"
    assert "意味はどれ" in body[1]["question_text"] or "Dog" in body[1]["question_text"] or '"' in body[1]["question_text"]


def test_questions_math_dynamic_fallback_when_empty(monkeypatch):
    monkeypatch.setattr(
        "app.question_service.list_questions_for_quiz",
        lambda *a, **k: [],
    )
    r = client.get("/api/questions?subject=math&level=1&limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 5
    for q in body:
        assert len(q["options"]) == 4, q


def test_quiz_complete_xp_formula_aligned():
    """成長 calculate_exp(quiz_complete) と progress 式が一致する。"""
    via_growth = calculate_exp(
        {
            "activity_type": "quiz_complete",
            "correct_count": 5,
            "total_count": 5,
            "level": 1,
        }
    )
    via_progress = compute_quiz_session_xp_raw(5, 5, 1)
    assert via_growth == via_progress
    assert via_growth > 0
