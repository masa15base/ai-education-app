"""ファミコン風キャラ生成用プロンプト（Replicate 等の画像 AI 向け）。"""
from __future__ import annotations

FAMICOM_STYLE_TAGS: tuple[str, ...] = (
    "Japanese retro Famicom style pixel art",
    "8-bit video game character",
    "limited color palette",
    "low resolution sprite",
    "cute educational mascot",
    "full body front view",
    "simple white background",
    "thick pixel outline",
    "no realistic texture",
    "no 3D",
    "no anime illustration",
    "no detailed background",
)

STAGE_PROMPT_HINTS: dict[str, str] = {
    "baby": "tiny round 32x32 sprite, minimal detail, 3 colors, no accessories",
    "child": "48x48 sprite, cheerful face, simple arms and legs, 4 colors",
    "student": "64x64 sprite, school hat or book or pencil, 5 colors, bright",
    "hero": "64x64 sprite, crown cape gold wand, achievement mascot, 6-7 colors",
    "adult": "64x64 sprite, crown cape gold wand, achievement mascot, 6-7 colors",
}


def build_famicom_character_prompt(
    base: str = "",
    *,
    stage: str = "child",
    display_name: str | None = None,
) -> str:
    """画像生成 AI に渡すプロンプト文字列を組み立てる。"""
    parts: list[str] = list(FAMICOM_STYLE_TAGS)
    hint = STAGE_PROMPT_HINTS.get(stage, STAGE_PROMPT_HINTS["child"])
    parts.append(hint)
    if display_name:
        parts.append(f"mascot inspired by hand-drawn character named {display_name}")
    if base.strip():
        parts.insert(0, base.strip())
    return ", ".join(parts)


def build_negative_prompt() -> str:
    return (
        "realistic, photo, 3d render, smooth gradient, high resolution detail, "
        "anime screenshot, watercolor, blurry, text watermark, complex background"
    )
