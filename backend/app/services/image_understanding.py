"""
手書き画像の image_understanding（特徴抽出）。
ルールベースをベースに、OPENAI_API_KEY があるとき OpenAI Vision で上書きマージ。
"""
from __future__ import annotations

import colorsys
import io
import os
from typing import Any

from PIL import Image, ImageOps

# Vision API に渡すときのスキーマ例（MVP では rule_based で埋める）
VISION_SCHEMA_VERSION = "1.0"


def _ensure_black_ink_on_white(line_img: Image.Image) -> Image.Image:
    g = line_img.convert("L")
    hist = g.histogram()
    total = max(1, sum(hist))
    mean_l = sum(i * hist[i] for i in range(256)) / total
    if mean_l < 128:
        return ImageOps.invert(g)
    return g


def _ink_mask(g: Image.Image, threshold: int = 200) -> list[list[bool]]:
    w, h = g.size
    px = g.load()
    return [[px[x, y] < threshold for x in range(w)] for y in range(h)]


def _bbox_from_mask(mask: list[list[bool]]) -> tuple[int, int, int, int] | None:
    h = len(mask)
    if not h:
        return None
    w = len(mask[0])
    ys, xs = [], []
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                ys.append(y)
                xs.append(x)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _region_ink_ratio(
    mask: list[list[bool]], x0: int, y0: int, x1: int, y1: int
) -> float:
    total = ink = 0
    for y in range(y0, y1):
        if y < 0 or y >= len(mask):
            continue
        for x in range(x0, x1):
            if x < 0 or x >= len(mask[0]):
                continue
            total += 1
            if mask[y][x]:
                ink += 1
    return ink / max(1, total)


def _dominant_accent_rgb(rgb: Image.Image) -> tuple[int, int, int] | None:
    px = rgb.convert("RGB").load()
    w, h = rgb.size
    buckets: dict[tuple[int, int, int], int] = {}
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if r > 240 and g > 240 and b > 240:
                continue
            if r < 40 and g < 40 and b < 40:
                continue
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s < 0.18 or v < 0.25:
                continue
            key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
            buckets[key] = buckets.get(key, 0) + 1
    if not buckets:
        return None
    return max(buckets, key=buckets.get)


def _eye_size_score(mask: list[list[bool]], fx0: int, fy0: int, fx1: int, fy1: int) -> float:
    fh = max(1, fy1 - fy0)
    eye_y1 = fy0 + int(fh * 0.55)
    ratio = _region_ink_ratio(mask, fx0, fy0, fx1, eye_y1)
    if ratio > 0.12:
        return 1.0
    if ratio > 0.07:
        return 0.65
    return 0.35


def _extract_raw_features(
    line_img: Image.Image, rgb_source: Image.Image | None = None
) -> dict[str, Any]:
    """ルールベースの低レベル特徴（手書きを直接ドット化しない）。"""
    g = _ensure_black_ink_on_white(line_img)
    w, h = g.size
    mask = _ink_mask(g)
    bbox = _bbox_from_mask(mask)

    if not bbox:
        return {
            "has_content": False,
            "face_shape": "round",
            "hair_style": "bob",
            "bangs": True,
            "eye_size": 0.8,
            "cheeks": True,
            "mood": "cute",
            "accent_rgb": (85, 221, 204),
            "accessories": [],
            "simplicity": 0.9,
            "bbox": (0, 0, w, h),
            "aspect": 1.0,
        }

    x0, y0, x1, y1 = bbox
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    aspect = bw / bh
    hair_y1 = y0 + int(bh * 0.38)
    face_y0 = y0 + int(bh * 0.22)
    face_y1 = y0 + int(bh * 0.72)
    face_x0 = x0 + int(bw * 0.15)
    face_x1 = x1 - int(bw * 0.15)

    hair_top_ratio = _region_ink_ratio(mask, x0, y0, x1, hair_y1)
    hair_side_ratio = _region_ink_ratio(
        mask, x0, y0, x0 + int(bw * 0.22), hair_y1
    ) + _region_ink_ratio(mask, x1 - int(bw * 0.22), y0, x1, hair_y1)

    if hair_top_ratio > 0.14 and hair_side_ratio > 0.08:
        hair_style, bangs = "bob", True
    elif hair_top_ratio > 0.08:
        hair_style, bangs = "short", hair_top_ratio > 0.05
    else:
        hair_style, bangs = "simple", False

    if 0.82 <= aspect <= 1.18:
        face_shape = "round"
    elif aspect > 1.18:
        face_shape = "wide"
    else:
        face_shape = "oval"

    eye_score = _eye_size_score(mask, face_x0, face_y0, face_x1, face_y1)
    cheek_ink = _region_ink_ratio(
        mask, face_x0, face_y0 + int((face_y1 - face_y0) * 0.45), face_x1, face_y1
    )
    accent = _dominant_accent_rgb(rgb_source) if rgb_source else None
    if accent is None:
        accent = (85, 221, 204)

    accessories: list[str] = []
    if _region_ink_ratio(mask, x0, y0, x0 + int(bw * 0.2), y0 + int(bh * 0.35)) > 0.03:
        accessories.append("star")

    ink_pixels = sum(sum(row) for row in mask)
    return {
        "has_content": True,
        "bbox": bbox,
        "centroid": ((x0 + x1) / 2, (y0 + y1) / 2),
        "aspect": round(aspect, 3),
        "ink_ratio": round(ink_pixels / max(1, w * h), 4),
        "face_shape": face_shape,
        "hair_style": hair_style,
        "bangs": bangs,
        "eye_size": round(eye_score, 2),
        "cheeks": cheek_ink > 0.03 or eye_score > 0.5,
        "mood": "cute" if eye_score > 0.5 else "gentle",
        "accent_rgb": accent,
        "accessories": accessories,
        "simplicity": round(1.0 - min(0.5, ink_pixels / max(1, w * h) * 8), 2),
    }


