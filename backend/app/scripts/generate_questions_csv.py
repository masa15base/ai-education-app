import pandas as pd
import json
import os

data = []

# 英語50問
english_words = [
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
    ("Computer", "コンピュータ", ["コンピュータ", "本", "テレビ"], "Computer は コンピュータ のことだよ。"),
    ("Phone", "電話", ["電話", "時計", "コンピュータ"], "Phone は 電話 のことだよ。"),
    ("Watch", "時計", ["時計", "電話", "コンピュータ"], "Watch は 時計 のことだよ。"),
    ("Bike", "自転車", ["自転車", "車", "バス"], "Bike は 自転車 のことだよ。"),
    ("Bus", "バス", ["バス", "電車", "飛行機"], "Bus は バス のことだよ。"),
    ("Train", "電車", ["電車", "バス", "飛行機"], "Train は 電車 のことだよ。"),
    ("Plane", "飛行機", ["飛行機", "船", "バス"], "Plane は 飛行機 のことだよ。"),
    ("Ship", "船", ["船", "飛行機", "電車"], "Ship は 船 のことだよ。"),
    ("River", "川", ["川", "山", "海"], "River は 川 のことだよ。"),
]

# レベル別に5問割り当て
for level in range(1, 11):
    for idx in range(5):
        word, correct, options, hint = english_words[(level - 1) * 5 + idx]
        data.append({
            "id": f"eng-{level}-{idx+1:03d}",
            "subject": "english",
            "level": level,
            "question_text": f"\"{word}\" の意味はどれ？",
            "options": json.dumps(options, ensure_ascii=False),
            "correct_answer": correct,
            "hint": hint,
            "image_url": None,
            "audio_url": None,
        })

# 算数問題
for level in range(1, 11):
    for idx in range(5):
        a = level * 2 + idx
        b = idx + 1
        if level <= 3:
            question_text = f"{a} + {b} は？"
            answer = str(a + b)
            options = [answer, str(a+b+1), str(a+b-1)]
        elif level <= 6:
            question_text = f"{a} × {b} は？"
            answer = str(a * b)
            options = [answer, str(a*b+1), str(a*b-1)]
        else:
            a = (a + 2) * b
            question_text = f"{a} ÷ {b} は？"
            answer = str(a // b)
            options = [answer, str(int(answer)+1), str(int(answer)-1)]
        
        data.append({
            "id": f"math-{level}-{idx+1:03d}",
            "subject": "math",
            "level": level,
            "question_text": question_text,
            "options": json.dumps(options, ensure_ascii=False),
            "correct_answer": answer,
            "hint": f"{question_text} を考えてごらん。",
            "image_url": None,
            "audio_url": None,
        })

# CSV出力
df_new = pd.DataFrame(data)
output_path = os.path.join(os.path.dirname(__file__), "../data/questions_level_10_final.csv")
df_new.to_csv(output_path, index=False)
print(f"✅ 100問のCSVを生成しました: {output_path}")