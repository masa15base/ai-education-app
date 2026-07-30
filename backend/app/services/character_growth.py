"""
キャラクター成長・進化・Home表示状態（ルールベース）。
DB 入出力は growth_stats_store 経由で stats dict を扱う。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

STAGES_ORDER: tuple[str, ...] = ("egg", "baby", "child", "student", "hero")

# 各 stage へ進化するために満たす累計条件（egg は初期）
EVOLUTION_TO: dict[str, dict[str, Any]] = {
    "baby": {"has_character_image": True},
    "child": {"character_exp": 100, "quiz_correct_count": 5},
    "student": {
        "character_exp": 300,
        "quiz_correct_count": 20,
        "total_steps": 10_000,
    },
    "hero": {
        "character_exp": 700,
        "quiz_correct_count": 50,
        "quiz_streak_days": 7,
        "total_steps": 50_000,
    },
}

STAGE_LABELS_JA: dict[str, str] = {
    "egg": "たまご",
    "baby": "ベビー",
    "child": "こども",
    "student": "がくせい",
    "hero": "ヒーロー",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_ymd() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def default_stats() -> dict[str, Any]:
    return {
        "stage": "egg",
        "quiz_correct_count": 0,
        "quiz_total_count": 0,
        "quiz_streak_days": 0,
        "total_steps": 0,
        "login_streak_days": 0,
        "last_quiz_ymd": None,
        "last_login_ymd": None,
        "has_character_image": False,
        "excited_until": None,
        "hero_preview_url": None,
        "next_stage_preview_url": None,
    }


def calculate_exp(activity: dict[str, Any]) -> int:
    """クイズ・歩数・ログイン情報から獲得 EXP を計算する。"""
    t = (activity.get("activity_type") or "").strip()
    exp = 0

    if t == "quiz_answer":
        exp += 5
        if activity.get("is_correct"):
            exp += 10
    elif t == "quiz_complete":
        # progress_service.compute_quiz_session_xp_raw と同一式（一本化）
        from ..growth_service import compute_quiz_session_xp_raw

        total = max(1, int(activity.get("total_count") or 0))
        correct = int(activity.get("correct_count") or 0)
        level = int(activity.get("level") or 1)
        exp = compute_quiz_session_xp_raw(correct, total, level)
    elif t == "login":
        exp += 5
    elif t == "steps":
        steps = int(activity.get("steps") or 0)
        exp += (steps // 1000) * 10
        if activity.get("goal_reached"):
            exp += 30
    elif t == "character_born":
        exp += 20

    return max(0, exp)


def _stats_with_exp(stats: dict[str, Any], character_exp: int) -> dict[str, Any]:
    s = {**default_stats(), **stats}
    s["character_exp"] = int(character_exp)
    return s


def _meets(requirements: dict[str, Any], stats: dict[str, Any]) -> bool:
    for key, need in requirements.items():
        if key == "has_character_image":
            if not stats.get("has_character_image"):
                return False
            continue
        if int(stats.get(key) or 0) < int(need):
            return False
    return True


def determine_character_stage(stats: dict[str, Any], character_exp: int = 0) -> str:
    """累計ステータスから現在の進化ステージを判定する。"""
    s = _stats_with_exp(stats, character_exp)
    stage = "egg"
    for name in STAGES_ORDER[1:]:
        req = EVOLUTION_TO.get(name, {})
        if _meets(req, s):
            stage = name
        else:
            break
    return stage


def get_next_evolution_requirement(
    stats: dict[str, Any], character_exp: int = 0
) -> dict[str, Any]:
    """次の進化に必要な条件と不足分を返す。"""
    s = _stats_with_exp(stats, character_exp)
    current = determine_character_stage(s, character_exp)
    try:
        idx = STAGES_ORDER.index(current)
    except ValueError:
        idx = 0
    if idx >= len(STAGES_ORDER) - 1:
        return {
            "next_stage": None,
            "current_stage": current,
            "complete": True,
        }

    nxt = STAGES_ORDER[idx + 1]
    req = EVOLUTION_TO[nxt]
    out: dict[str, Any] = {
        "next_stage": nxt,
        "next_stage_label": STAGE_LABELS_JA.get(nxt, nxt),
        "current_stage": current,
        "current_stage_label": STAGE_LABELS_JA.get(current, current),
        "complete": False,
        "requirements": [],
    }
    for key, need in req.items():
        if key == "has_character_image":
            have_img = bool(s.get("has_character_image"))
            remaining = 0 if have_img else 1
            out[f"required_{key}"] = True
            out[f"remaining_{key}"] = remaining
            out[f"current_{key}"] = have_img
            out[f"progress_{key}"] = 1.0 if have_img else 0.0
            out["requirements"].append(
                {
                    "key": key,
                    "label": "キャラ画像",
                    "required": True,
                    "current": have_img,
                    "remaining": remaining,
                    "progress": 1.0 if have_img else 0.0,
                    "done": have_img,
                }
            )
            continue
        have = int(s.get(key) or 0) if key != "character_exp" else int(character_exp)
        need_i = int(need)
        remaining = max(0, need_i - have)
        progress = min(1.0, have / need_i) if need_i else 1.0
        out[f"required_{key}"] = need_i
        out[f"remaining_{key}"] = remaining
        out[f"current_{key}"] = have
        out[f"progress_{key}"] = round(progress, 3)
        label_map = {
            "character_exp": "経験値",
            "quiz_correct_count": "クイズ正解",
            "total_steps": "累計歩数",
            "quiz_streak_days": "クイズ連続日数",
        }
        out["requirements"].append(
            {
                "key": key,
                "label": label_map.get(key, key),
                "required": need_i,
                "current": have,
                "remaining": remaining,
                "progress": round(progress, 3),
                "done": remaining == 0,
            }
        )
    if "remaining_character_exp" in out:
        out["remaining_exp"] = out["remaining_character_exp"]
        out["required_exp"] = out.get("required_character_exp")
        out["current_exp"] = out.get("current_character_exp")
        out["progress_exp"] = out.get("progress_character_exp")
    return out


def _is_excited(stats: dict[str, Any]) -> bool:
    raw = stats.get("excited_until")
    if not raw:
        return False
    if isinstance(raw, datetime):
        return raw > _utc_now()
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > _utc_now()
    except Exception:
        return False


def determine_mood(
    stats: dict[str, Any],
    *,
    character_exp: int = 0,
    daily_steps: int = 0,
    steps_goal: int = 5000,
    quiz_today: bool = False,
    last_quiz_score: int | None = None,
) -> str:
    s = _stats_with_exp(stats, character_exp)
    stage = determine_character_stage(s, character_exp)

    if _is_excited(s):
        return "excited"
    if stage == "egg":
        return "normal"
    if quiz_today and last_quiz_score is not None and last_quiz_score >= 80:
        return "happy"
    if quiz_today or s.get("quiz_streak_days", 0) >= 3:
        return "happy"
    if daily_steps >= steps_goal:
        return "happy"
    if not quiz_today and daily_steps < 1000:
        return "sleepy"
    return "normal"


def determine_home_action(
    stats: dict[str, Any],
    mood: str,
    *,
    character_exp: int = 0,
    quiz_today: bool = False,
    daily_steps: int = 0,
    steps_goal: int = 5000,
) -> str:
    s = _stats_with_exp(stats, character_exp)
    stage = determine_character_stage(s, character_exp)

    if mood == "excited" or mood == "happy" and quiz_today:
        return "celebrating"
    if mood == "sleepy":
        return "sleeping"
    if quiz_today:
        return "studying"
    if daily_steps >= steps_goal * 0.5:
        return "walking"
    if stage == "egg":
        return "cheering"
    if not quiz_today:
        return "cheering"
    return "idle"


def pick_message(
    stage: str,
    mood: str,
    home_action: str,
    display_name: str,
) -> str:
    name = display_name or "みーちゃん"
    if stage == "egg":
        return "きみの絵から、もうすぐ相棒が生まれるよ！"
    if mood == "excited" or home_action == "celebrating":
        return f"やったね！{name}はうれしいよ！"
    if mood == "sleepy":
        return "今日はまだクイズに挑戦していないみたい。少しずつやってみよう！"
    if home_action == "cheering":
        return "今日もクイズがんばろう！"
    if home_action == "walking":
        return "いっぱい歩いたね！すごい！"
    if home_action == "studying":
        return "クイズおつかれさま！つづけて学ぼう！"
    if stage == "baby":
        return "こんにちは！いっしょにまなぼう！"
    if stage == "child":
        return "いい感じ！もっと正解すると進化できそう！"
    if stage == "student":
        return "学びの力がたまってきたよ！あと少しでヒーローになれそう！"
    if stage == "hero":
        return "すごい！きみの努力でここまで成長したよ！"
    return "今日も一緒にチャレンジしよう！"


def build_character_status(
    stats: dict[str, Any],
    *,
    character_id: str,
    display_name: str,
    image_url: str | None,
    character_exp: int,
    daily_steps: int = 0,
    steps_goal: int = 5000,
    quiz_today: bool = False,
    last_quiz_score: int | None = None,
    hero_preview_url: str | None = None,
    next_stage_preview_url: str | None = None,
) -> dict[str, Any]:
    """Home 画面表示用のキャラクター状態を返す。"""
    s = _stats_with_exp(stats, character_exp)
    stage = determine_character_stage(s, character_exp)
    level = max(1, min(99, 1 + character_exp // 100))
    xp_in_level = character_exp % 100
    exp_to_next_level = 100 - xp_in_level

    next_evo = get_next_evolution_requirement(s, character_exp)
    mood = determine_mood(
        s,
        character_exp=character_exp,
        daily_steps=daily_steps,
        steps_goal=steps_goal,
        quiz_today=quiz_today,
        last_quiz_score=last_quiz_score,
    )
    home_action = determine_home_action(
        s,
        mood,
        character_exp=character_exp,
        quiz_today=quiz_today,
        daily_steps=daily_steps,
        steps_goal=steps_goal,
    )
    message = pick_message(stage, mood, home_action, display_name)

    return {
        "character_id": character_id,
        "display_name": display_name,
        "image_url": image_url,
        "current_stage_image": image_url,
        "hero_preview_url": hero_preview_url,
        "next_stage_preview_url": next_stage_preview_url,
        "final_hero_preview": hero_preview_url,
        "stage": stage,
        "stage_label": STAGE_LABELS_JA.get(stage, stage),
        "level": level,
        "exp": character_exp,
        "character_exp": character_exp,
        "exp_in_level": xp_in_level,
        "exp_to_next": exp_to_next_level,
        "quiz_correct_count": int(s.get("quiz_correct_count") or 0),
        "quiz_total_count": int(s.get("quiz_total_count") or 0),
        "quiz_streak_days": int(s.get("quiz_streak_days") or 0),
        "total_steps": int(s.get("total_steps") or 0),
        "daily_steps": daily_steps,
        "login_streak_days": int(s.get("login_streak_days") or 0),
        "quiz_today": quiz_today,
        "mood": mood,
        "home_action": home_action,
        "message": message,
        "next_evolution": next_evo,
    }
