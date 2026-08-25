from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_optional_uid
from app.quiz_engine import make_question

client = TestClient(app)


def test_quiz_verify_math():
    q = make_question("math", 1, 1)
    r = client.post(
        "/api/quiz/verify",
        json={
            "subject": "math",
            "level": 1,
            "question_index": 1,
            "selected_answer": q["correct_answer"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["correct"] is True
    assert body["correct_answer"] == q["correct_answer"]


def test_quiz_verify_english_dynamic():
    r = client.post(
        "/api/quiz/verify",
        json={
            "subject": "english",
            "level": 1,
            "question_index": 1,
            "selected_answer": "いぬ",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["correct"] is True
    assert body["correct_answer"] == "いぬ"


def test_quiz_complete_anonymous():
    q1 = make_question("math", 1, 1)
    q2 = make_question("math", 1, 2)
    r = client.post(
        "/api/quiz/complete",
        json={
            "subject": "math",
            "level": 1,
            "answers": [
                {"question_index": 1, "selected_answer": q1["correct_answer"]},
                {"question_index": 2, "selected_answer": "99999"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["correct"] == 1
    assert body["saved"] is False


def test_quiz_complete_saves_with_auth_override():
    def fake_uid():
        return "u1"

    app.dependency_overrides[get_optional_uid] = fake_uid
    try:
        r = client.post(
            "/api/quiz/complete",
            json={
                "subject": "math",
                "level": 1,
                "answers": [
                    {"question_index": 1, "selected_answer": make_question("math", 1, 1)["correct_answer"]},
                ],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["saved"] is True
        # メモリモードでも growth 経由で XP > 0（DB 時は progress 日次上限付き）
        assert body["gained_xp"] > 0
        assert body["growth"]["exp_gained"] == body["gained_xp"]
    finally:
        app.dependency_overrides.clear()


def test_quiz_complete_xp_matches_formula():
    from app.growth_service import compute_quiz_session_xp_raw

    def fake_uid():
        return "xp-unify-user"

    app.dependency_overrides[get_optional_uid] = fake_uid
    try:
        answers = []
        for i in range(1, 6):
            q = make_question("math", 2, i)
            answers.append(
                {
                    "question_index": i,
                    "question_id": q["id"],
                    "selected_answer": q["correct_answer"],
                }
            )
        r = client.post(
            "/api/quiz/complete",
            json={"subject": "math", "level": 2, "answers": answers},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        expected = compute_quiz_session_xp_raw(5, 5, 2)
        assert body["correct"] == 5
        assert body["gained_xp"] == expected
    finally:
        app.dependency_overrides.clear()
