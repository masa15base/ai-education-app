from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.mysql import JSON
from .db import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(String(50), primary_key=True, index=True)
    subject = Column(String(20), nullable=True)
    level = Column(Integer, nullable=True)
    question_text = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(50), nullable=True)
    hint = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    audio_url = Column(String(255), nullable=True)

class AnswerHistory(Base):
    __tablename__ = "answer_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False)
    question_id = Column(String(50), nullable=False)
    selected_answer = Column(String(100), nullable=False)
    correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False)
    subject = Column(String(50), nullable=False)
    current_level = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ProgressEntry(Base):
    """学習履歴（ /api/progress の1行分 ）。"""

    __tablename__ = "progress_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    subject = Column(String(50), nullable=False)
    level = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    gained_xp = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())


class UserCharacter(Base):
    """子ども向けアクティブキャラ（Firebase uid 1人1行）。"""

    __tablename__ = "user_characters"

    user_id = Column(String(128), primary_key=True)
    display_name = Column(String(100), nullable=False)
    image_url = Column(Text, nullable=True)
    experience = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # 歩数由来 XP の冪等付与（JST 日付で daily_steps と揃える）
    steps_growth_ymd = Column(String(10), nullable=True)
    steps_xp_paid_tier = Column(Integer, nullable=False, default=0)
    steps_xp_goal_bonus = Column(Boolean, nullable=False, default=False)


class UserCharacterGrowthStats(Base):
    """学習・歩数・継続に基づく進化ステータス（1ユーザー1行）。"""

    __tablename__ = "user_character_growth_stats"

    user_id = Column(String(128), primary_key=True)
    stage = Column(String(20), nullable=False, default="egg")
    quiz_correct_count = Column(Integer, nullable=False, default=0)
    quiz_total_count = Column(Integer, nullable=False, default=0)
    quiz_streak_days = Column(Integer, nullable=False, default=0)
    total_steps = Column(Integer, nullable=False, default=0)
    login_streak_days = Column(Integer, nullable=False, default=0)
    last_quiz_ymd = Column(String(10), nullable=True)
    last_login_ymd = Column(String(10), nullable=True)
    has_character_image = Column(Boolean, nullable=False, default=False)
    excited_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DailyStep(Base):
    """ユーザー×暦日ごとの歩数（手入力・デモ同期用。ウェア連携は将来差し替え）。"""

    __tablename__ = "daily_steps"
    __table_args__ = (
        UniqueConstraint("user_id", "step_date", name="uq_daily_steps_user_day"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    step_date = Column(String(10), nullable=False)  # YYYY-MM-DD（サーバー日付基準）
    steps = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class QuizAnswerLog(Base):
    """動的クイズの各解答ログ（DBに questions 行が無くても記録可能）。"""

    __tablename__ = "quiz_answer_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    subject = Column(String(50), nullable=False)
    level = Column(Integer, nullable=False)
    question_index = Column(Integer, nullable=False)
    question_id = Column(String(120), nullable=False)
    selected_answer = Column(String(100), nullable=False)
    correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
