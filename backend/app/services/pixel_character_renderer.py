"""
character_design_spec → ファミコン風ドットキャラの手続き描画。
描画順: 体 → 顔 → 髪 → 前髪 → 横髪 → 目 → ハイライト → ほっぺ → 口 → アクセント → 星 → ステージ装飾
"""
from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

WHITE_RGB: tuple[int, int, int] = (255, 255, 255)


def _pal(spec: dict[str, Any], key: str) -> tuple[int, int, int]:
    palette = spec.get("palette") or {}
    return tuple(palette.get(key, (34, 34, 34)))


def _scale(sprite: int, ratio: float) -> int:
    return max(1, int(sprite * ratio))


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int], size: int = 2) -> None:
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1)):
        x, y = cx + dx * size // 2, cy + dy * size // 2
        draw.point((x, y), fill=color)


def _apply_outline(img: Image.Image, outline: tuple[int, int, int]) -> Image.Image:
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


def _draw_body(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int) -> None:
    shirt = _pal(spec, "shirt")
    shadow = _pal(spec, "shirt_shadow")
    outline = _pal(spec, "outline")
    top = _scale(sprite, 0.54)
    draw.ellipse(
        (cx - _scale(sprite, 0.17), top, cx + _scale(sprite, 0.17), _scale(sprite, 0.78)),
        fill=shirt,
        outline=outline,
    )
    draw.rectangle(
        (cx - _scale(sprite, 0.13), top + 3, cx + _scale(sprite, 0.13), _scale(sprite, 0.72)),
        fill=shadow,
    )
    if spec.get("limbs"):
        fy = sprite - 4
        for dx in (-5, 5):
            x = cx + dx
            draw.rectangle((x - 2, fy - 3, x + 2, fy), fill=outline)
            draw.rectangle((x - 1, fy - 5, x + 1, fy - 2), fill=shirt)
        ay = _scale(sprite, 0.58)
        for dx in (-9, 9):
            draw.rectangle((cx + dx - 1, ay, cx + dx + 1, ay + 4), fill=shirt, outline=outline)


def _draw_face(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int) -> tuple[int, int, int, int]:
    """顔（肌）を大きめに。戻り値: face box (x0,y0,x1,y1)"""
    skin = _pal(spec, "skin")
    shadow = _pal(spec, "skin_shadow")
    cy = _scale(sprite, 0.38)
    face_shape = spec.get("face_shape", "round")
    if face_shape == "wide":
        rx, ry = _scale(sprite, 0.24), _scale(sprite, 0.19)
    elif face_shape == "oval":
        rx, ry = _scale(sprite, 0.20), _scale(sprite, 0.23)
    else:
        rx, ry = _scale(sprite, 0.22), _scale(sprite, 0.21)
    x0, y0, x1, y1 = cx - rx, cy - ry, cx + rx, cy + ry
    draw.ellipse((x0, y0, x1, y1), fill=skin)
    draw.pieslice((x0, cy, x1, y1 + 2), 0, 180, fill=shadow)
    return x0, y0, x1, y1


