print("✅ questions.py が読み込まれました")
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

@router.get("", response_model=list[dict])
def get_questions(
    level: int = Query(..., description="取得するレベル"),
    subject: str = Query(..., description="教科 (例: english, math)")
):
    print(f"✅ get_questions 呼び出し: level={level}, subject={subject}")

    try:
        # モックデータを返す
        sample_questions = [
            {
                "id": 1,
                "subject": subject,
                "level": level,
                "question_text": "2 + 2 = ?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "4",
                "hint": "2と2を足してみて",
                "image_url": None,
                "audio_url": None
            },
            {
                "id": 2,
                "subject": subject,
                "level": level,
                "question_text": "5 - 3 = ?",
                "options": ["1", "2", "3", "4"],
                "correct_answer": "2",
                "hint": "5から3を引いてみて",
                "image_url": None,
                "audio_url": None
            }
        ]
        print(f"✅ モックデータ返却: {len(sample_questions)} 件")
        return sample_questions
    except Exception as e:
        print("❌ エラー:", e)
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")