"""/api/questions の出題元（動的 vs DB）を確認。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_questions_math_always_dynamic(monkeypatch):
    """算数は DB があっても quiz_engine の動的4択を返す。"""

    def fake_db(subject: str, level: int, limit: int):
        return [
            {
                "id": "math-1-001",
                "subject": "math",
                "level": 1,
                "question_text": "DB question 1",
                "options": ["a", "b", "c"],
                "correct_answer": "a",
                "hint": "db",
                "media": {"image_url": None, "audio_url": None},
            },
            {
                "id": "math-1-002",
                "subject": "math",
                "level": 1,
                "question_text": "DB question 2",
                "options": ["a", "b", "c"],
                "correct_answer": "b",
                "hint": "db",
                "media": {"image_url": None, "audio_url": None},
            },
        ]

    called = {"fallback": 0}

    def fake_fallback(subject: str, level: int, limit: int):
        called["fallback"] += 1
        return []

    monkeypatch.setattr("app.main.list_questions_for_quiz", fake_db)
    monkeypatch.setattr("app.main.make_questions", fake_fallback)

    r = client.get("/api/questions?subject=math&level=1&limit=2")
    assert r.status_code == 200, r.text
    assert called["fallback"] == 1


def test_questions_english_always_dynamic(monkeypatch):
    """英語は DB があっても quiz_engine の動的語彙を返す。"""

    def fake_db(subject: str, level: int, limit: int):
        return [
            {
                "id": "eng-old",
                "subject": "english",
                "level": 1,
                "question_text": "英単語 '猫' はどれ？",
                "options": ["cat", "dog"],
                "correct_answer": "cat",
                "hint": "old",
                "media": {"image_url": None, "audio_url": None},
            }
        ]

    monkeypatch.setattr("app.main.list_questions_for_quiz", fake_db)

    r = client.get("/api/questions?subject=english&level=1&limit=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 2
    assert '"Dog"' in body[0]["question_text"]
    assert body[0]["correct_answer"] == "いぬ"


def test_questions_math_dynamic_has_four_options():
    r = client.get("/api/questions?subject=math&level=1&limit=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 5
    for q in body:
        assert len(q["options"]) == 4, q
