"""quiz_engine の動的問題（算数・英語）。"""

from app.quiz_engine import make_question


def test_make_question_math_level1_idx1_subtraction():
    q = make_question("math", 1, 1)
    assert q["id"] == "math-1-1"
    assert q["question_text"] == "9 - 2 は？"
    assert q["correct_answer"] == "7"
    assert len(q["options"]) == 4
    assert "7" in q["options"]


def test_make_question_math_level1_idx2_multiplication():
    q = make_question("math", 1, 2)
    assert q["question_text"] == "2 × 3 は？"
    assert q["correct_answer"] == "6"


def test_make_question_math_level1_idx3_addition():
    q = make_question("math", 1, 3)
    assert q["question_text"] == "4 + 3 は？"
    assert q["correct_answer"] == "7"


def test_make_question_math_level1_idx5_division():
    q = make_question("math", 1, 5)
    assert "÷" in q["question_text"]
    assert q["correct_answer"] == "5"
    assert q["question_text"] == "30 ÷ 6 は？"


def test_make_question_math_level5_idx1_multiplication_band():
    """v = (5+1-1)%6 = 5 → 割り算"""
    q = make_question("math", 5, 1)
    assert "÷" in q["question_text"]


def test_make_question_english_level1_idx1():
    q = make_question("english", 1, 1)
    assert q["id"] == "english-1-1"
    assert q["correct_answer"] == "いぬ"
    assert q["question_text"] == '"Dog" の意味はどれ？'
    assert len(q["options"]) == 4
    assert "いぬ" in q["options"]
    assert "いぬ" in q["hint"]


def test_make_question_english_level2_idx1():
    """レベル2の先頭は語彙インデックス5（Run）。"""
    q = make_question("english", 2, 1)
    assert q["id"] == "english-2-1"
    assert q["correct_answer"] == "走る"
    assert "Run" in q["question_text"]


def test_make_question_english_cycles_vocab():
    """レベル11では語彙が周回する。"""
    q11 = make_question("english", 11, 1)
    q1 = make_question("english", 1, 1)
    assert q11["question_text"] == q1["question_text"]
    assert q11["correct_answer"] == q1["correct_answer"]


def test_make_question_non_math_uses_english_vocab():
    """math 以外は従来どおり英語動的（教科名は小文字化）。"""
    q = make_question("English", 1, 2)
    assert q["id"] == "english-1-2"
    assert q["correct_answer"] == "ねこ"
