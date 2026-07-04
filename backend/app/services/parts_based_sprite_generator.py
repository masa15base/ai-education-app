"""
パーツ合成方式のファミコン風スプライト生成。
画像生成 AI は使わず、固定パーツを座標配置して組み立てる。
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .character_sprite_designer import STAGES_ORDER, next_stage_after
from .image_understanding import understand_image

DISPLAY_SIZE = 512
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"
WHITE = (255, 255, 255)

PARTS: dict[str, list[str]] = {
    "face": ["round", "oval"],
    "hair": ["short_bob", "long", "short"],
    "eyes": ["large_round", "dot"],
    "mouth": ["smile", "neutral"],
    "accessory": ["star", "ribbon", "none"],
    "body": ["baby", "child", "student", "hero"],
}

# MVP: 手描き反映の土台（Vision 後もこの locked でパーツ選択）
MVP_PARTS_DNA: dict[str, Any] = {
    "face_shape": "round",
    "hair_color": "dark_navy",
    "hair_style": "short_bob",
    "bangs": "center",
    "eye_shape": "large_round",
    "mouth": "smile",
    "cheeks": True,
    "accent_color": "mint_green",
    "accessory": "star",
    "mood": "cheerful",
}

MVP_FEATURES_JA: list[str] = [
    "ボブ風の髪",
    "大きな目",
    "ピンクのほっぺ",
    "ミントグリーンの星",
    "やさしい笑顔",
]

STAGE_CANVAS: dict[str, int] = {
    "egg": 32,
    "baby": 32,
    "child": 48,
    "student": 64,
    "hero": 64,
}

PALETTE: dict[str, tuple[int, int, int]] = {
    "outline": (34, 34, 34),
    "hair": (42, 48, 72),
    "hair_hi": (68, 74, 98),
    "skin": (255, 248, 240),
    "skin_shadow": (255, 228, 218),
    "cheek": (255, 180, 170),
    "eye_white": (255, 255, 255),
    "eye_pupil": (34, 34, 34),
    "accent": (85, 221, 204),
    "shirt": (80, 140, 220),
    "shirt_shadow": (55, 100, 180),
    "gold": (255, 210, 80),
    "cape": (220, 72, 72),
}


def _s(size: int, ratio: float) -> int:
    return max(1, int(size * ratio))


def _pal(key: str) -> tuple[int, int, int]:
    return PALETTE[key]


def resolve_parts_dna(character_dna: dict[str, Any] | None) -> dict[str, Any]:
    """
    character_dna からパーツ選択用 DNA を得る。
    MVP では locked 特徴を固定（同一キャラの安定生成）。
    """
    _ = character_dna
    return dict(MVP_PARTS_DNA)


def select_parts(parts_dna: dict[str, Any], stage: str) -> dict[str, str]:
    """DNA → パーツ ID。"""
    stage = stage if stage in STAGE_CANVAS else "baby"
    body = {
        "egg": "baby",
        "baby": "baby",
        "child": "child",
        "student": "student",
        "hero": "hero",
    }.get(stage, "child")

    face = parts_dna.get("face_shape", "round")
    if face not in PARTS["face"]:
        face = "round"

    hair = parts_dna.get("hair_style", "short_bob")
    if hair not in PARTS["hair"]:
        hair = "short_bob"

    eyes = parts_dna.get("eye_shape", "large_round")
    if eyes not in PARTS["eyes"]:
        eyes = "large_round"

    mouth = parts_dna.get("mouth", "smile")
    if mouth not in PARTS["mouth"]:
        mouth = "smile"

    accessory = parts_dna.get("accessory", "star")
    if accessory not in PARTS["accessory"]:
        accessory = "star"

    return {
        "face": face,
        "hair": hair,
        "eyes": eyes,
        "mouth": mouth,
        "accessory": accessory,
        "body": body,
        "cheeks": str(bool(parts_dna.get("cheeks", True))),
        "bangs": str(parts_dna.get("bangs", "center")),
    }


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int], scale: int = 1) -> None:
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        draw.point((cx + dx * scale, cy + dy * scale), fill=color)


def _draw_body(draw: ImageDraw.ImageDraw, size: int, body: str) -> None:
    cx = size // 2
    shirt = _pal("shirt")
    shadow = _pal("shirt_shadow")
    outline = _pal("outline")
    top = _s(size, 0.54)
    if body == "baby":
        draw.ellipse(
            (cx - _s(size, 0.14), top, cx + _s(size, 0.14), _s(size, 0.72)),
            fill=shirt,
            outline=outline,
        )
        return
    draw.ellipse(
        (cx - _s(size, 0.16), top, cx + _s(size, 0.16), _s(size, 0.76)),
        fill=shirt,
        outline=outline,
    )
    draw.rectangle(
        (cx - _s(size, 0.12), top + 2, cx + _s(size, 0.12), _s(size, 0.68)),
        fill=shadow,
    )
    if body in ("child", "student", "hero"):
        fy = size - _s(size, 0.06)
        for dx in (-_s(size, 0.14), _s(size, 0.14)):
            x = cx + dx
            draw.rectangle((x - 2, fy - 3, x + 2, fy), fill=outline)
            draw.rectangle((x - 1, fy - 5, x + 1, fy - 2), fill=shirt)
        ay = _s(size, 0.58)
        for dx in (-_s(size, 0.26), _s(size, 0.26)):
            draw.rectangle((cx + dx - 1, ay, cx + dx + 1, ay + _s(size, 0.06)), fill=shirt, outline=outline)


def _draw_face(draw: ImageDraw.ImageDraw, size: int, face: str) -> tuple[int, int, int, int]:
    cx = size // 2
    skin = _pal("skin")
    shadow = _pal("skin_shadow")
    cy = _s(size, 0.38)
    if face == "oval":
        rx, ry = _s(size, 0.20), _s(size, 0.23)
    else:
        rx, ry = _s(size, 0.22), _s(size, 0.21)
    x0, y0, x1, y1 = cx - rx, cy - ry, cx + rx, cy + ry
    draw.ellipse((x0, y0, x1, y1), fill=skin)
    draw.pieslice((x0, cy, x1, y1 + 2), 0, 180, fill=shadow)
    return x0, y0, x1, y1


def _draw_hair_back(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], hair: str) -> None:
    cx = size // 2
    hair_c = _pal("hair")
    hair_hi = _pal("hair_hi")
    _, fy0, _, fy1 = face_box
    top = _s(size, 0.06)
    head_bottom = fy1 - _s(size, 0.02)
    w = 0.33 if hair != "short" else 0.26
    draw.pieslice(
        (cx - _s(size, w), top, cx + _s(size, w), head_bottom + _s(size, 0.08)),
        200,
        340,
        fill=hair_c,
    )
    if hair != "short":
        draw.ellipse(
            (cx - _s(size, w - 0.03), top + 1, cx + _s(size, w - 0.03), fy0 + _s(size, 0.06)),
            fill=hair_c,
        )
    draw.arc(
        (cx - _s(size, 0.22), top + 2, cx - _s(size, 0.04), top + _s(size, 0.14)),
        200,
        300,
        fill=hair_hi,
    )
    if hair == "long":
        draw.rectangle(
            (cx + _s(size, 0.28), top + _s(size, 0.12), cx + _s(size, 0.34), head_bottom),
            fill=hair_c,
        )


def _draw_hair_side(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int]) -> None:
    hair_c = _pal("hair")
    hair_hi = _pal("hair_hi")
    fx0, fy0, fx1, fy1 = face_box
    for side, xb in ((-1, fx0 - _s(size, 0.04)), (1, fx1 + _s(size, 0.02))):
        x = max(1, min(size - 2, xb))
        draw.line((x, fy0 + 2, x + side * 2, fy1 - 4), fill=hair_c, width=1)
        draw.point((x, fy0 + 4), fill=hair_hi)


def _draw_hair_bangs(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], bangs: str) -> None:
    if bangs == "none":
        return
    cx = size // 2
    hair_c = _pal("hair")
    fx0, fy0, fx1, _ = face_box
    bang_top = fy0 - _s(size, 0.06)
    bang_bottom = fy0 + _s(size, 0.08)
    for bx in (cx - _s(size, 0.08), cx, cx + _s(size, 0.08)):
        if fx0 + 2 < bx < fx1 - 2:
            draw.line((bx, bang_top, bx, bang_bottom), fill=hair_c, width=1)


def _draw_eyes(
    draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], eye: str
) -> None:
    cx = size // 2
    outline = _pal("outline")
    white = _pal("eye_white")
    pupil = _pal("eye_pupil")
    accent = _pal("accent")
    _, fy0, _, fy1 = face_box
    eye_y = fy0 + (fy1 - fy0) // 3
    spacing = _s(size, 0.11)
    if eye == "dot":
        ew, eh = max(2, size // 14), max(2, size // 14)
    else:
        ew, eh = max(3, size // 9), max(4, size // 7)
    for side in (-1, 1):
        ex = cx + side * spacing
        draw.ellipse((ex - ew, eye_y - eh, ex + ew, eye_y + eh), fill=white, outline=outline)
        draw.ellipse((ex - 1, eye_y - 1, ex + 1, eye_y + 1), fill=pupil)
        if eye == "large_round":
            draw.point((ex + 1, eye_y - 1), fill=white)
            draw.point((ex + 1, eye_y - 2), fill=accent)


def _draw_cheeks(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int]) -> None:
    cheek = _pal("cheek")
    fx0, fy0, fx1, fy1 = face_box
    cy = fy0 + (fy1 - fy0) * 2 // 3
    for x in (fx0 + _s(size, 0.06), fx1 - _s(size, 0.06)):
        draw.ellipse((x - 2, cy - 1, x + 2, cy + 2), fill=cheek)


def _draw_mouth(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], mouth: str) -> None:
    cx = size // 2
    outline = _pal("outline")
    _, fy0, _, fy1 = face_box
    mouth_y = fy0 + (fy1 - fy0) * 3 // 4
    if mouth == "neutral":
        draw.point((cx, mouth_y), fill=outline)
    else:
        draw.arc((cx - 4, mouth_y - 2, cx + 4, mouth_y + 3), 0, 180, fill=outline, width=1)


def _draw_accessory(
    draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], accessory: str, stage: str
) -> None:
    if accessory == "none":
        return
    accent = _pal("accent")
    cx = size // 2
    fx0, fy0, _, _ = face_box
    if accessory == "ribbon":
        by = fy0 - _s(size, 0.04)
        draw.ellipse((cx - 4, by - 2, cx - 1, by + 2), fill=accent)
        draw.ellipse((cx + 1, by - 2, cx + 4, by + 2), fill=accent)
        return
    if accessory == "star":
        if stage == "baby":
            _draw_star(draw, cx - _s(size, 0.14), fy0 - _s(size, 0.10), accent, 1)
        else:
            _draw_star(draw, fx0 - _s(size, 0.06), fy0 + _s(size, 0.04), accent, 1)


def _draw_stage_decoration(draw: ImageDraw.ImageDraw, size: int, face_box: tuple[int, int, int, int], body: str) -> None:
    cx = size // 2
    fx0, fy0, _, fy1 = face_box
    accent = _pal("accent")
    gold = _pal("gold")
    cape = _pal("cape")
    outline = _pal("outline")
    shirt = _pal("shirt")

    if body == "child":
        _draw_star(draw, fx0 - _s(size, 0.06), fy0 + _s(size, 0.04), accent, 1)

    elif body == "student":
        hy = max(1, _s(size, 0.10))
        draw.rectangle((cx - 8, hy, cx + 8, hy + 3), fill=shirt)
        draw.rectangle((cx + 7, _s(size, 0.56), cx + 11, _s(size, 0.64)), fill=(220, 72, 72), outline=outline)
        _draw_star(draw, cx + 6, hy - 2, accent, 1)

    elif body == "hero":
        for x in range(cx - 3, cx + 4):
            draw.point((x, 2), fill=gold)
        for y in range(_s(size, 0.34), _s(size, 0.76)):
            draw.point((1, y), fill=cape)
            draw.point((size - 2, y), fill=cape)
        wx = min(size - 3, cx + _s(size, 0.24))
        for y in range(_s(size, 0.36), _s(size, 0.66)):
            draw.point((wx, y), fill=gold)
        _draw_star(draw, wx, _s(size, 0.34), accent, 1)
        draw.ellipse((cx - 2, _s(size, 0.50), cx + 2, _s(size, 0.54)), fill=gold)


def _apply_outline(img: Image.Image) -> Image.Image:
    outline = _pal("outline")
    src = img.convert("RGB")
    w, h = src.size
    px = src.load()
    out = src.copy()
    opx = out.load()

    def is_bg(r: int, g: int, b: int) -> bool:
        return r > 235 and g > 235 and b > 235

    for y in range(h):
        for x in range(w):
            if not is_bg(*px[x, y]):
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not is_bg(*px[nx, ny]):
                    opx[x, y] = outline
                    break
    return out


def compose_parts_sprite(parts_dna: dict[str, Any], stage: str) -> Image.Image:
    """
    パーツを固定順で配置したスプライト（32/48/64px）。
    """
    stage = stage if stage in STAGE_CANVAS else "baby"
    size = STAGE_CANVAS[stage]
    selected = select_parts(parts_dna, stage)

    canvas = Image.new("RGB", (size, size), WHITE)
    draw = ImageDraw.Draw(canvas)

    _draw_body(draw, size, selected["body"])
    face_box = _draw_face(draw, size, selected["face"])
    _draw_hair_back(draw, size, face_box, selected["hair"])
    _draw_hair_side(draw, size, face_box)
    _draw_hair_bangs(draw, size, face_box, selected["bangs"])
    _draw_eyes(draw, size, face_box, selected["eyes"])
    if selected.get("cheeks") == "True" or parts_dna.get("cheeks", True):
        _draw_cheeks(draw, size, face_box)
    _draw_mouth(draw, size, face_box, selected["mouth"])
    _draw_accessory(draw, size, face_box, selected["accessory"], stage)
    _draw_stage_decoration(draw, size, face_box, selected["body"])

    return _apply_outline(canvas)


def upscale_sprite(sprite: Image.Image, display_size: int = DISPLAY_SIZE) -> Image.Image:
    """Nearest Neighbor で 512px に拡大。"""
    return sprite.resize((display_size, display_size), Image.Resampling.NEAREST)


def _dna_from_understanding(image_understanding: dict[str, Any]) -> dict[str, Any]:
    if "character_dna" in image_understanding:
        return image_understanding["character_dna"]
    from .character_dna import normalize_character_dna, rule_based_to_vision_result

    raw = image_understanding.get("raw_features") or {}
    analysis = image_understanding.get("analysis") or {}
    return normalize_character_dna(rule_based_to_vision_result(raw, analysis))


def generate_parts_evolution_bundle(
    image_understanding: dict[str, Any],
    *,
    stage_key: str,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
    force_egg: bool = False,
) -> dict[str, Any]:
    """パーツ合成で current / next / hero を生成。"""
    _ = character_profile
    if force_egg:
        stage_key = "egg"
    else:
        stage_key = stage_key if stage_key in STAGES_ORDER else "baby"
        if stage_key == "egg":
            stage_key = "baby"

    full_dna = _dna_from_understanding(image_understanding)
    parts_dna = resolve_parts_dna(full_dna)

    current_sprite = compose_parts_sprite(parts_dna, stage_key)
    current_display = upscale_sprite(current_sprite)

    nxt = next_stage_after(stage_key)
    next_display = None
    if nxt and nxt != "egg":
        next_display = upscale_sprite(compose_parts_sprite(parts_dna, nxt))

    hero_display = upscale_sprite(compose_parts_sprite(parts_dna, "hero"))

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"parts_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")
        hero_display.save(dest / f"parts_hero_{tag}.png", format="PNG")
        if next_display is not None and nxt:
            next_display.save(dest / f"parts_{nxt}_{tag}.png", format="PNG")

    features_ja = MVP_FEATURES_JA
    sprite_size = STAGE_CANVAS.get(stage_key, 32)

    meta: dict[str, Any] = {
        "stage": stage_key,
        "generation_mode": "parts_based_sprite",
        "render_mode": "parts_based_sprite",
        "pipeline": [
            "vision_result_extraction",
            "normalize_character_dna",
            "parts_selection",
            "fixed_coordinate_compose",
            "nearest_upscale_512",
        ],
        "image_understanding": image_understanding,
        "vision_result": image_understanding.get("vision_result"),
        "character_dna": full_dna,
        "parts_dna": parts_dna,
        "selected_parts": select_parts(parts_dna, stage_key),
        "signature_features_ja": features_ja,
        "sprite_size": sprite_size,
        "display_size": DISPLAY_SIZE,
        "saved_path": saved_path,
        "parts_catalog": PARTS,
        "next_stage": nxt,
    }

    return {
        "image_understanding": image_understanding,
        "character_dna": full_dna,
        "parts_dna": parts_dna,
        "current_sprite": current_sprite,
        "current_display": current_display,
        "next_stage_preview": next_display,
        "final_hero_preview": hero_display,
        "current_stage_image": current_display,
        "meta": meta,
        "saved_path": saved_path,
    }


def _resolve_stage(stage: str | None, learning_level: int) -> str:
    if stage == "adult":
        stage = "hero"
    if stage in STAGE_CANVAS:
        return stage
    lv = max(1, int(learning_level))
    if lv <= 4:
        return "baby"
    if lv <= 10:
        return "child"
    if lv <= 20:
        return "student"
    return "hero"


def generate_parts_bundle_from_bytes(
    image_bytes: bytes,
    *,
    character_profile: dict | None = None,
    stage: str | None = None,
    learning_level: int = 1,
    output_dir: str | Path | None = None,
    save_file: bool = True,
) -> dict[str, Any]:
    understanding = understand_image(image_bytes)
    force_egg = stage == "egg"
    stage_key = "egg" if force_egg else _resolve_stage(stage, learning_level)
    if stage_key == "egg" and not force_egg:
        stage_key = "baby"
    return generate_parts_evolution_bundle(
        understanding,
        stage_key=stage_key,
        character_profile=character_profile,
        save_file=save_file,
        output_dir=output_dir,
        force_egg=force_egg,
    )
