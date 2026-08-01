"""シード用 CSV 生成（算数・英語 × Lv1-10 × 各5問 = 100問、すべて4択）。"""
from __future__ import annotations

import csv
import json
import os
import sys

# backend を path に
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.quiz_options import four_string_options  # noqa: E402

english_words = [
    ("Dog", "いぬ", ["ねこ", "りんご", "くるま"]),
    ("Cat", "ねこ", ["いぬ", "さかな", "とり"]),
    ("Apple", "りんご", ["ばなな", "みかん", "ぶどう"]),
    ("Book", "本", ["ペン", "ノート", "カバン"]),
    ("Car", "車", ["自転車", "バス", "電車"]),
    ("Run", "走る", ["食べる", "寝る", "泳ぐ"]),
    ("Swim", "泳ぐ", ["飛ぶ", "歩く", "走る"]),
    ("Blue", "青", ["赤", "緑", "きいろ"]),
    ("Happy", "うれしい", ["かなしい", "おこる", "ねむい"]),
    ("School", "学校", ["びょういん", "としょかん", "こうえん"]),
    ("Teacher", "先生", ["せいと", "いしゃ", "かぞく"]),
    ("Milk", "ぎゅうにゅう", ["みず", "ジュース", "おちゃ"]),
    ("Big", "おおきい", ["ちいさい", "はやい", "おそい"]),
    ("Small", "ちいさい", ["おおきい", "たかい", "ひくい"]),
    ("Chair", "いす", ["つくえ", "ベッド", "ほんだな"]),
    ("Table", "つくえ", ["いす", "ベッド", "まど"]),
    ("Window", "まど", ["ドア", "かべ", "ゆか"]),
    ("House", "いえ", ["がっこう", "びょういん", "みせ"]),
    ("Sun", "たいよう", ["つき", "ほし", "くも"]),
    ("Moon", "つき", ["たいよう", "ちきゅう", "ほし"]),
    ("Star", "ほし", ["くも", "やま", "うみ"]),
    ("Tree", "き", ["はな", "くさ", "いし"]),
    ("Flower", "はな", ["き", "くさ", "はっぱ"]),
    ("Bird", "とり", ["ねこ", "いぬ", "さかな"]),
    ("Fish", "さかな", ["いぬ", "ねこ", "とり"]),
    ("Ball", "ボール", ["ほん", "ペン", "くつ"]),
    ("Pen", "ペン", ["ノート", "ほん", "けしゴム"]),
    ("Desk", "つくえ", ["いす", "たな", "まど"]),
    ("Friend", "ともだち", ["せんせい", "かぞく", "となり"]),
    ("Family", "かぞく", ["ともだち", "せんせい", "がっこう"]),
    ("Mother", "おかあさん", ["おとうさん", "おにいさん", "おねえさん"]),
    ("Father", "おとうさん", ["おかあさん", "おねえさん", "おとうと"]),
    ("Brother", "あに", ["おとうと", "あね", "いもうと"]),
    ("Sister", "あね", ["いもうと", "あに", "おとうと"]),
    ("Food", "たべもの", ["のみもの", "おかし", "みず"]),
    ("Drink", "のみもの", ["たべもの", "みず", "ごはん"]),
    ("Water", "みず", ["ぎゅうにゅう", "ジュース", "おちゃ"]),
    ("Juice", "ジュース", ["みず", "ぎゅうにゅう", "おちゃ"]),
    ("Music", "おんがく", ["えいが", "ほん", "ゲーム"]),
    ("Movie", "えいが", ["おんがく", "ほん", "テレビ"]),
    ("Game", "ゲーム", ["ほん", "うんどう", "おんがく"]),
    ("Computer", "コンピュータ", ["ほん", "テレビ", "でんわ"]),
    ("Phone", "でんわ", ["とけい", "コンピュータ", "テレビ"]),
    ("Watch", "とけい", ["でんわ", "コンピュータ", "めがね"]),
    ("Bike", "じてんしゃ", ["くるま", "バス", "でんしゃ"]),
    ("Bus", "バス", ["でんしゃ", "ひこうき", "ふね"]),
    ("Train", "でんしゃ", ["バス", "ひこうき", "くるま"]),
    ("Plane", "ひこうき", ["ふね", "バス", "でんしゃ"]),
    ("Ship", "ふね", ["ひこうき", "でんしゃ", "バス"]),
    ("River", "かわ", ["やま", "うみ", "いけ"]),
]

rows: list[dict] = []

for level in range(1, 11):
    for idx in range(5):
        word, correct, distractors = english_words[(level - 1) * 5 + idx]
        qid = f"eng-{level}-{idx + 1:03d}"
        options = four_string_options(correct, distractors, seed=qid)
        rows.append(
            {
                "id": qid,
                "subject": "english",
                "level": level,
                "question_text": f'"{word}" の意味はどれ？',
                "options": json.dumps(options, ensure_ascii=False),
                "correct_answer": correct,
                "hint": f"{word} は {correct} のことだよ。",
                "image_url": "",
                "audio_url": "",
            }
        )

def _math_distractors(answer: int) -> list[str]:
    """正解と重複しない誤答を3つ作る。"""
    seen = {str(answer)}
    out: list[str] = []
    for delta in (1, -1, 2, -2, 3, -3, 5, 10, 4, -5):
        s = str(answer + delta)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 3:
            break
    return out


for level in range(1, 11):
    for idx in range(5):
        a = level * 2 + idx
        b = idx + 1
        if level <= 3:
            question_text = f"{a} + {b} は？"
            answer_n = a + b
        elif level <= 6:
            question_text = f"{a} × {b} は？"
            answer_n = a * b
        else:
            a = (a + 2) * b
            question_text = f"{a} ÷ {b} は？"
            answer_n = a // b
        answer = str(answer_n)
        distractors = _math_distractors(answer_n)
        qid = f"math-{level}-{idx + 1:03d}"
        options = four_string_options(answer, distractors, seed=qid)
        rows.append(
            {
                "id": qid,
                "subject": "math",
                "level": level,
                "question_text": question_text,
                "options": json.dumps(options, ensure_ascii=False),
                "correct_answer": answer,
                "hint": f"{question_text} を考えてごらん。",
                "image_url": "",
                "audio_url": "",
            }
        )

out = os.path.join(os.path.dirname(__file__), "../data/questions_level_10_final.csv")
fieldnames = [
    "id",
    "subject",
    "level",
    "question_text",
    "options",
    "correct_answer",
    "hint",
    "image_url",
    "audio_url",
]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {len(rows)} questions → {out}")
