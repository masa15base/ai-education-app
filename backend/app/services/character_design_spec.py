"""
手書き画像の特徴 → キャラクター設計書（character_design_spec）。
不足分は子ども向けかわいい女の子キャラとして自然に補完する。
"""
from __future__ import annotations

from typing import Any

from .color_utils import clamp_rgb, darken, lighten, pick_salient_color

# 子ども向け・女の子線画の自然なデフォルト（MVP）
DEFAULT_CUTE_GIRL: dict[str, Any] = {
    "character_type": "cute_girl",
    "face_shape": "round",
    "hair": {
        "color": "dark_navy",
        "style": "short_bob",
        "bangs": "center_long_bangs",
        "side_hair": True,
        "outer_shape": "rounded",
        "highlight": True,
    },
    "eyes": {
        "type": "large_round",
        "count": 2,
        "highlight": True,
        "spacing": "wide",
    },
    "mouth": {"type": "gentle_smile"},
    "cheeks": {
        "enabled": True,
        "color": "soft_pink",
        "position": "both_sides",
    },
    "ears": {"visible": True, "style": "simple"},
    "accessories": {
        "star": True,
        "star_color": "mint_green",
        "star_position": "left_of_head",
        "accent_color": "mint_green",
    },
    "body": {
        "type": "small_chibi",
        "outfit": "simple_learning_uniform",
    },
    "mood": "bright_cute",
    "signature_features": [
        "large round eyes",
        "soft smile",
        "rounded short bob hair",
        "mint green star accent",
        "pink cheeks",
    ],
}

COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "dark_navy": (42, 48, 72),
    "dark_navy_hi": (68, 74, 98),
    "soft_pink": (255, 180, 170),
    "mint_green": (85, 221, 204),
    "skin": (255, 248, 240),
    "skin_shadow": (255, 228, 218),
    "outline": (34, 34, 34),
    "eye_white": (255, 255, 255),
    "shirt_blue": (80, 140, 220),
    "shirt_shadow": (55, 100, 180),
    "gold": (255, 210, 80),
    "cape_red": (220, 72, 72),
    "glow": (255, 255, 200),
}

SIGNATURE_FEATURES_JA: dict[str, str] = {
    "large round eyes": "大きな目",
    "soft smile": "やさしい笑顔",
    "rounded short bob hair": "ボブ風の髪",
    "mint green star accent": "ミントグリーンの星",
    "pink cheeks": "ピンクのほっぺ",
    "round face": "丸い顔",
    "oval face": "卵型の顔",
    "wide face": "わりと横長の顔",
    "girl character": "女の子らしい顔",
    "center bangs": "前髪",
    "side hair": "横髪",
    "ponytail hair": "ポニーテール",
    "gentle mood": "かわいい・明るい雰囲気",
    "vision analyzed": "AIが絵を読み取り",
}


def _vision_signature_ja(
    vision_attrs: dict[str, Any],
    analysis: dict[str, Any],
    image_understanding: dict[str, Any],
) -> list[str]:
    """Vision マージ時の UI 用特徴（デフォルト文言の丸写しを避ける）。"""
    ja: list[str] = ["AIが絵を読み取り"]
    face = analysis.get("face_shape_detected", "round")
    face_labels = {"round": "丸い顔", "oval": "卵型の顔", "wide": "横長の顔"}
    if face in face_labels:
        ja.append(face_labels[face])
    hair = str(vision_attrs.get("hair_style") or analysis.get("hair_style_detected", ""))
    if hair in ("ponytail", "long"):
        ja.append("ポニーテール")
    elif hair in ("spiky",):
        ja.append("ツンツン髪")
    elif hair in ("bob", "short"):
        ja.append("ボブ風の髪")
    if float(analysis.get("eye_size_score", 0)) >= 0.45:
        ja.append("大きな目")
    if analysis.get("cheeks_detected"):
        ja.append("ピンクのほっぺ")
    if analysis.get("smile_likely"):
        ja.append("やさしい笑顔")
    if analysis.get("star_detected"):
        ja.append("星のアクセント")
    desc = (image_understanding.get("vision_api_response") or {}).get("description")
    if desc and len(ja) < 6:
        ja.append(str(desc)[:36])
    return ja[:8]


