from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..models import AnswerHistory
from ..models import UserProgress
from datetime import datetime

router = APIRouter()

@router.post("", response_model=schemas.AnswerResponse)
def check_answer(req: schemas.AnswerRequest, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.id == req.question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = (req.selected_answer == question.correct_answer)

    return {
        "correct": is_correct,
        "correct_answer": question.correct_answer,
        "hint": question.hint
    }

@router.post("/save", response_model=dict)
def save_answer(req: schemas.AnswerHistoryRequest, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.id == req.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = (req.selected_answer == question.correct_answer)

    # 解答を保存
    history = AnswerHistory(
        user_id=req.user_id,
        question_id=req.question_id,
        selected_answer=req.selected_answer,
        correct=is_correct
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    # レベル進行チェック
    level_questions = db.query(models.Question.id)\
                        .filter(models.Question.level == question.level,
                                models.Question.subject == question.subject)\
                        .all()

    answered_correct = db.query(models.AnswerHistory.question_id)\
                         .filter(models.AnswerHistory.user_id == req.user_id,
                                 models.AnswerHistory.correct == True,
                                 models.AnswerHistory.question_id.in_([q.id for q in level_questions]))\
                         .distinct()\
                         .count()

    next_level = None
    if answered_correct == len(level_questions):
        next_level = question.level + 1

        # user_progress を更新 or 新規作成
        progress = db.query(UserProgress)\
                     .filter(UserProgress.user_id == req.user_id,
                             UserProgress.subject == question.subject)\
                     .first()

        if progress:
            progress.current_level = next_level
            progress.updated_at = datetime.now()
        else:
            progress = UserProgress(
                user_id=req.user_id,
                subject=question.subject,
                current_level=next_level
            )
            db.add(progress)

        db.commit()

    return {
        "id": history.id,
        "user_id": history.user_id,
        "question_id": history.question_id,
        "selected_answer": history.selected_answer,
        "correct": history.correct,
        "timestamp": history.timestamp,
        "next_level": next_level
    }

@router.get("/history", response_model=list[schemas.AnswerHistoryResponse])
def get_answer_history(user_id: str, db: Session = Depends(get_db)):
    histories = db.query(models.AnswerHistory)\
                  .filter(models.AnswerHistory.user_id == user_id)\
                  .order_by(models.AnswerHistory.timestamp.desc())\
                  .all()
    return histories

@router.get("/stats", response_model=schemas.AnswerStatsResponse)
def get_answer_stats(user_id: str, db: Session = Depends(get_db)):
    histories = db.query(models.AnswerHistory)\
                  .filter(models.AnswerHistory.user_id == user_id)\
                  .order_by(models.AnswerHistory.timestamp.desc())\
                  .all()

    total = len(histories)
    if total == 0:
        return {
            "user_id": user_id,
            "total_answers": 0,
            "correct_answers": 0,
            "accuracy": 0.0,
            "streak": 0
        }

    correct_count = sum(1 for h in histories if h.correct)
    accuracy = round((correct_count / total) * 100, 1)

    # 連続正解数を計算
    streak = 0
    for h in histories:
        if h.correct:
            streak += 1
        else:
            break

    return {
        "user_id": user_id,
        "total_answers": total,
        "correct_answers": correct_count,
        "accuracy": accuracy,
        "streak": streak
    }


# User progress endpoint
from ..models import UserProgress

@router.get("/progress", response_model=schemas.UserProgressResponse)
def get_progress(user_id: str, subject: str, db: Session = Depends(get_db)):
    progress = db.query(UserProgress)\
                 .filter(UserProgress.user_id == user_id,
                         UserProgress.subject == subject)\
                 .first()

    if not progress:
        raise HTTPException(status_code=404, detail="No progress found")

    return progress