def _build_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    accent = raw.get("accent_rgb") or (85, 221, 204)
    return {
        "has_content": bool(raw.get("has_content", True)),
        "face_shape_detected": raw.get("face_shape", "round"),
        "hair_style_detected": raw.get("hair_style", "bob"),
        "bangs_detected": bool(raw.get("bangs", True)),
        "eye_size_score": float(raw.get("eye_size", 0.75)),
        "cheeks_detected": bool(raw.get("cheeks", True)),
        "smile_likely": raw.get("mood") in ("cute", "gentle", "bright_cute"),
        "star_detected": "star" in (raw.get("accessories") or []),
        "accent_rgb": accent,
        "aspect": raw.get("aspect", 1.0),
        "mood_detected": raw.get("mood", "cute"),
    }


def _vision_api_payload(raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    """将来の Vision API 入出力とマージしやすい形式。"""
    tags = ["cute", "hand_drawn", "child_character"]
    if analysis.get("face_shape_detected") == "round":
        tags.append("round_face")
    if analysis.get("hair_style_detected") in ("bob", "short"):
        tags.append("bob_hair")
    if analysis.get("star_detected"):
        tags.append("star_accessory")

    description = (
        "A cute girl character with round face, large eyes, gentle smile, "
        "short bob dark hair with bangs, pink cheeks, and mint green star accent."
    )
    return {
        "schema_version": VISION_SCHEMA_VERSION,
        "description": description,
        "tags": tags,
        "attributes": {
            "character_type": "cute_girl",
            "face_shape": analysis.get("face_shape_detected"),
            "hair_style": analysis.get("hair_style_detected"),
            "eye_size": "large" if analysis.get("eye_size_score", 0) >= 0.45 else "medium",
            "cheeks": analysis.get("cheeks_detected"),
            "star_accent": analysis.get("star_detected"),
            "accent_color_rgb": list(analysis.get("accent_rgb") or (85, 221, 204)),
            "mood": "bright_cute",
        },
        "provider": "rule_based_mvp",
        "merge_hint": "Replace attributes with Vision API response when available",
    }


def _complemented_defaults(raw: dict[str, Any]) -> list[str]:
    """検出できなかったが補完した項目。"""
    notes: list[str] = []
    if not raw.get("has_content"):
        notes.append("no_ink_detected_used_cute_girl_defaults")
    if "star" not in (raw.get("accessories") or []):
        notes.append("star_accent_complemented")
    if float(raw.get("eye_size", 0)) < 0.45:
        notes.append("large_eyes_complemented")
    notes.append("round_face_and_bob_hair_complemented")
    return notes


def understand_image_from_pil(
    line_img: Image.Image,
    rgb_source: Image.Image | None = None,
) -> dict[str, Any]:
    """PIL 画像から image_understanding を生成。"""
    raw = _extract_raw_features(line_img, rgb_source)
    analysis = _build_analysis(raw)
    return {
        "source": "rule_based_mvp",
        "pipeline_step": "image_understanding",
        "raw_features": raw,
        "analysis": analysis,
        "detected": {
            "face_shape": analysis["face_shape_detected"],
            "hair_style": analysis["hair_style_detected"],
            "bangs": analysis["bangs_detected"],
            "large_eyes": analysis["eye_size_score"] >= 0.45,
            "cheeks": analysis["cheeks_detected"],
            "smile": analysis["smile_likely"],
            "star_accent": analysis["star_detected"],
            "accent_rgb": analysis["accent_rgb"],
            "mood": analysis["mood_detected"],
        },
        "vision_api_ready": _vision_api_payload(raw, analysis),
        "complemented_defaults": _complemented_defaults(raw),
    }


def understand_image(image_bytes: bytes) -> dict[str, Any]:
    """
    PNG/JPEG bytes → image_understanding。
    Vision は schema JSON 抽出のみ。character_dna は normalize_character_dna() 経由。
    """
    from .character_dna import normalize_character_dna, rule_based_to_vision_result
    from .vision_client import fetch_vision_result, is_character_vision_enabled

    raw_img = Image.open(io.BytesIO(image_bytes))
    rgb = raw_img.convert("RGB")
    line = _ensure_black_ink_on_white(raw_img.convert("L"))
    rule = understand_image_from_pil(line, rgb)

    vision_result = rule_based_to_vision_result(rule["raw_features"], rule["analysis"])
    source = "rule_based"
    vision_status = "rule_based"
    vision_error: str | None = None

    if is_character_vision_enabled():
        rule["vision_api_attempted"] = True
        vr, vision_err = fetch_vision_result(image_bytes)
        if vr:
            vision_result = vr
            source = "vision_api"
            vision_status = "ok"
        else:
            vision_status = "fallback_rule_based"
            vision_error = vision_err
    else:
        vision_status = "disabled"
        if not os.getenv("OPENAI_API_KEY", "").strip():
            vision_error = "OPENAI_API_KEY is not set"
        else:
            vision_error = "CHARACTER_VISION_ENABLED is off"

    character_dna = normalize_character_dna(vision_result)

    out = {
        **rule,
        "source": source,
        "vision_result": vision_result,
        "character_dna": character_dna,
        "vision_api_status": vision_status,
        "pipeline_step": "image_understanding",
        "render_mode": "parts_based_sprite",
    }
    if vision_error:
        out["vision_api_error"] = vision_error
    return out


_EYE_SIZE_SCORE = {"large": 0.88, "medium": 0.58, "small": 0.32}


def _raw_features_from_vision_attributes(attrs: dict[str, Any]) -> dict[str, Any]:
    hair = str(attrs.get("hair_style") or "bob").lower()
    hair_style = hair if hair in (
        "bob",
        "short",
        "long",
        "ponytail",
        "spiky",
        "simple",
        "bald",
        "other",
    ) else "bob"

    accessories = list(attrs.get("accessories") or [])
    if attrs.get("star_accent") and "star" not in accessories:
        accessories.append("star")

    eye_label = str(attrs.get("eye_size") or "large")
    mood = str(attrs.get("mood") or "bright_cute")
    if mood in ("bright_cute", "cute", "playful"):
        mood_key = "cute"
    elif mood == "gentle":
        mood_key = "gentle"
    else:
        mood_key = "gentle"

    from .color_utils import clamp_rgb

    accent = clamp_rgb(attrs.get("accent_color_rgb"), (85, 221, 204))
    hair_color = clamp_rgb(attrs.get("hair_color_rgb"), (42, 48, 72))
    outfit_color = clamp_rgb(attrs.get("outfit_color_rgb"), (80, 140, 220))

    return {
        "has_content": True,
        "face_shape": str(attrs.get("face_shape") or "round"),
        "hair_style": hair_style,
        "hair_color_rgb": hair_color,
        "outfit_color_rgb": outfit_color,
        "eye_spacing": str(attrs.get("eye_spacing") or "wide"),
        "bangs": bool(attrs.get("bangs", True)),
        "eye_size": _EYE_SIZE_SCORE.get(eye_label, 0.75),
        "cheeks": bool(attrs.get("cheeks", True)),
        "mood": mood_key,
        "accent_rgb": accent,
        "accessories": accessories,
        "simplicity": 0.85,
        "character_type": attrs.get("character_type"),
        "vision_enriched": True,
    }


def merge_vision_api_result(
    understanding: dict[str, Any], vision_response: dict[str, Any]
) -> dict[str, Any]:
    """Vision API 応答を image_understanding にマージ。"""
    out = {**understanding}
    out["rule_based_backup"] = {
        "source": understanding.get("source"),
        "raw_features": understanding.get("raw_features"),
        "analysis": understanding.get("analysis"),
        "detected": understanding.get("detected"),
    }
    attrs = dict(vision_response.get("attributes") or vision_response)

    raw = dict(out.get("raw_features") or {})
    raw.update(_raw_features_from_vision_attributes(attrs))
    raw["smile"] = bool(attrs.get("smile", True))
    analysis = _build_analysis(raw)
    if not analysis.get("smile_likely") and attrs.get("smile"):
        analysis["smile_likely"] = True

    out["source"] = "vision_api_merged"
    out["raw_features"] = raw
    out["analysis"] = analysis
    out["detected"] = {
        "face_shape": analysis["face_shape_detected"],
        "hair_style": analysis["hair_style_detected"],
        "bangs": analysis["bangs_detected"],
        "large_eyes": analysis["eye_size_score"] >= 0.45,
        "cheeks": analysis["cheeks_detected"],
        "smile": analysis["smile_likely"],
        "star_accent": analysis["star_detected"],
        "accent_rgb": analysis["accent_rgb"],
        "mood": analysis["mood_detected"],
        "character_type": attrs.get("character_type"),
    }
    out["vision_api_ready"] = vision_response
    out["vision_api_response"] = vision_response
    notes = list(out.get("complemented_defaults") or [])
    notes.append("vision_api_merged")
    out["complemented_defaults"] = notes
    return out