def _draw_hair_back_and_outline(
    draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]
) -> None:
    """丸いボブの外形（顔の後ろ・横）。黒塊にしない。"""
    hair = _pal(spec, "hair")
    hair_hi = _pal(spec, "hair_hi")
    _, fy0, _, fy1 = face_box
    top = _scale(sprite, 0.06)
    head_bottom = fy1 - _scale(sprite, 0.02)

    hair_style = spec.get("hair", {}).get("style", "short_bob")
    if hair_style == "ponytail":
        draw.rectangle(
            (cx + _scale(sprite, 0.28), top + _scale(sprite, 0.12), cx + _scale(sprite, 0.34), head_bottom),
            fill=hair,
        )

    hair_w = 0.33 if hair_style != "simple" else 0.26
    if hair_style == "spiky":
        for i, ox in enumerate((-0.20, -0.08, 0.06, 0.18)):
            tx = cx + _scale(sprite, ox)
            ty = top + _scale(sprite, 0.02)
            draw.polygon(
                [(tx, ty + _scale(sprite, 0.14)), (tx - 2, ty), (tx + 2, ty)],
                fill=hair,
            )

    # 後ろの丸いボブ / シンプル髪
    draw.pieslice(
        (cx - _scale(sprite, hair_w), top, cx + _scale(sprite, hair_w), head_bottom + _scale(sprite, 0.08)),
        200,
        340,
        fill=hair,
    )
    if hair_style != "simple":
        draw.ellipse(
            (cx - _scale(sprite, hair_w - 0.03), top + 1, cx + _scale(sprite, hair_w - 0.03), fy0 + _scale(sprite, 0.06)),
            fill=hair,
        )
    # ハイライト（髪の明部）
    draw.arc(
        (cx - _scale(sprite, 0.22), top + 2, cx - _scale(sprite, 0.04), top + _scale(sprite, 0.14)),
        200,
        300,
        fill=hair_hi,
    )


def _draw_bangs(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    """前髪3本 — 顔を隠しすぎない。"""
    hair = _pal(spec, "hair")
    fx0, fy0, fx1, _ = face_box
    bangs_type = spec.get("hair", {}).get("bangs", "center_long_bangs")
    if bangs_type == "none":
        return
    bang_top = fy0 - _scale(sprite, 0.06)
    bang_bottom = fy0 + _scale(sprite, 0.08)
    positions = [cx - _scale(sprite, 0.08), cx, cx + _scale(sprite, 0.08)]
    for bx in positions:
        if bx < fx0 + 2 or bx > fx1 - 2:
            continue
        draw.line((bx, bang_top, bx, bang_bottom), fill=hair, width=1)
        draw.point((bx, bang_bottom), fill=hair)


def _draw_side_hair(
    draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]
) -> None:
    if not spec.get("hair", {}).get("side_hair", True):
        return
    hair = _pal(spec, "hair")
    hair_hi = _pal(spec, "hair_hi")
    fx0, fy0, fx1, fy1 = face_box
    for side, x_base in ((-1, fx0 - _scale(sprite, 0.04)), (1, fx1 + _scale(sprite, 0.02))):
        x = max(1, min(sprite - 2, x_base))
        draw.line((x, fy0 + 2, x + side * 2, fy1 - 4), fill=hair, width=1)
        draw.point((x, fy0 + 4), fill=hair_hi)


