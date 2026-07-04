"""
手書き画像 → 少女ファミコン風ドットキャラ生成（固定 spec 版）。

添付仕様書「少女 ファミコン風」準拠:
- 32×32 キャンバス、中央に小さな全身 NPC（高さ 24〜26px）
- 8色パレット、1px 黒アウトライン、白背景
- Nearest Neighbor で 512×512 プレビュー
- Vision / 自動特徴抽出 / 進化は当面停止
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from .famicom_sprite_common import (
    BLACK,
    DISPLAY_SIZE,
    WHITE,
    add_exterior_outline,
    upscale_nearest,
)

GENERATION_MODE = "famicom_sprite_spec"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"
SPRITE_SIZE = 32

# キャラ配置ガイド（32×32 内・添付仕様）
CHAR_X0, CHAR_X1 = 7, 24
CHAR_Y0, CHAR_Y1 = 4, 29
HEAD_Y0, HEAD_Y1 = 4, 16
FACE_X0, FACE_X1 = 11, 20
FACE_Y0, FACE_Y1 = 8, 16
BODY_X0, BODY_X1 = 10, 22
BODY_Y0, BODY_Y1 = 17, 25
LEGS_X0, LEGS_X1 = 11, 21
LEGS_Y0, LEGS_Y1 = 25, 29

# 添付仕様の 8 色パレット（#000000 〜 #4EDCB0）
COLOR_BY_NAME: dict[str, tuple[int, int, int]] = {
    "black": BLACK,
    "white": WHITE,
    "dark_navy": (0x1E, 0x21, 0x40),
    "blue": (0x2B, 0x7B, 0xFF),
    "orange": (0xE1, 0x64, 0x0A),
    "grey": (0x80, 0x80, 0x80),
    "skin": (0xF4, 0xD8, 0xC0),
    "cheek_pink": (0xFF, 0xB6, 0xB6),
    "mint_green": (0x4E, 0xDC, 0xB0),
    "brown": (0x8B, 0x5A, 0x2B),
}

NPC_PALETTE_8: tuple[tuple[int, int, int], ...] = (
    BLACK,
    COLOR_BY_NAME["dark_navy"],
    COLOR_BY_NAME["blue"],
    COLOR_BY_NAME["orange"],
    COLOR_BY_NAME["grey"],
    COLOR_BY_NAME["skin"],
    COLOR_BY_NAME["cheek_pink"],
    COLOR_BY_NAME["mint_green"],
)

# MVP 固定 spec（自動推定なし）
FIXED_MVP_CHARACTER_SPEC: dict[str, Any] = {
    "gender": "girl",
    "hair_style": "short_bob",
    "hair_color": "dark_navy",
    "bangs": "straight",
    "face_shape": "round",
    "eye_style": "dot",
    "mouth": "none",
    "cheeks": True,
    "accessory": "mint_green_star",
    "top_color": "blue",
    "ribbon_color": "orange",
    "skirt_color": "grey",
    "shoe_color": "brown",
}

FEATURES_JA: list[str] = [
    "小さな全身スプライト（24〜26px）",
    "濃紺ショートボブ",
    "ドット目・ピンクほっぺ",
    "ミントグリーンの十字星",
    "青トップス・オレンジリボン",
    "グレースカート・茶色の靴",
]


@dataclass(frozen=True)
class SpriteSpec:
    gender: str
    hair_style: str
    hair_rgb: tuple[int, int, int]
    bangs: str
    face_shape: str
    eye_style: str
    mouth: str
    cheeks: bool
    accessory: str
    accent_rgb: tuple[int, int, int]
    top_rgb: tuple[int, int, int]
    ribbon_rgb: tuple[int, int, int]
    skirt_rgb: tuple[int, int, int]
    shoe_rgb: tuple[int, int, int]
    skin_rgb: tuple[int, int, int]
    cheek_rgb: tuple[int, int, int]


@dataclass
class SpriteValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _normalize_accessory(raw: str) -> str:
    if raw in ("star", "mint_green_star", "mint_green", "cross"):
        return "mint_green_star"
    return raw


def build_sprite_spec(character_spec: dict[str, Any] | None = None) -> SpriteSpec:
    spec = {**FIXED_MVP_CHARACTER_SPEC, **(character_spec or {})}
    return SpriteSpec(
        gender=str(spec["gender"]),
        hair_style=str(spec["hair_style"]),
        hair_rgb=COLOR_BY_NAME[str(spec["hair_color"])],
        bangs=str(spec.get("bangs", "straight")),
        face_shape=str(spec["face_shape"]),
        eye_style=str(spec["eye_style"]),
        mouth=str(spec.get("mouth", "none")),
        cheeks=bool(spec.get("cheeks", True)),
        accessory=_normalize_accessory(str(spec.get("accessory", "mint_green_star"))),
        accent_rgb=COLOR_BY_NAME["mint_green"],
        top_rgb=COLOR_BY_NAME[str(spec.get("top_color", spec.get("outfit_color", "blue")))],
        ribbon_rgb=COLOR_BY_NAME[str(spec.get("ribbon_color", "orange"))],
        skirt_rgb=COLOR_BY_NAME[str(spec.get("skirt_color", "grey"))],
        shoe_rgb=COLOR_BY_NAME[str(spec.get("shoe_color", "brown"))],
        skin_rgb=COLOR_BY_NAME["skin"],
        cheek_rgb=COLOR_BY_NAME["cheek_pink"],
    )


def _px(img: Image.Image, x: int, y: int, c: tuple[int, int, int]) -> None:
    if 0 <= x < SPRITE_SIZE and 0 <= y < SPRITE_SIZE:
        img.putpixel((x, y), c)


def _count_color(img: Image.Image, color: tuple[int, int, int]) -> int:
    px = img.load()
    w, h = img.size
    return sum(1 for y in range(h) for x in range(w) if px[x, y] == color)


def _region_color_count(
    img: Image.Image,
    color: tuple[int, int, int],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> int:
    return sum(
        1
        for y in range(y0, y1 + 1)
        for x in range(x0, x1 + 1)
        if img.getpixel((x, y)) == color
    )


def validate_fixed_girl_sprite(img: Image.Image, spec: SpriteSpec) -> SpriteValidationResult:
    issues: list[str] = []
    if img.size != (32, 32):
        issues.append("sprite must be 32x32")

    navy = COLOR_BY_NAME["dark_navy"]
    mint = COLOR_BY_NAME["mint_green"]
    cheek = COLOR_BY_NAME["cheek_pink"]
    blue = COLOR_BY_NAME["blue"]
    orange = COLOR_BY_NAME["orange"]
    grey = COLOR_BY_NAME["grey"]
    brown = COLOR_BY_NAME["brown"]
    skin = COLOR_BY_NAME["skin"]

    navy_n = _count_color(img, navy)
    mint_n = _count_color(img, mint)
    cheek_n = _count_color(img, cheek)
    blue_n = _count_color(img, blue)
    orange_n = _count_color(img, orange)
    grey_n = _count_color(img, grey)
    brown_n = _count_color(img, brown)
    skin_n = _count_color(img, skin)

    head_navy = _region_color_count(img, navy, 8, HEAD_Y0, 23, HEAD_Y1)
    face_skin = _region_color_count(img, skin, FACE_X0, FACE_Y0, FACE_X1, FACE_Y1)
    top_blue = _region_color_count(img, blue, BODY_X0, 17, BODY_X1, 21)
    skirt_grey = _region_color_count(img, grey, BODY_X0, 22, BODY_X1, 25)

    left_eye = sum(
        1 for y in range(10, 13) for x in (13, 14) if img.getpixel((x, y)) == BLACK
    )
    right_eye = sum(
        1 for y in range(10, 13) for x in (17, 18) if img.getpixel((x, y)) == BLACK
    )

    top_margin_white = sum(
        1 for y in range(0, 4) for x in range(32) if img.getpixel((x, y)) == WHITE
    )
    char_pixels = sum(
        1
        for y in range(CHAR_Y0, CHAR_Y1 + 1)
        for x in range(CHAR_X0, CHAR_X1 + 1)
        if img.getpixel((x, y)) not in (WHITE, BLACK)
    )
    bbox_area = (CHAR_X1 - CHAR_X0 + 1) * (CHAR_Y1 - CHAR_Y0 + 1)
    fill_ratio = char_pixels / bbox_area

    metrics = {
        "dark_navy_pixels": navy_n,
        "head_navy_pixels": head_navy,
        "mint_pixels": mint_n,
        "cheek_pixels": cheek_n,
        "top_blue_pixels": blue_n,
        "ribbon_orange_pixels": orange_n,
        "skirt_grey_pixels": grey_n,
        "shoe_brown_pixels": brown_n,
        "skin_pixels": skin_n,
        "face_skin_pixels": face_skin,
        "top_body_blue_pixels": top_blue,
        "skirt_body_grey_pixels": skirt_grey,
        "left_eye_pixels": left_eye,
        "right_eye_pixels": right_eye,
        "top_margin_white_pixels": top_margin_white,
        "character_pixels": char_pixels,
        "bbox_fill_ratio": round(fill_ratio, 3),
    }

    if img.getpixel((0, 0)) != WHITE or img.getpixel((31, 31)) != WHITE:
        issues.append("background must be white")
    if top_margin_white < 100:
        issues.append("hair fills canvas too much (top margin)")
    if fill_ratio > 0.58:
        issues.append("character fills bbox too much (face icon risk)")
    if head_navy < 30 or head_navy > 120:
        issues.append("head hair size out of npc range")
    if face_skin < 6 or face_skin > 36:
        issues.append("face size out of npc range")
    if left_eye < 1 or right_eye < 1:
        issues.append("dot eyes missing")
    if left_eye > 4 or right_eye > 4:
        issues.append("eyes too large (not dot style)")
    if spec.cheeks and cheek_n < 2:
        issues.append("pink cheeks missing")
    if spec.accessory == "mint_green_star" and mint_n < 3:
        issues.append("mint green star accessory missing")
    if top_blue < 12:
        issues.append("blue top missing")
    if orange_n < 2:
        issues.append("orange ribbon missing")
    if skirt_grey < 12:
        issues.append("grey skirt missing")
    if brown_n < 4:
        issues.append("brown shoes missing")

    return SpriteValidationResult(passed=len(issues) == 0, issues=issues, metrics=metrics)


def _draw_cross_star(img: Image.Image, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    """髪右上のミントグリーン十字（+）アクセサリ。"""
    for dx, dy in ((0, 0), (0, -1), (-1, 0), (1, 0), (0, 1)):
        _px(img, cx + dx, cy + dy, color)


def _draw_hair_back(img: Image.Image, spec: SpriteSpec) -> None:
    """頭 y4-15・濃紺ショートボブ（後ろ髪）。"""
    hc = spec.hair_rgb
    for x in range(10, 22):
        _px(img, x, 4, hc)
    for x in range(9, 23):
        _px(img, x, 5, hc)
    for x in range(8, 24):
        _px(img, x, 6, hc)
        _px(img, x, 7, hc)
    for y in range(8, 15):
        _px(img, 8, y, hc)
        _px(img, 9, y, hc)
        _px(img, 22, y, hc)
        _px(img, 23, y, hc)
    for x in range(10, 22):
        _px(img, x, 14, hc)
    for x in range(11, 21):
        _px(img, x, 15, hc)


def _draw_face(img: Image.Image, spec: SpriteSpec) -> None:
    """顔 y10-14・小さな丸顔（肌色）。"""
    sk = spec.skin_rgb
    for y, x0, x1 in (
        (10, 12, 19),
        (11, 12, 19),
        (12, 12, 19),
        (13, 12, 19),
        (14, 13, 18),
    ):
        for x in range(x0, x1 + 1):
            _px(img, x, y, sk)


def _draw_hair_front(img: Image.Image, spec: SpriteSpec) -> None:
    """前髪（目を隠さない直線バング）。"""
    hc = spec.hair_rgb
    for x in range(11, 21):
        _px(img, x, 8, hc)
    for x in (12, 13, 18, 19):
        _px(img, x, 9, hc)


def _draw_dot_eyes(img: Image.Image) -> None:
    """黒の縦 2px ドット目。"""
    _px(img, 13, 11, BLACK)
    _px(img, 13, 12, BLACK)
    _px(img, 18, 11, BLACK)
    _px(img, 18, 12, BLACK)


def _draw_cheeks(img: Image.Image, spec: SpriteSpec) -> None:
    if spec.cheeks:
        _px(img, 12, 12, spec.cheek_rgb)
        _px(img, 19, 12, spec.cheek_rgb)


def _draw_ribbon(img: Image.Image, spec: SpriteSpec) -> None:
    """首元のオレンジリボン。"""
    rc = spec.ribbon_rgb
    _px(img, 14, 16, rc)
    _px(img, 15, 16, rc)
    _px(img, 16, 16, rc)
    _px(img, 17, 16, rc)


def _draw_top(img: Image.Image, spec: SpriteSpec) -> None:
    """青トップス + 袖口の肌色ハンドドット。"""
    tc = spec.top_rgb
    sk = spec.skin_rgb
    for y, x0, x1 in (
        (17, 11, 20),
        (18, 10, 21),
        (19, 10, 21),
        (20, 10, 21),
        (21, 11, 20),
    ):
        for x in range(x0, x1 + 1):
            _px(img, x, y, tc)
    _px(img, 10, 19, sk)
    _px(img, 21, 19, sk)


def _draw_skirt(img: Image.Image, spec: SpriteSpec) -> None:
    """グレースカート。"""
    sc = spec.skirt_rgb
    for y, x0, x1 in (
        (22, 11, 20),
        (23, 10, 21),
        (24, 11, 20),
        (25, 12, 19),
    ):
        for x in range(x0, x1 + 1):
            _px(img, x, y, sc)


def _draw_shoes(img: Image.Image, spec: SpriteSpec) -> None:
    """茶色の靴。"""
    bc = spec.shoe_rgb
    for x in (12, 13):
        _px(img, x, 27, bc)
        _px(img, x, 28, bc)
    for x in (18, 19):
        _px(img, x, 27, bc)
        _px(img, x, 28, bc)


def render_girl_sprite_32(spec: SpriteSpec | None = None) -> Image.Image:
    """32×32 正面向き・少女ファミコン風全身 NPC。"""
    sp = spec or build_sprite_spec()
    img = Image.new("RGB", (SPRITE_SIZE, SPRITE_SIZE), WHITE)

    _draw_hair_back(img, sp)
    _draw_face(img, sp)
    _draw_hair_front(img, sp)
    _draw_dot_eyes(img)
    _draw_cheeks(img, sp)
    _draw_ribbon(img, sp)
    _draw_top(img, sp)
    _draw_skirt(img, sp)
    _draw_shoes(img, sp)

    if sp.accessory == "mint_green_star":
        _draw_cross_star(img, 21, 5, sp.accent_rgb)

    return add_exterior_outline(img)


def generate_sprite_from_spec(
    character_spec: dict[str, Any] | None = None,
) -> tuple[Image.Image, Image.Image, SpriteSpec, SpriteValidationResult, dict[str, Any]]:
    sprite_spec = build_sprite_spec(character_spec)
    sprite = render_girl_sprite_32(sprite_spec)
    validation = validate_fixed_girl_sprite(sprite, sprite_spec)
    display = upscale_nearest(sprite, DISPLAY_SIZE)
    meta: dict[str, Any] = {
        "generation_mode": GENERATION_MODE,
        "render_mode": GENERATION_MODE,
        "sprite_size": SPRITE_SIZE,
        "display_size": DISPLAY_SIZE,
        "palette": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in NPC_PALETTE_8],
        "character_spec": FIXED_MVP_CHARACTER_SPEC,
        "sprite_spec": {
            "gender": sprite_spec.gender,
            "hair_style": sprite_spec.hair_style,
            "hair_color": "dark_navy",
            "eye_style": sprite_spec.eye_style,
            "accessory": sprite_spec.accessory,
            "top_color": "blue",
            "ribbon_color": "orange",
            "skirt_color": "grey",
            "shoe_color": "brown",
        },
        "validation_result": {
            "passed": validation.passed,
            "issues": validation.issues,
            "metrics": validation.metrics,
        },
        "pipeline": [
            "fixed_character_spec",
            "sprite_spec_build",
            "render_npc_girl_32x32",
            "quality_validation",
            "nearest_upscale_512",
        ],
    }
    return sprite, display, sprite_spec, validation, meta


def generate_spec_sprite_bundle(
    image_bytes: bytes | None = None,
    *,
    character_spec: dict[str, Any] | None = None,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    固定 spec で 1 枚生成。進化プレビューは当面同じスプライト（装飾なし）。
    image_bytes は将来用。現状は描画に使用しない。
    """
    _ = (image_bytes, character_profile)
    sprite, display, _spec, validation, base_meta = generate_sprite_from_spec(character_spec)
    if not validation.passed:
        raise ValueError(
            "sprite quality check failed: " + "; ".join(validation.issues)
        )

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"spec_girl_{tag}.png")
        display.save(saved_path, format="PNG")

    understanding = {
        "source": GENERATION_MODE,
        "raw_features": base_meta.get("sprite_spec", {}),
        "vision_api_status": "skipped",
        "render_mode": GENERATION_MODE,
    }

    meta: dict[str, Any] = {
        **base_meta,
        "stage": "baby",
        "next_stage": None,
        "signature_features_ja": FEATURES_JA,
        "image_understanding": understanding,
        "saved_path": saved_path,
    }

    return {
        "image_understanding": understanding,
        "character_dna": None,
        "parts_dna": None,
        "current_sprite": sprite,
        "current_display": display,
        "next_stage_preview": None,
        "final_hero_preview": None,
        "current_stage_image": display,
        "meta": meta,
        "saved_path": saved_path,
    }


def main() -> None:
    """ローカル確認: 32px と 512px PNG を出力。"""
    sprite, display, _spec, validation, _meta = generate_sprite_from_spec()
    out_dir = DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    sprite.save(out_dir / "girl_npc_32.png", format="PNG")
    display.save(out_dir / "girl_npc_512.png", format="PNG")
    print("validation:", validation.passed, validation.issues)
    print("saved:", out_dir / "girl_npc_32.png", out_dir / "girl_npc_512.png")


if __name__ == "__main__":
    main()


__all__ = [
    "FIXED_MVP_CHARACTER_SPEC",
    "GENERATION_MODE",
    "NPC_PALETTE_8",
    "SpriteSpec",
    "SpriteValidationResult",
    "build_sprite_spec",
    "generate_spec_sprite_bundle",
    "generate_sprite_from_spec",
    "render_girl_sprite_32",
    "validate_fixed_girl_sprite",
]
