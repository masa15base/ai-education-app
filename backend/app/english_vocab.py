"""動的英語クイズ用の語彙（generate_questions_csv と同じ並び・周回ルール）。"""
from __future__ import annotations

from typing import Final

from .quiz_options import four_string_options

# (英単語, 日本語の正解, 3択の選択肢（正解を含む）, ヒント)
ENGLISH_VOCAB: Final[list[tuple[str, str, list[str], str]]] = [
    ("Dog", "いぬ", ["いぬ", "ねこ", "りんご"], "Dog は いぬ のことだよ。"),
    ("Cat", "ねこ", ["ねこ", "いぬ", "さかな"], "Cat は ねこ のことだよ。"),
    ("Apple", "りんご", ["りんご", "ばなな", "みかん"], "Apple は りんご のことだよ。"),
    ("Book", "本", ["本", "ペン", "ノート"], "Book は 本 のことだよ。"),
    ("Car", "車", ["車", "自転車", "バス"], "Car は 車 のことだよ。"),
    ("Run", "走る", ["走る", "食べる", "寝る"], "Run は 走る のことだよ。"),
    ("Swim", "泳ぐ", ["泳ぐ", "飛ぶ", "歩く"], "Swim は 泳ぐ のことだよ。"),
    ("Blue", "青", ["青", "赤", "緑"], "Blue は 青 のことだよ。"),
    ("Happy", "幸せ", ["幸せ", "悲しい", "怒っている"], "Happy は 幸せ のことだよ。"),
    ("School", "学校", ["学校", "病院", "図書館"], "School は 学校 のことだよ。"),
    ("Teacher", "先生", ["先生", "生徒", "医者"], "Teacher は 先生 のことだよ。"),
    ("Milk", "牛乳", ["牛乳", "水", "ジュース"], "Milk は 牛乳 のことだよ。"),
    ("Big", "大きい", ["大きい", "小さい", "速い"], "Big は 大きい のことだよ。"),
    ("Small", "小さい", ["小さい", "大きい", "高い"], "Small は 小さい のことだよ。"),
    ("Chair", "いす", ["いす", "机", "ベッド"], "Chair は いす のことだよ。"),
    ("Table", "机", ["机", "椅子", "棚"], "Table は 机 のことだよ。"),
    ("Window", "窓", ["窓", "ドア", "壁"], "Window は 窓 のことだよ。"),
    ("House", "家", ["家", "学校", "病院"], "House は 家 のことだよ。"),
    ("Sun", "太陽", ["太陽", "月", "星"], "Sun は 太陽 のことだよ。"),
    ("Moon", "月", ["月", "太陽", "地球"], "Moon は 月 のことだよ。"),
    ("Star", "星", ["星", "雲", "山"], "Star は 星 のことだよ。"),
    ("Tree", "木", ["木", "花", "草"], "Tree は 木 のことだよ。"),
    ("Flower", "花", ["花", "木", "草"], "Flower は 花 のことだよ。"),
    ("Bird", "とり", ["とり", "ねこ", "いぬ"], "Bird は とり のことだよ。"),
    ("Fish", "さかな", ["さかな", "いぬ", "ねこ"], "Fish は さかな のことだよ。"),
    ("Ball", "ボール", ["ボール", "本", "ペン"], "Ball は ボール のことだよ。"),
    ("Pen", "ペン", ["ペン", "ノート", "本"], "Pen は ペン のことだよ。"),
    ("Desk", "机", ["机", "椅子", "棚"], "Desk は 机 のことだよ。"),
    ("Friend", "友達", ["友達", "先生", "家族"], "Friend は 友達 のことだよ。"),
    ("Family", "家族", ["家族", "友達", "先生"], "Family は 家族 のことだよ。"),
    ("Mother", "母", ["母", "父", "兄"], "Mother は 母 のことだよ。"),
    ("Father", "父", ["父", "母", "姉"], "Father は 父 のことだよ。"),
    ("Brother", "兄", ["兄", "弟", "姉"], "Brother は 兄 のことだよ。"),
    ("Sister", "姉", ["姉", "妹", "兄"], "Sister は 姉 のことだよ。"),
    ("Food", "食べ物", ["食べ物", "飲み物", "お菓子"], "Food は 食べ物 のことだよ。"),
    ("Drink", "飲み物", ["飲み物", "食べ物", "水"], "Drink は 飲み物 のことだよ。"),
    ("Water", "水", ["水", "牛乳", "ジュース"], "Water は 水 のことだよ。"),
    ("Juice", "ジュース", ["ジュース", "水", "牛乳"], "Juice は ジュース のことだよ。"),
    ("Music", "音楽", ["音楽", "映画", "本"], "Music は 音楽 のことだよ。"),
    ("Movie", "映画", ["映画", "音楽", "本"], "Movie は 映画 のことだよ。"),
    ("Game", "ゲーム", ["ゲーム", "本", "運動"], "Game は ゲーム のことだよ。"),
    (
        "Computer",
        "コンピュータ",
        ["コンピュータ", "本", "テレビ"],
        "Computer は コンピュータ のことだよ。",
    ),
    ("Phone", "電話", ["電話", "時計", "コンピュータ"], "Phone は 電話 のことだよ。"),
    ("Watch", "時計", ["時計", "電話", "コンピュータ"], "Watch は 時計 のことだよ。"),
    ("Bike", "自転車", ["自転車", "車", "バス"], "Bike は 自転車 のことだよ。"),
    ("Bus", "バス", ["バス", "電車", "飛行機"], "Bus は バス のことだよ。"),
    ("Train", "電車", ["電車", "バス", "飛行機"], "Train は 電車 のことだよ。"),
    ("Plane", "飛行機", ["飛行機", "船", "バス"], "Plane は 飛行機 のことだよ。"),
    ("Ship", "船", ["船", "飛行機", "電車"], "Ship は 船 のことだよ。"),
    ("River", "川", ["川", "山", "海"], "River は 川 のことだよ。"),
]


def english_vocab_row_index(level: int, idx: int) -> int:
    """レベル・問題番号（いずれも 1 始まり）から語彙行。DB CSV と同じ (level-1)*5+(idx-1) を周回。"""
    lv = max(1, int(level))
    j = max(1, int(idx))
    return ((lv - 1) * 5 + (j - 1)) % len(ENGLISH_VOCAB)


def _extra_japanese_distractors(jp_correct: str, skip_row: int) -> list[str]:
    out: list[str] = []
    for i, row in enumerate(ENGLISH_VOCAB):
        if i == skip_row:
            continue
        jp = row[1]
        if jp != jp_correct and jp not in out:
            out.append(jp)
        if len(out) >= 8:
            break
    return out


def english_question_parts(level: int, idx: int) -> tuple[str, str, list[str], str, str]:
    """
    戻り値: (英単語, 正解日本語, 4択（日本語）, ヒント, 問題文)
    """
    pos = english_vocab_row_index(level, idx)
    word_en, jp_correct, three_opts, hint = ENGLISH_VOCAB[pos]
    seed = f"english-{level}-{idx}"
    options = four_string_options(
        jp_correct,
        list(three_opts) + _extra_japanese_distractors(jp_correct, pos),
        seed,
    )
    text = f'"{word_en}" の意味はどれ？'
    return word_en, jp_correct, options, hint, text
