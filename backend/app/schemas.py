from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class QuestionSchema(BaseModel):
    id: str
    subject: Optional[str] = None
    level: Optional[int] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: str
    hint: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerRequest(BaseModel):
    question_id: str
    selected_answer: str

class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    hint: Optional[str] = None

class AnswerHistoryRequest(BaseModel):
    user_id: str
    question_id: str
    selected_answer: str

class AnswerHistoryResponse(BaseModel):
    id: int
    user_id: str
    question_id: str
    selected_answer: str
    correct: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerStatsResponse(BaseModel):
    user_id: str
    total_answers: int
    correct_answers: int
    accuracy: float
    streak: int


# UserProgressResponse schema
class UserProgressResponse(BaseModel):
    user_id: str
    subject: str
    current_level: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def character_level_from_xp(experience: int) -> int:
    return max(1, min(99, 1 + experience // 100))


class CharacterUpsert(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    image_url: Optional[str] = None
    experience: int = Field(default=0, ge=0, le=1_000_000)
    hero_preview_url: Optional[str] = Field(default=None, max_length=2_000_000)
    next_stage_preview_url: Optional[str] = Field(default=None, max_length=2_000_000)
    character_dna: Optional[dict] = None
    image_understanding: Optional[dict] = None


class CharacterOut(BaseModel):
    display_name: str
    image_url: Optional[str] = None
    experience: int
    level: int


class SyncStepsXpIn(BaseModel):
    goal_steps: int = Field(default=5000, ge=1000, le=100_000)


class SyncStepsXpOut(BaseModel):
    xp_gained: int
    detail: List[str]
    display_name: str
    image_url: Optional[str] = None
    experience: int
    level: int


class StatsTimelineItem(BaseModel):
    created_at: str
    subject: str
    level: int
    score: int
    kind: str = "quiz_session"


class StatsDailyActivity(BaseModel):
    date: str
    quiz_sessions: int = 0
    average_score: Optional[float] = None


class StatsSubjectBreakdown(BaseModel):
    subject: str
    sessions_week: int = 0
    average_score_week: Optional[float] = None
    answers_count_week: int = 0
    answer_accuracy_week: Optional[float] = None


class StatsCharacterBrief(BaseModel):
    display_name: str
    experience: int
    level: int
    image_url: Optional[str] = None


class StatsSummary(BaseModel):
    database_configured: bool
    window_days: int = 7
    quiz_sessions_week: int = 0
    quiz_sessions_total: int = 0
    average_score_week: float = 0.0
    answers_count_week: int = 0
    answer_accuracy_week: Optional[float] = None
    character: Optional[StatsCharacterBrief] = None
    timeline: List[StatsTimelineItem] = []
    weekly_activity: List[StatsDailyActivity] = []
    subject_breakdown: List[StatsSubjectBreakdown] = []
    steps_goal: int = 5000
    steps_today: Optional[int] = None
    steps_ymd: Optional[str] = None
    steps_source: Optional[str] = None


class StepsTodayOut(BaseModel):
    """GET /api/steps/today — 未ログインでも 200（クラウド値なし）。"""

    authenticated: bool
    today_ymd: str
    goal_steps: int = 5000
    steps: Optional[int] = None
    source: str = "none"  # none | memory | database
    hint: Optional[str] = None


class StepsPutIn(BaseModel):
    steps: int = Field(ge=0, le=999_999)


class StepsPutOut(BaseModel):
    today_ymd: str
    steps: int
    source: str


class StepsWeekDayOut(BaseModel):
    date: str
    steps: int = 0
    goal_reached: bool = False


class StepsWeekOut(BaseModel):
    authenticated: bool
    today_ymd: str
    goal_steps: int = 5000
    source: str = "none"
    days: List[StepsWeekDayOut] = []


class CharacterNextEvolution(BaseModel):
    next_stage: Optional[str] = None
    current_stage: Optional[str] = None
    complete: bool = False


class CharacterStatusOut(BaseModel):
    character_id: str
    display_name: str = "みーちゃん"
    image_url: Optional[str] = None
    stage: str = "egg"
    stage_label: str = "たまご"
    level: int = 1
    exp: int = 0
    character_exp: int = 0
    exp_in_level: int = 0
    exp_to_next: int = 100
    quiz_correct_count: int = 0
    quiz_total_count: int = 0
    quiz_streak_days: int = 0
    total_steps: int = 0
    daily_steps: int = 0
    login_streak_days: int = 0
    quiz_today: bool = False
    mood: str = "normal"
    home_action: str = "idle"
    message: str = ""
    next_evolution: dict = Field(default_factory=dict)
    current_stage_image: Optional[str] = None
    hero_preview_url: Optional[str] = None
    next_stage_preview_url: Optional[str] = None
    final_hero_preview: Optional[str] = None


class CharacterActivityIn(BaseModel):
    user_id: Optional[str] = Field(default=None, max_length=128)
    activity_type: str = Field(max_length=40)
    is_correct: Optional[bool] = None
    steps: int = Field(default=0, ge=0)
    correct_count: Optional[int] = Field(default=None, ge=0)
    total_count: Optional[int] = Field(default=None, ge=0)
    goal_reached: Optional[bool] = None
    total_steps: Optional[int] = Field(default=None, ge=0)


class CharacterActivityOut(BaseModel):
    exp_gained: int = 0
    stage: str = "egg"
    evolved: bool = False
    previous_stage: Optional[str] = None
    character_exp: int = 0
    status: Optional[CharacterStatusOut] = None