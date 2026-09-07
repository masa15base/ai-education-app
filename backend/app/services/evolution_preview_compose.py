"""進化プレビュー用のフレーミング・ステージ装飾・ヒント文言。"""
from __future__ import annotations

from typing import Any

from PIL import Image

WHITE = (255, 255, 255)

STAGE_LABEL_JA: dict[str, str] = {
    "egg": "たまご",
    "baby": "ベビー",
    "child": "こども",
    "student": "がくせい",
    "hero": "ヒーロー",
}

STAGE_PREVIEW_BG: dict[str, tuple[int, int, int]] = {
    "egg": (255, 252, 240),
    "baby": (240, 255, 250),
    "child": (255, 248, 225),
    "student": (232, 244, 255),
    "hero": (255, 244, 210),
}

STAGE_PREVIEW_HINT_JA: dict[str, str] = {
    "egg": "たまごの姿",
    "baby": "小さな chibi の姿",
    "child": "★ が付いて元気になる",
    "student": "学生帽と本を持つ",
    "hero": "マントと王冠のヒーロー",
}


def stage_label_ja(stage: str | None) -> str:
    if not stage:
        return ""
    return STAGE_LABEL_JA.get(stage, stage)


def stage_preview_hint_ja(stage: str | None) -> str:
    if not stage:
        return ""
    return STAGE_PREVIEW_HINT_JA.get(stage, "")


def crop_to_content(img: Image.Image, *, pad: int = 2) -> Image.Image:
    """白背景スプライトをキャラ周辺でトリム。"""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            if px[x, y] != WHITE:
                xs.append(x)
                ys.append(y)
    if not xs:
        return rgb
    x0 = max(0, min(xs) - pad)
    y0 = max(0, min(ys) - pad)
    x1 = min(w - 1, max(xs) + pad)
    y1 = min(h - 1, max(ys) + pad)
    return rgb.crop((x0, y0, x1 + 1, y1 + 1))


def frame_sprite_preview(
    sprite: Image.Image,
    stage: str,
    *,
    canvas: int = 192,
    min_scale: int = 5,
) -> Image.Image:
    """
    32px スプライトをトリムして拡大し、ステージ色背景の正方形に配置。
    進化プレビューでキャラが大きく見えるようにする。
    """
    cropped = crop_to_content(sprite)
    cw, ch = cropped.size
    if cw <= 0 or ch <= 0:
        return Image.new("RGB", (canvas, canvas), STAGE_PREVIEW_BG.get(stage, WHITE))

    scale = max(min_scale, min(canvas // cw, canvas // ch))
    up = cropped.resize((cw * scale, ch * scale), Image.Resampling.NEAREST)
    bg = STAGE_PREVIEW_BG.get(stage, WHITE)
    out = Image.new("RGB", (canvas, canvas), bg)
    ox = (canvas - up.width) // 2
    oy = (canvas - up.height) // 2
    out.paste(up, (ox, oy))
    return out


def frame_sprite_display(
    sprite: Image.Image,
    stage: str,
    *,
    canvas: int = 192,
    display_size: int = 512,
) -> Image.Image:
    """メイン表示用: フレーム後に display_size へ NEAREST 拡大。"""
    framed = frame_sprite_preview(sprite, stage, canvas=canvas)
    return framed.resize((display_size, display_size), Image.Resampling.NEAREST)


def preview_meta_for_stage(stage: str | None) -> dict[str, Any]:
    return {
        "stage": stage,
        "stage_label_ja": stage_label_ja(stage),
        "preview_hint_ja": stage_preview_hint_ja(stage),
    }
