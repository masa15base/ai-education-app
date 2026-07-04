"""
まなとも固定キャラクター DNA。
Vision API は特徴 JSON の抽出のみ。設計・進化・描画ルールはここで制御する。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# --- Vision API が返す schema（このキーのみ） ---
VISION_RESULT_KEYS = (
    "face_shape",
    "hair_color",
    "hair_style",
    "bangs",
    "eye_shape",
    "eye_count",
    "mouth",
    "cheeks",
    "accent_color",
    "accessory",
    "mood",
    "signature_features",
)

FACE_SHAPES = frozenset({"round", "oval", "square", "unknown"})
HAIR_COLORS = frozenset({"black", "dark_navy", "brown", "blonde", "unknown"})
HAIR_STYLES = frozenset({"short_bob", "long", "twin_tail", "short", "unknown"})
BANGS = frozenset({"straight", "center", "side", "none", "unknown"})
EYE_SHAPES = frozenset({"large_round", "small_dot", "almond", "unknown"})
MOUTHS = frozenset({"smile", "neutral", "open_smile", "unknown"})
ACCENT_COLORS = frozenset({"mint_green", "pink", "blue", "yellow", "none"})
ACCESSORIES = frozenset({"star", "ribbon", "hat", "none"})
MOODS = frozenset({"cute", "cheerful", "calm", "energetic"})

# まなとも既定 DNA（不明時の補正先）
MANATOMO_DEFAULT_VISION: dict[str, Any] = {
    "face_shape": "round",
    "hair_color": "dark_navy",
    "hair_style": "short_bob",
    "bangs": "center",
    "eye_shape": "large_round",
    "eye_count": 2,
    "mouth": "smile",
    "cheeks": True,
    "accent_color": "mint_green",
    "accessory": "star",
    "mood": "cheerful",
    "signature_features": [
        "round face",
        "large round eyes",
        "short bob hair",
        "mint green star",
        "pink cheeks",
    ],
}

HAIR_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "black": (34, 34, 34),
    "dark_navy": (42, 48, 72),
    "brown": (90, 60, 40),
    "blonde": (220, 190, 120),
}

ACCENT_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "mint_green": (85, 221, 204),
    "pink": (255, 180, 170),
    "blue": (80, 140, 220),
    "yellow": (255, 210, 80),
    "none": (85, 221, 204),
}

SIGNATURE_FEATURES_JA: dict[str, str] = {
    "round face": "丸い顔",
    "large round eyes": "大きな目",
    "short bob hair": "ボブ風の髪",
    "mint green star": "ミントグリーンの星",
    "pink cheeks": "ピンクのほっぺ",
    "gentle smile": "やさしい笑顔",
    "ribbon accent": "リボン",
    "hat accent": "帽子",
}


def _pick_enum(value: Any, allowed: frozenset[str], default: str) -> str:
    v = str(value or "unknown").strip().lower()
    if v in allowed:
        return v
    return default if default in allowed else next(iter(allowed - {"unknown"}))


def _coerce_vision_result(raw: dict[str, Any]) -> dict[str, Any]:
    """API / ルールベース入力を schema 形にそろえる。"""
    inner = raw.get("attributes") if isinstance(raw.get("attributes"), dict) else raw
    sig = inner.get("signature_features")
    if not isinstance(sig, list):
        sig = raw.get("signature_features") if isinstance(raw.get("signature_features"), list) else []

    return {
        "face_shape": inner.get("face_shape", raw.get("face_shape", "unknown")),
        "hair_color": inner.get("hair_color", raw.get("hair_color", "unknown")),
        "hair_style": inner.get("hair_style", raw.get("hair_style", "unknown")),
        "bangs": inner.get("bangs", raw.get("bangs", "unknown")),
        "eye_shape": inner.get("eye_shape", raw.get("eye_shape", "unknown")),
        "eye_count": int(inner.get("eye_count", raw.get("eye_count", 2)) or 2),
        "mouth": inner.get("mouth", raw.get("mouth", "unknown")),
        "cheeks": bool(inner.get("cheeks", raw.get("cheeks", True))),
        "accent_color": inner.get("accent_color", raw.get("accent_color", "unknown")),
        "accessory": inner.get("accessory", raw.get("accessory", "unknown")),
        "mood": inner.get("mood", raw.get("mood", "unknown")),
        "signature_features": [str(s) for s in sig[:12]],
    }


def normalize_character_dna(vision_result: dict[str, Any]) -> dict[str, Any]:
    """
    Vision API の結果を、まなともで使う固定キャラクター DNA に正規化する。
    不明・ブレ・余計な解釈を補正する。
    """
    v = _coerce_vision_result(vision_result)
    defaults = MANATOMO_DEFAULT_VISION

    face = _pick_enum(v["face_shape"], FACE_SHAPES, "round")
    if face == "unknown":
        face = defaults["face_shape"]

    hair_color = _pick_enum(v["hair_color"], HAIR_COLORS, "dark_navy")
    if hair_color == "unknown":
        hair_color = defaults["hair_color"]

    hair_style = _pick_enum(v["hair_style"], HAIR_STYLES, "short_bob")
    if hair_style == "unknown":
        hair_style = defaults["hair_style"]

    bangs = _pick_enum(v["bangs"], BANGS, "center")
    if bangs == "unknown":
        bangs = defaults["bangs"]

    eye_shape = _pick_enum(v["eye_shape"], EYE_SHAPES, "large_round")
    if eye_shape == "unknown":
        eye_shape = defaults["eye_shape"]

    mouth = _pick_enum(v["mouth"], MOUTHS, "smile")
    if mouth == "unknown":
        mouth = defaults["mouth"]

    accent = _pick_enum(v["accent_color"], ACCENT_COLORS, "mint_green")
    if accent == "none" and defaults["accent_color"] != "none":
        accent = defaults["accent_color"]
    elif accent == "unknown":
        accent = defaults["accent_color"]

    accessory = _pick_enum(v["accessory"], ACCESSORIES, "star")
    if accessory == "unknown":
        accessory = defaults["accessory"]

    mood = _pick_enum(v["mood"], MOODS, "cheerful")
    if mood == "unknown":
        mood = defaults["mood"]

    eye_count = int(v.get("eye_count") or 2)
    if eye_count != 2:
        eye_count = 2

    cheeks = bool(v.get("cheeks", True))

    signature = list(v.get("signature_features") or [])
    if not signature:
        signature = list(defaults["signature_features"])

    locked = {
        "hair_color": hair_color,
        "hair_style": hair_style,
        "bangs": bangs,
        "eye_shape": eye_shape,
        "mouth": _mouth_to_renderer(mouth),
        "cheeks": cheeks,
        "accent_color": accent,
        "accessory": accessory,
    }

    return {
        "base_identity": {
            "type": "cute_chibi_girl",
            "face_shape": _face_to_renderer(face),
            "mood": mood,
        },
        "locked_features": locked,
        "style_rules": {
            "art_style": "famicom_pixel_art",
            "view": "front",
            "body_type": "small_chibi",
            "background": "white",
            "palette_limit": 6,
            "outline": "thick_dark",
        },
        "signature_features": signature,
        "normalization_notes": _normalization_notes(v, locked),
    }


def _face_to_renderer(face: str) -> str:
    if face == "square":
        return "wide"
    if face == "oval":
        return "oval"
    return "round"


def _mouth_to_renderer(mouth: str) -> str:
    if mouth == "neutral":
        return "small"
    if mouth == "open_smile":
        return "gentle_smile"
    return "gentle_smile"


def _normalization_notes(vision: dict[str, Any], locked: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key in VISION_RESULT_KEYS:
        if key == "signature_features":
            continue
        raw = vision.get(key)
        if str(raw).lower() in ("unknown", "", "none") and key in locked:
            notes.append(f"defaulted_{key}")
    return notes


def build_generation_prompt(character_dna: dict[str, Any], stage: str) -> str:
    """画像生成 AI 用の固定制約プロンプト（DNA から組み立て。Vision 原文は入れない）。"""
    locked = character_dna["locked_features"]
    identity = character_dna["base_identity"]
    parts = [
        "front view only",
        "full body chibi character",
        "white background",
        "centered composition",
        "same character identity across stages",
        "preserve locked features",
        "no realistic style",
        "no detailed background",
        "no side view",
        "no different hairstyle",
        "no different gender",
        "no extra characters",
        "no text",
        "Japanese retro Famicom pixel art",
        "thick pixel outline",
        f"stage: {stage}",
        f"face_shape: {identity['face_shape']}",
        f"hair_color: {locked['hair_color']}",
        f"hair_style: {locked['hair_style']}",
        f"bangs: {locked['bangs']}",
        f"eye_shape: {locked['eye_shape']}",
        f"mouth: {locked['mouth']}",
        f"accent_color: {locked['accent_color']}",
        f"accessory: {locked['accessory']}",
        f"mood: {identity['mood']}",
    ]
    stage_hints = {
        "baby": "minimal decoration, small round body, tiny star above head or beside head",
        "child": "add limbs, bright expression, star as hair ornament",
        "student": "add one of book pencil or hat, learner mood, face fully visible",
        "hero": "cape badge star wand, RPG hero, keep same hair eyes cheeks smile",
    }
    if stage in stage_hints:
        parts.append(stage_hints[stage])
    return ", ".join(parts)


STAGE_RULES: dict[str, dict[str, Any]] = {
    "egg": {
        "limbs": False,
        "star_placement": "none",
        "stage_decor": "egg",
        "student_prop": None,
        "scale": 0.92,
    },
    "baby": {
        "limbs": False,
        "star_placement": "above_head",
        "stage_decor": "minimal",
        "student_prop": None,
        "scale": 0.94,
    },
    "child": {
        "limbs": True,
        "star_placement": "hair_ornament",
        "stage_decor": "light",
        "student_prop": None,
        "scale": 1.0,
    },
    "student": {
        "limbs": True,
        "star_placement": "hair_ornament",
        "stage_decor": "study",
        "student_prop": "book",
        "scale": 1.0,
    },
    "hero": {
        "limbs": True,
        "star_placement": "wand_or_badge",
        "stage_decor": "hero",
        "student_prop": None,
        "scale": 1.0,
    },
}


def build_stage_spec(character_dna: dict[str, Any], stage: str) -> dict[str, Any]:
    """
    character_dna をもとに、baby/child/student/hero の各ステージ設計を作る。
    locked_features は全ステージで維持する。
    """
    stage = stage if stage in STAGE_RULES else "baby"
    rules = deepcopy(STAGE_RULES[stage])
    locked = deepcopy(character_dna["locked_features"])

    return {
        "stage": stage,
        "base_identity": deepcopy(character_dna["base_identity"]),
        "locked_features": locked,
        "style_rules": deepcopy(character_dna["style_rules"]),
        "stage_rules": rules,
        "generation_prompt": build_generation_prompt(character_dna, stage),
        "signature_features": list(character_dna.get("signature_features") or []),
    }


def stage_spec_to_render_spec(stage_spec: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    """stage_spec → pixel_character_renderer 用の設計 dict。"""
    locked = stage_spec["locked_features"]
    identity = stage_spec["base_identity"]
    rules = stage_spec["stage_rules"]
    stage = stage_spec["stage"]

    hair_rgb = HAIR_COLOR_RGB.get(locked["hair_color"], HAIR_COLOR_RGB["dark_navy"])
    accent_key = locked["accent_color"]
    accent_rgb = ACCENT_COLOR_RGB.get(accent_key, ACCENT_COLOR_RGB["mint_green"])

    hair_style_render = {
        "short_bob": "short_bob",
        "long": "ponytail",
        "twin_tail": "ponytail",
        "short": "simple",
    }.get(locked["hair_style"], "short_bob")

    bangs_render = {
        "center": "center_long_bangs",
        "straight": "center_long_bangs",
        "side": "short_bangs",
        "none": "none",
    }.get(locked["bangs"], "center_long_bangs")

    eye_type = {
        "large_round": "large_round",
        "small_dot": "medium_round",
        "almond": "medium_round",
    }.get(locked["eye_shape"], "large_round")

    accessory = locked["accessory"]
    show_star = accessory == "star" and accent_key != "none"
    if strict:
        show_star = accessory == "star"

    spec: dict[str, Any] = {
        "character_type": "cute_chibi_girl",
        "face_shape": identity["face_shape"],
        "hair": {
            "style": hair_style_render,
            "bangs": bangs_render,
            "side_hair": hair_style_render in ("short_bob", "ponytail"),
            "color": locked["hair_color"],
        },
        "eyes": {
            "type": eye_type,
            "count": 2,
            "highlight": locked["eye_shape"] == "large_round",
            "spacing": "wide",
        },
        "mouth": {"type": locked["mouth"]},
        "cheeks": {"enabled": bool(locked["cheeks"])},
        "ears": {"visible": True},
        "accessories": {
            "star": show_star,
            "bow": accessory == "ribbon",
            "hat": accessory == "hat",
            "accent_color": accent_key,
            "accent_rgb": accent_rgb,
        },
        "body": {"type": "small_chibi"},
        "mood": identity["mood"],
        "stage": stage,
        "limbs": bool(rules.get("limbs")),
        "star_placement": rules.get("star_placement", "hair_ornament"),
        "stage_decor": rules.get("stage_decor", "light"),
        "student_prop": rules.get("student_prop"),
        "signature_features": stage_spec.get("signature_features", []),
        "vision_enriched": True,
        "palette": _palette_from_locked(locked, accent_rgb, hair_rgb),
        "debug_notes": [
            f"Rendered from character_dna stage={stage}",
            "locked_features preserved",
        ],
    }
    if strict:
        spec["debug_notes"].append("strict_validation_retry")
    return spec


def _palette_from_locked(
    locked: dict[str, Any],
    accent_rgb: tuple[int, int, int],
    hair_rgb: tuple[int, int, int],
) -> dict[str, tuple[int, int, int]]:
    from .color_utils import darken, lighten

    shirt = (80, 140, 220)
    return {
        "outline": (34, 34, 34),
        "skin": (255, 248, 240),
        "skin_shadow": (255, 228, 218),
        "hair": hair_rgb,
        "hair_hi": lighten(hair_rgb, 0.22),
        "cheek": (255, 180, 170) if locked.get("cheeks") else (255, 248, 240),
        "eye_white": (255, 255, 255),
        "eye_pupil": (34, 34, 34),
        "accent": accent_rgb,
        "shirt": shirt,
        "shirt_shadow": darken(shirt, 0.2),
        "gold": (255, 210, 80),
        "cape": (220, 72, 72),
        "glow": (255, 255, 200),
    }


def signature_features_ja_from_dna(character_dna: dict[str, Any]) -> list[str]:
    ja: list[str] = []
    seen: set[str] = set()
    for key in character_dna.get("signature_features") or []:
        label = SIGNATURE_FEATURES_JA.get(key, key)
        if label not in seen:
            ja.append(label)
            seen.add(label)
    if not ja:
        ja = ["丸い顔", "大きな目", "ボブ風の髪", "ミントグリーンの星", "ピンクのほっぺ"]
    return ja


def rule_based_to_vision_result(raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    """ルールベース特徴 → Vision schema（フォールバック用）。"""
    hair_map = {"bob": "short_bob", "short": "short", "ponytail": "long", "long": "long", "simple": "short"}
    face = str(raw.get("face_shape") or "round")
    face_schema = "round" if face == "round" else ("oval" if face == "oval" else "square")

    accessories = raw.get("accessories") or []
    accessory = "star" if "star" in accessories or analysis.get("star_detected") else "none"

    eye_score = float(analysis.get("eye_size_score", 0.75))
    eye_shape = "large_round" if eye_score >= 0.45 else "small_dot"

    return {
        "face_shape": face_schema,
        "hair_color": "dark_navy",
        "hair_style": hair_map.get(str(raw.get("hair_style", "bob")), "short_bob"),
        "bangs": "center" if raw.get("bangs", True) else "none",
        "eye_shape": eye_shape,
        "eye_count": 2,
        "mouth": "smile" if analysis.get("smile_likely", True) else "neutral",
        "cheeks": bool(analysis.get("cheeks_detected", True)),
        "accent_color": "mint_green",
        "accessory": accessory,
        "mood": "cheerful" if raw.get("mood") == "cute" else "cute",
        "signature_features": list(MANATOMO_DEFAULT_VISION["signature_features"]),
    }