def build_image_analysis(features: dict[str, Any]) -> dict[str, Any]:
    """抽出 features を設計用の image_analysis に正規化（後方互換）。"""
    accent = features.get("accent_rgb") or COLOR_MAP["mint_green"]
    return {
        "has_content": bool(features.get("has_content", True)),
        "face_shape_detected": features.get("face_shape", "round"),
        "hair_style_detected": features.get("hair_style", "bob"),
        "bangs_detected": bool(features.get("bangs", True)),
        "eye_size_score": float(features.get("eye_size", 0.75)),
        "cheeks_detected": bool(features.get("cheeks", True)),
        "smile_likely": features.get("mood") in ("cute", "gentle", "bright_cute"),
        "star_detected": "star" in (features.get("accessories") or []),
        "accent_rgb": accent,
        "aspect": features.get("aspect", 1.0),
        "mood_detected": features.get("mood", "cute"),
    }


def _analysis_from_understanding(image_understanding: dict[str, Any]) -> dict[str, Any]:
    if "analysis" in image_understanding:
        return image_understanding["analysis"]
    if "raw_features" in image_understanding:
        return build_image_analysis(image_understanding["raw_features"])
    return image_understanding


def build_character_design_spec(
    image_understanding: dict[str, Any],
    *,
    stage: str = "baby",
    features: dict[str, Any] | None = None,
    image_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    image_understanding からキャラクター設計書を作る。
    後方互換: features / image_analysis のみ渡された場合も受け付ける。
    """
    if features is not None:
        analysis = image_analysis or build_image_analysis(features)
    elif "analysis" in image_understanding:
        analysis = image_understanding["analysis"]
    elif "raw_features" in image_understanding:
        analysis = build_image_analysis(image_understanding["raw_features"])
    elif "vision_api_ready" in image_understanding or "pipeline_step" in image_understanding:
        analysis = _analysis_from_understanding(image_understanding)
    else:
        analysis = image_analysis or build_image_analysis(image_understanding)
    spec: dict[str, Any] = {
        k: (v.copy() if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
        for k, v in DEFAULT_CUTE_GIRL.items()
    }
    debug_notes: list[str] = []
    signature: list[str] = list(spec["signature_features"])
    use_vision = image_understanding.get("source") == "vision_api_merged"
    vision_attrs = (
        (image_understanding.get("vision_api_response") or {}).get("attributes") or {}
    )

    char_type = str(vision_attrs.get("character_type") or "cute_girl").lower()
    spec["character_type"] = char_type if use_vision else "cute_girl"
    face_detected = analysis.get("face_shape_detected", "round")
    if use_vision and face_detected in ("round", "oval", "wide"):
        spec["face_shape"] = face_detected
        debug_notes.append(f"Vision: face_shape={face_detected}")
        signature.append(f"{face_detected} face")
    else:
        spec["face_shape"] = "round"
        debug_notes.append("Applied round face (cute girl default)")

    hair_detected = analysis.get("hair_style_detected", "bob")
    hair_vision = str(vision_attrs.get("hair_style") or hair_detected).lower()
    if use_vision and hair_vision in ("ponytail", "long"):
        spec["hair"]["style"] = "ponytail"
        spec["hair"]["bangs"] = "center_long_bangs" if vision_attrs.get("bangs", True) else "none"
        spec["hair"]["side_hair"] = True
        debug_notes.append("Vision: ponytail / long hair")
        signature.append("ponytail hair")
    elif hair_vision in ("spiky",):
        spec["hair"]["style"] = "spiky"
        spec["hair"]["bangs"] = "short_bangs" if vision_attrs.get("bangs", True) else "none"
        spec["hair"]["side_hair"] = False
        debug_notes.append("Vision: spiky hair")
        signature.append("spiky hair")
    elif hair_vision in ("simple", "bald", "other"):
        spec["hair"]["style"] = "simple"
        spec["hair"]["bangs"] = "none"
        spec["hair"]["side_hair"] = False
        debug_notes.append("Vision: simple / minimal hair")
    elif hair_detected in ("bob", "short") or hair_vision in ("bob", "short"):
        spec["hair"]["style"] = "short_bob"
        spec["hair"]["bangs"] = "center_long_bangs"
        spec["hair"]["side_hair"] = True
        debug_notes.append("Applied short bob hair with bangs and side hair")
    else:
        spec["hair"]["style"] = "short_bob"
        spec["hair"]["bangs"] = "center_long_bangs"
        debug_notes.append("Assumed bob hair (default complement)")

    eye_score = float(analysis.get("eye_size_score", 0.75))
    if eye_score >= 0.45:
        spec["eyes"]["type"] = "large_round"
        spec["eyes"]["highlight"] = True
        debug_notes.append("Large round eyes with highlight")
    else:
        spec["eyes"]["type"] = "medium_round"
        spec["eyes"]["highlight"] = eye_score >= 0.35
        debug_notes.append("Medium eyes from drawing / vision")

    eye_spacing = str(vision_attrs.get("eye_spacing") or "wide").lower()
    if eye_spacing in ("wide", "normal", "close"):
        spec["eyes"]["spacing"] = eye_spacing

    spec["cheeks"]["enabled"] = bool(analysis.get("cheeks_detected", True))
    if use_vision:
        spec["cheeks"]["enabled"] = bool(vision_attrs.get("cheeks", True))
    spec["mouth"]["type"] = "gentle_smile" if analysis.get("smile_likely", True) else "small"

    accent = tuple(analysis.get("accent_rgb") or COLOR_MAP["mint_green"])
    spec["accessories"]["accent_rgb"] = accent
    star_on = bool(analysis.get("star_detected"))
    if use_vision:
        star_on = bool(vision_attrs.get("star_accent"))
    spec["accessories"]["star"] = star_on if use_vision else True
    spec["accessories"]["accent_color"] = "mint_green"
    if star_on:
        debug_notes.append("Detected star accent from drawing")
    elif use_vision:
        debug_notes.append("Vision: no star in drawing")
    else:
        spec["accessories"]["star"] = True
        debug_notes.append("Added mint green star accessory (signature default)")

    if use_vision:
        debug_notes.append("Vision API merged into design spec")
        if "vision analyzed" not in signature:
            signature.append("vision analyzed")

        raw = image_understanding.get("raw_features") or {}
        hair_rgb = pick_salient_color(
            clamp_rgb(vision_attrs.get("hair_color_rgb"), COLOR_MAP["dark_navy"]),
            clamp_rgb(raw.get("hair_color_rgb"), COLOR_MAP["dark_navy"]),
            fallback=COLOR_MAP["dark_navy"],
        )
        outfit_rgb = clamp_rgb(
            vision_attrs.get("outfit_color_rgb"),
            COLOR_MAP["shirt_blue"],
        )
        accent_rgb = pick_salient_color(
            clamp_rgb(vision_attrs.get("accent_color_rgb"), COLOR_MAP["mint_green"]),
            clamp_rgb(analysis.get("accent_rgb"), COLOR_MAP["mint_green"]),
            fallback=COLOR_MAP["mint_green"],
        )
        spec["vision_palette"] = {
            "hair": hair_rgb,
            "hair_hi": lighten(hair_rgb, 0.22),
            "shirt": outfit_rgb,
            "shirt_shadow": darken(outfit_rgb, 0.22),
            "accent": accent_rgb,
        }
        spec["accessories"]["accent_rgb"] = accent_rgb
        spec["skin_tone"] = str(vision_attrs.get("skin_tone") or "light")
        accessories = [str(a).lower() for a in (vision_attrs.get("accessories") or [])]
        spec["accessories"]["bow"] = "bow" in accessories or "ribbon" in accessories
        spec["accessories"]["glasses"] = "glasses" in accessories
        debug_notes.append(f"Vision colors hair={hair_rgb} outfit={outfit_rgb} accent={accent_rgb}")
    else:
        if "girl character" not in signature:
            signature.append("girl character")
        if "round face" not in signature:
            signature.append("round face")
        if "center bangs" not in signature:
            signature.append("center bangs")
        if "side hair" not in signature:
            signature.append("side hair")
        if "gentle mood" not in signature:
            signature.append("gentle mood")

    spec["signature_features"] = signature
    spec["vision_enriched"] = use_vision
    if use_vision:
        spec["vision_signature_ja"] = _vision_signature_ja(
            vision_attrs, analysis, image_understanding
        )
    spec["stage"] = stage
    spec["palette"] = spec_palette_from_spec(spec)
    spec["star_placement"] = _star_placement_for_stage(stage)
    spec["stage_decor"] = _stage_decor_for_stage(stage)
    spec["limbs"] = stage not in ("egg", "baby")
    spec["debug_notes"] = debug_notes
    return spec


def _skin_colors_for_tone(tone: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if tone == "tan":
        return (255, 220, 190), (240, 190, 160)
    if tone == "medium":
        return (255, 235, 215), (245, 215, 195)
    return COLOR_MAP["skin"], COLOR_MAP["skin_shadow"]


def spec_palette_from_spec(spec: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    """設計書 → 描画パレット（Vision 色があれば優先）。"""
    accent = spec.get("accessories", {}).get("accent_rgb") or COLOR_MAP["mint_green"]
    if isinstance(accent, list):
        accent = tuple(accent)
    accent = clamp_rgb(accent, COLOR_MAP["mint_green"])

    custom = dict(spec.get("vision_palette") or {})
    skin, skin_shadow = _skin_colors_for_tone(str(spec.get("skin_tone") or "light"))

    hair = custom.get("hair") or COLOR_MAP["dark_navy"]
    shirt = custom.get("shirt") or COLOR_MAP["shirt_blue"]

    return {
        "outline": COLOR_MAP["outline"],
        "skin": custom.get("skin") or skin,
        "skin_shadow": custom.get("skin_shadow") or skin_shadow,
        "hair": hair,
        "hair_hi": custom.get("hair_hi") or lighten(hair, 0.2),
        "cheek": custom.get("cheek") or COLOR_MAP["soft_pink"],
        "eye_white": COLOR_MAP["eye_white"],
        "eye_pupil": COLOR_MAP["outline"],
        "accent": custom.get("accent") or accent,
        "shirt": shirt,
        "shirt_shadow": custom.get("shirt_shadow") or darken(shirt, 0.2),
        "gold": COLOR_MAP["gold"],
        "cape": COLOR_MAP["cape_red"],
        "glow": COLOR_MAP["glow"],
    }


def signature_features_for_ui(spec: dict[str, Any]) -> list[str]:
    """UI 表示用の日本語特徴リスト。"""
    if spec.get("vision_signature_ja"):
        return list(spec["vision_signature_ja"])

    ja: list[str] = []
    seen: set[str] = set()
    for key in spec.get("signature_features") or []:
        label = SIGNATURE_FEATURES_JA.get(key, key)
        if label not in seen:
            ja.append(label)
            seen.add(label)
    if spec.get("vision_enriched"):
        defaults: list[str] = []
    else:
        defaults = ["丸い顔", "大きな目", "やさしい笑顔", "ボブ風の髪", "ミントグリーンの星", "ピンクのほっぺ"]
    for d in defaults:
        if d not in seen:
            ja.append(d)
            seen.add(d)
    return ja


def _star_placement_for_stage(stage: str) -> str:
    return {
        "egg": "none",
        "baby": "above_head",
        "child": "hair_ornament",
        "student": "hat_or_bag",
        "hero": "wand_or_badge",
    }.get(stage, "hair_ornament")


def _stage_decor_for_stage(stage: str) -> str:
    return {
        "egg": "egg",
        "baby": "minimal",
        "child": "light",
        "student": "study",
        "hero": "hero",
    }.get(stage, "light")


def merge_debug_notes(*parts: list[str]) -> list[str]:
    out: list[str] = []
    for p in parts:
        for n in p:
            if n and n not in out:
                out.append(n)
    return out