def _draw_ears(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    if not spec.get("ears", {}).get("visible", True):
        return
    skin = _pal(spec, "skin")
    outline = _pal(spec, "outline")
    fx0, fy0, fx1, fy1 = face_box
    ear_y = fy0 + _scale(sprite, 0.12)
    for x in (fx0 - 2, fx1 + 1):
        if 0 <= x < sprite:
            draw.point((x, ear_y), fill=outline)
            draw.point((x, ear_y + 1), fill=skin)


def _draw_eyes(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    outline = _pal(spec, "outline")
    white = _pal(spec, "eye_white")
    pupil = _pal(spec, "eye_pupil")
    accent = _pal(spec, "accent")
    _, fy0, _, fy1 = face_box
    eye_y = fy0 + (fy1 - fy0) // 3
    spacing_key = spec.get("eyes", {}).get("spacing", "wide")
    spacing_ratio = {"wide": 0.12, "normal": 0.10, "close": 0.08}.get(spacing_key, 0.11)
    spacing = _scale(sprite, spacing_ratio)
    eye_type = spec.get("eyes", {}).get("type", "large_round")

    if eye_type == "large_round":
        ew, eh = max(3, sprite // 9), max(4, sprite // 7)
    else:
        ew, eh = max(2, sprite // 12), max(3, sprite // 9)

    for side in (-1, 1):
        ex = cx + side * spacing
        draw.ellipse((ex - ew, eye_y - eh, ex + ew, eye_y + eh), fill=white, outline=outline)
        draw.ellipse((ex - 1, eye_y - 1, ex + 1, eye_y + 1), fill=pupil)
        if spec.get("eyes", {}).get("highlight", True):
            draw.point((ex + 1, eye_y - 1), fill=white)
            draw.point((ex + 1, eye_y - 2), fill=accent)


def _draw_cheeks(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    if not spec.get("cheeks", {}).get("enabled", True):
        return
    cheek = _pal(spec, "cheek")
    fx0, fy0, fx1, fy1 = face_box
    cy = fy0 + (fy1 - fy0) * 2 // 3
    for x in (fx0 + _scale(sprite, 0.06), fx1 - _scale(sprite, 0.06)):
        draw.ellipse((x - 2, cy - 1, x + 2, cy + 2), fill=cheek)


def _draw_mouth(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    outline = _pal(spec, "outline")
    _, fy0, _, fy1 = face_box
    mouth_y = fy0 + (fy1 - fy0) * 3 // 4
    mouth_type = spec.get("mouth", {}).get("type", "gentle_smile")
    if mouth_type == "gentle_smile":
        draw.arc((cx - 4, mouth_y - 2, cx + 4, mouth_y + 3), 0, 180, fill=outline, width=1)
    else:
        draw.point((cx, mouth_y), fill=outline)


def _draw_bow(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    if not spec.get("accessories", {}).get("bow"):
        return
    accent = _pal(spec, "accent")
    fx0, fy0, _, _ = face_box
    by = fy0 - _scale(sprite, 0.04)
    draw.ellipse((cx - 4, by - 2, cx - 1, by + 2), fill=accent)
    draw.ellipse((cx + 1, by - 2, cx + 4, by + 2), fill=accent)
    draw.point((cx, by), fill=_pal(spec, "outline"))


def _draw_glasses(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    if not spec.get("accessories", {}).get("glasses"):
        return
    outline = _pal(spec, "outline")
    _, fy0, _, fy1 = face_box
    eye_y = fy0 + (fy1 - fy0) // 3
    spacing_key = spec.get("eyes", {}).get("spacing", "wide")
    spacing_ratio = {"wide": 0.12, "normal": 0.10, "close": 0.08}.get(spacing_key, 0.11)
    spacing = _scale(sprite, spacing_ratio)
    for side in (-1, 1):
        ex = cx + side * spacing
        draw.ellipse((ex - 3, eye_y - 3, ex + 3, eye_y + 3), outline=outline, width=1)
    draw.line((cx - spacing + 3, eye_y, cx + spacing - 3, eye_y), fill=outline, width=1)


def _draw_signature_star(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    if not spec.get("accessories", {}).get("star", True):
        return
    accent = _pal(spec, "accent")
    placement = spec.get("star_placement", "hair_ornament")
    fx0, fy0, _, _ = face_box

    if placement == "above_head":
        _draw_star(draw, cx - _scale(sprite, 0.14), fy0 - _scale(sprite, 0.10), accent, 2)
    elif placement == "hair_ornament":
        _draw_star(draw, fx0 - _scale(sprite, 0.06), fy0 + _scale(sprite, 0.04), accent, 2)
    elif placement == "hat_or_bag":
        _draw_star(draw, cx + _scale(sprite, 0.20), _scale(sprite, 0.12), accent, 2)
    elif placement == "wand_or_badge":
        _draw_star(draw, min(sprite - 4, cx + _scale(sprite, 0.22)), _scale(sprite, 0.40), accent, 2)
        _draw_star(draw, cx - _scale(sprite, 0.12), fy0 - _scale(sprite, 0.08), accent, 1)
    else:
        _draw_star(draw, fx0 - _scale(sprite, 0.08), fy0 + 2, accent, 2)


def _draw_stage_decor(draw: ImageDraw.ImageDraw, spec: dict[str, Any], sprite: int, cx: int, face_box: tuple[int, int, int, int]) -> None:
    decor = spec.get("stage_decor", "light")
    gold = _pal(spec, "gold")
    cape = _pal(spec, "cape")
    accent = _pal(spec, "accent")
    outline = _pal(spec, "outline")
    glow = _pal(spec, "glow")
    _, fy0, _, _ = face_box

    if decor == "study":
        hy = max(1, _scale(sprite, 0.10))
        draw.rectangle((cx - 8, hy, cx + 8, hy + 3), fill=_pal(spec, "shirt"))
        draw.rectangle((cx + 7, _scale(sprite, 0.56), cx + 11, _scale(sprite, 0.64)), fill=(220, 72, 72), outline=outline)
        draw.line((cx - 10, _scale(sprite, 0.56), cx - 10, _scale(sprite, 0.64)), fill=accent, width=1)
        _draw_star(draw, cx + 6, hy - 2, accent, 1)

    elif decor == "hero":
        # 王冠（顔の上・小さめ）
        for x in range(cx - 3, cx + 4):
            draw.point((x, 2), fill=gold)
        # マント（顔の外側のみ）
        for y in range(_scale(sprite, 0.34), _scale(sprite, 0.76)):
            draw.point((1, y), fill=cape)
            draw.point((sprite - 2, y), fill=cape)
        # 杖 + 星
        wx = min(sprite - 3, cx + _scale(sprite, 0.24))
        for y in range(_scale(sprite, 0.36), _scale(sprite, 0.66)):
            draw.point((wx, y), fill=gold)
        _draw_star(draw, wx, _scale(sprite, 0.34), accent, 2)
        # バッジ
        draw.ellipse((cx - 2, _scale(sprite, 0.50), cx + 2, _scale(sprite, 0.54)), fill=gold)
        draw.point((cx - 1, 3), fill=glow)
        # 顔周りの星は維持
        _draw_star(draw, cx - _scale(sprite, 0.14), fy0 - _scale(sprite, 0.06), accent, 1)


def render_sprite_from_spec(spec: dict[str, Any], sprite: int) -> Image.Image:
    """キャラクター設計書からドットキャラを描画。"""
    canvas = Image.new("RGB", (sprite, sprite), WHITE_RGB)
    draw = ImageDraw.Draw(canvas)
    cx = sprite // 2

    # 指定順序で描画
    _draw_body(draw, spec, sprite, cx)
    face_box = _draw_face(draw, spec, sprite, cx)
    _draw_hair_back_and_outline(draw, spec, sprite, cx, face_box)
    _draw_bangs(draw, spec, sprite, cx, face_box)
    _draw_side_hair(draw, spec, sprite, cx, face_box)
    _draw_ears(draw, spec, sprite, cx, face_box)
    _draw_eyes(draw, spec, sprite, cx, face_box)
    _draw_glasses(draw, spec, sprite, cx, face_box)
    _draw_cheeks(draw, spec, sprite, cx, face_box)
    _draw_mouth(draw, spec, sprite, cx, face_box)
    _draw_bow(draw, spec, sprite, cx, face_box)
    _draw_signature_star(draw, spec, sprite, cx, face_box)
    _draw_stage_decor(draw, spec, sprite, cx, face_box)

    return _apply_outline(canvas, _pal(spec, "outline"))


def render_sprite_from_design(design: dict[str, Any], sprite: int) -> Image.Image:
    """後方互換: design に spec があればそれを使う。"""
    if design.get("character_type") or design.get("hair", {}).get("style"):
        return render_sprite_from_spec(design, sprite)
    # 旧形式フォールバック
    from .character_design_spec import DEFAULT_CUTE_GIRL, build_character_design_spec

    spec = build_character_design_spec({}, stage=design.get("stage", "baby"))
    spec["palette"] = design.get("palette") or spec["palette"]
    spec["stage"] = design.get("stage", "baby")
    spec["limbs"] = design.get("limbs", False)
    spec["stage_decor"] = design.get("decor", "light")
    return render_sprite_from_spec(spec, sprite)
