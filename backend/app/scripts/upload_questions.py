import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import json

# 環境変数読み込み
load_dotenv()
DATABASE_URL = os.getenv("JAWSDB_URL")

if not DATABASE_URL:
    raise ValueError("❌ 環境変数 JAWSDB_URL が設定されていません")

engine = create_engine(DATABASE_URL)

# CSVの読み込み
csv_path = os.path.join(os.path.dirname(__file__), "../data/questions_level_10_final.csv")
df = pd.read_csv(csv_path)

# NaN を None に変換
df = df.where(pd.notnull(df), None)

with engine.begin() as conn:
    # 既存データ削除
    print("⚠️ questions テーブルの既存データを削除します...")
    conn.execute(text("DELETE FROM questions"))

    # 新しいデータを挿入
    for _, row in df.iterrows():
        # optionsをJSON文字列に変換
        options_json = row["options"]
        if isinstance(options_json, str):
            try:
                options_json = json.dumps(eval(options_json))
            except:
                options_json = json.dumps([])
        elif isinstance(options_json, list):
            options_json = json.dumps(options_json)
        else:
            options_json = json.dumps([])

        conn.execute(text("""
            INSERT INTO questions (id, subject, level, question_text, options, correct_answer, hint, image_url, audio_url)
            VALUES (:id, :subject, :level, :question_text, :options, :correct_answer, :hint, :image_url, :audio_url)
        """), {
            "id": row["id"],
            "subject": row["subject"],
            "level": int(row["level"]),
            "question_text": row["question_text"],
            "options": options_json,
            "correct_answer": row["correct_answer"],
            "hint": row["hint"],
            "image_url": None if pd.isna(row["image_url"]) else row["image_url"],
            "audio_url": None if pd.isna(row["audio_url"]) else row["audio_url"],
        })

print("✅ レベル1〜10の100問をアップロードしました！（英語50問＋算数50問）")