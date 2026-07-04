"""
DEPRECATED: trace_pixelize / line_trace は品質問題のためメイン経路から廃止。
装飾・パレット共通処理は famicom_sprite_common.py を使用すること。
"""
from __future__ import annotations

import colorsys
import io
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from ..image_preprocess_algo import build_binary_scribble
from .character_sprite_designer import STAGES_ORDER, next_stage_after, _dominant_accent_rgb

# --- ファミコン 8 色パレット（仕様書準拠） ---
FAMICOM_PALETTE: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "skin": (255, 224, 189),   # #FFE0BD
    "orange": (255, 167, 51),  # #FFA733
    "brown": (204, 122, 46),   # #CC7A2E
    "blue": (77, 141, 245),    # #4D8DF5
    "gray": (107, 107, 107),   # #6B6B6B
    "green": (46, 204, 113),   # #2ECC71
}

BLACK = FAMICOM_PALETTE["black"]
WHITE = FAMICOM_PALETTE["white"]
SKIN = FAMICOM_PALETTE["skin"]
ORANGE = FAMICOM_PALETTE["orange"]
BROWN = FAMICOM_PALETTE["brown"]
BLUE = FAMICOM_PALETTE["blue"]
GRAY = FAMICOM_PALETTE["gray"]
GREEN = FAMICOM_PALETTE["green"]

PALETTE_COLORS: tuple[tuple[int, int, int], ...] = tuple(FAMICOM_PALETTE.values())
MAX_PALETTE_COLORS = 8

DISPLAY_SIZE = 512
DEFAULT_SPRITE_SIZE = 32
MIN_SPRITE_SIZE = 16
LINE_TRACE_MODE = "line_trace"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"
MAX_WORK_EDGE = 900
LINE_INK_THRESHOLD = 180


def _luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b


def _color_dist(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> int:
    return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2


def _nearest_palette(r: int, g: int, b: int) -> tuple[int, int, int]:
    src = (r, g, b)
    best = WHITE
    best_d = 10**9
    for c in PALETTE_COLORS:
        d = _color_dist(src, c)
        if d < best_d:
            best_d = d
            best = c
    return best


def _is_ink(r: int, g: int, b: int) -> bool:
    """輪郭・目・口の線（黒一色塗りつぶしはしない：ソースで暗い線のみ）。"""
    l = _luminance(r, g, b)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if l < 72:
        return True
    if l < 118 and s < 0.28:
        return True
    if l < 145 and s < 0.12 and v < 0.55:
        return True
    return False


def _is_skin_fill(r: int, g: int, b: int) -> bool:
    l = _luminance(r, g, b)
    if l < 120 or l > 248:
        return False
    h, s, _v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if s < 0.06 or s > 0.55:
        return False
    return (0.02 <= h <= 0.14) or (0.90 <= h <= 1.0)


def _classify_pixel(
    r: int,
    g: int,
    b: int,
    *,
    y_ratio: float,
    in_face_band: bool,
) -> tuple[int, int, int]:
    """ソース色 → 8 色パレット（フラット、グラデーションなし）。"""
    l = _luminance(r, g, b)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    if l > 246 and max(r, g, b) - min(r, g, b) < 18:
        return WHITE

    if _is_ink(r, g, b):
        return BLACK

    # 緑系アクセント（星・装飾）
    if s >= 0.22 and 0.22 <= h <= 0.48 and v >= 0.25:
        return GREEN

    # 青系（服・リボン）
    if s >= 0.18 and 0.52 <= h <= 0.72 and v >= 0.25:
        return BLUE

    # 髪・暖色（上寄り）
    if y_ratio < 0.55:
        if 0.04 <= h <= 0.12 and s >= 0.25:
            return ORANGE if v >= 0.55 else BROWN
        if 0.12 <= h <= 0.18 and s >= 0.20:
            return BROWN

    # 肌（顔帯のみ・薄塗り）
    if in_face_band and _is_skin_fill(r, g, b):
        return SKIN

    # 低彩度 → グレー or 白
    if s < 0.12:
        return GRAY if l < 210 else WHITE

    return _nearest_palette(r, g, b)


def _snap_to_palette(img: Image.Image) -> Image.Image:
    """使用色を 8 色パレットに厳密に制限。"""
    w, h = img.size
    out = Image.new("RGB", (w, h), WHITE)
    src = img.load()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            dst[x, y] = _nearest_palette(*src[x, y])
    return out


def _add_exterior_outline(sprite: Image.Image) -> Image.Image:
    """色ピクセルの外側（白背景側）に 1px 黒アウトラインを追加。"""
    w, h = sprite.size
    out = sprite.copy()
    src = sprite.load()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            c = src[x, y]
            if c in (WHITE, BLACK):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ox, oy = x + dx, y + dy
                if 0 <= ox < w and 0 <= oy < h and src[ox, oy] == WHITE:
                    dst[ox, oy] = BLACK
    return out


def _rgba_to_rgb_white(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (*WHITE, 255))
        bg.alpha_composite(img)
        return bg.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img.copy()


def _normalize_work_size(img: Image.Image) -> Image.Image:
    w, h = img.size
    edge = max(w, h)
    if edge <= MAX_WORK_EDGE:
        return img
    scale = MAX_WORK_EDGE / edge
    return img.resize(
        (max(1, int(w * scale)), max(1, int(h * scale))),
        Image.Resampling.LANCZOS,
    )


def _brighten_background(rgb: Image.Image) -> Image.Image:
    """明るい紙・影を #FFFFFF に正規化。"""
    out = Image.new("RGB", rgb.size, WHITE)
    src = rgb.load()
    dst = out.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            l = _luminance(r, g, b)
            hsv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            s, v = hsv[1], hsv[2]
            if l > 228 and s < 0.14:
                dst[x, y] = WHITE
            elif l > 210 and s < 0.08:
                dst[x, y] = WHITE
            elif v > 0.92 and s < 0.10 and not _is_ink(r, g, b):
                dst[x, y] = WHITE
            else:
                dst[x, y] = (r, g, b)
    return out


def _trace_rgb(rgb: Image.Image) -> Image.Image:
    w, h = rgb.size
    out = Image.new("RGB", (w, h), WHITE)
    src = rgb.load()
    dst = out.load()
    y_face0 = int(h * 0.28)
    y_face1 = int(h * 0.82)
    x_face0 = int(w * 0.18)
    x_face1 = int(w * 0.82)
    for y in range(h):
        y_ratio = y / max(1, h - 1)
        for x in range(w):
            r, g, b = src[x, y]
            in_face = y_face0 <= y <= y_face1 and x_face0 <= x <= x_face1
            dst[x, y] = _classify_pixel(r, g, b, y_ratio=y_ratio, in_face_band=in_face)
    return out


def _content_bbox(img: Image.Image, pad_ratio: float = 0.06) -> Image.Image:
    g = img.convert("L")
    inv = ImageOps.invert(g)
    bbox = inv.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    w, h = img.size
    pad_x = max(2, int((x1 - x0) * pad_ratio))
    pad_y = max(2, int((y1 - y0) * pad_ratio))
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w, x1 + pad_x)
    y1 = min(h, y1 + pad_y)
    return img.crop((x0, y0, x1, y1))


def _square_pad(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = max(w, h)
    sq = Image.new("RGB", (side, side), WHITE)
    ox = (side - w) // 2
    oy = (side - h) // 2
    sq.paste(img, (ox, oy))
    return sq


def _downscale_trace(img: Image.Image, sprite_size: int) -> Image.Image:
    """32×32 等に縮小 → パレット再分類 → 1px 黒アウトライン。"""
    sprite_size = max(MIN_SPRITE_SIZE, min(32, sprite_size))
    small = img.resize((sprite_size, sprite_size), Image.Resampling.BOX)
    w, h = small.size
    out = Image.new("RGB", (w, h), WHITE)
    src = small.load()
    dst = out.load()
    y_face0 = int(h * 0.28)
    y_face1 = int(h * 0.82)
    x_face0 = int(w * 0.18)
    x_face1 = int(w * 0.82)
    for y in range(h):
        y_ratio = y / max(1, h - 1)
        for x in range(w):
            r, g, b = src[x, y]
            in_face = y_face0 <= y <= y_face1 and x_face0 <= x <= x_face1
            dst[x, y] = _classify_pixel(r, g, b, y_ratio=y_ratio, in_face_band=in_face)
    out = _snap_to_palette(out)
    out = _add_exterior_outline(out)
    return out


def _square_pad_l(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = max(w, h)
    sq = Image.new("L", (side, side), 255)
    ox = (side - w) // 2
    oy = (side - h) // 2
    sq.paste(img, (ox, oy))
    return sq


def _prepare_line_art(line: Image.Image) -> Image.Image:
    """前処理線画を黒線・白背景に正規化し、32px でも線が消えにくくする。"""
    g = line.convert("L")
    hist = g.histogram()
    total = max(1, sum(hist))
    mean_l = sum(i * hist[i] for i in range(256)) / total
    if mean_l < 128:
        g = ImageOps.invert(g)
    g = g.filter(ImageFilter.MinFilter(3))
    return g


def _flood_fill_skin(sprite: Image.Image, seed: tuple[int, int]) -> Image.Image:
    """線で囲まれた顔の内側だけ薄い肌色に（外側は白のまま）。"""
    w, h = sprite.size
    sx, sy = seed
    if sprite.getpixel((sx, sy)) != WHITE:
        return sprite
    from collections import deque

    out = sprite.copy()
    q: deque[tuple[int, int]] = deque([(sx, sy)])
    visited: set[tuple[int, int]] = set()
    filled: list[tuple[int, int]] = []
    while q:
        x, y = q.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if out.getpixel((x, y)) != WHITE:
            continue
        filled.append((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                q.append((nx, ny))
    if 5 < len(filled) < w * h * 0.45:
        for x, y in filled:
            out.putpixel((x, y), SKIN)
    return out


def _map_accent_to_sprite(
    sprite: Image.Image,
    rgb_source: Image.Image,
    line: Image.Image,
    accent: tuple[int, int, int],
) -> Image.Image:
    """元画像のカラーアクセント位置をスプライト座標に写す。"""
    if line.size != rgb_source.size:
        line = line.resize(rgb_source.size, Image.Resampling.NEAREST)
    src_px = rgb_source.load()
    w, h = rgb_source.size
    sx, sy = sprite.size
    inv = ImageOps.invert(_prepare_line_art(line))
    bbox = inv.getbbox()
    if not bbox:
        return sprite
    x0, y0, x1, y1 = bbox
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    accent_px = GREEN if accent == GREEN else BLUE if accent == BLUE else ORANGE
    out = sprite.copy()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = src_px[x, y]
            if _luminance(r, g, b) > 235:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if ss < 0.35 or vv < 0.25:
                continue
            tx = int((x - x0) / bw * (sx - 1))
            ty = int((y - y0) / bh * (sy - 1))
            if 0 <= tx < sx and 0 <= ty < sy:
                cur = out.getpixel((tx, ty))
                if cur in (WHITE, SKIN):
                    out.putpixel((tx, ty), accent_px)
    return out


def _image_has_color_accents(rgb: Image.Image, line: Image.Image) -> bool:
    """白黒線画（線上の圧縮ノイズ除く）ではアクセント塗りをスキップ。"""
    if line.size != rgb.size:
        line = line.resize(rgb.size, Image.Resampling.NEAREST)
    px = rgb.convert("RGB").load()
    line_px = line.convert("L").load()
    w, h = rgb.size
    color = total = 0
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            if line_px[x, y] < LINE_INK_THRESHOLD:
                continue
            r, g, b = px[x, y]
            if r > 240 and g > 240 and b > 240:
                continue
            total += 1
            _, s, _v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if s >= 0.35:
                color += 1
    return total > 0 and (color / total) >= 0.03


def trace_pixelize_line_art(
    line: Image.Image,
    rgb_source: Image.Image | None = None,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> Image.Image:
    """
    前処理済み線画 → 32×32 FC スプライト。
    元絵の線の構図を NEAREST 縮小で保持する。
    """
    sprite_size = max(MIN_SPRITE_SIZE, min(32, sprite_size))
    g = _prepare_line_art(line)
    inv = ImageOps.invert(g)
    bbox = inv.getbbox()
    if bbox:
        g = g.crop(bbox)
    g = _square_pad_l(g)
    small = g.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)

    out = Image.new("RGB", (sprite_size, sprite_size), WHITE)
    for y in range(sprite_size):
        for x in range(sprite_size):
            out.putpixel((x, y), BLACK if small.getpixel((x, y)) < LINE_INK_THRESHOLD else WHITE)

    seed = (sprite_size // 2, int(sprite_size * 0.52))
    out = _flood_fill_skin(out, seed)

    out = _snap_to_palette(out)
    return out


def line_trace_from_bytes(
    image_bytes: bytes,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> tuple[Image.Image, dict[str, Any]]:
    rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    line, preprocess_meta = build_binary_scribble(rgb, max_edge=512, famicom_pixels=False)
    sprite = trace_pixelize_line_art(line, rgb, sprite_size=sprite_size)
    meta = {
        "generation_mode": LINE_TRACE_MODE,
        "render_mode": LINE_TRACE_MODE,
        "sprite_size": sprite.size[0],
        "display_size": DISPLAY_SIZE,
        "max_colors": MAX_PALETTE_COLORS,
        "palette_hex": _palette_hex_list(sprite),
        "preprocess": preprocess_meta,
        "pipeline": [
            "binary_scribble_line_extract",
            "nearest_downscale_32",
            "face_skin_flood_fill",
            "accent_color_map",
            "8_color_quantize",
            "nearest_upscale_512",
        ],
    }
    return sprite, meta


LINE_TRACE_FEATURES_JA: list[str] = [
    "元の線画をそのままドット化",
    "32×32 ファミコン風",
    "8色・白背景",
]


def generate_line_trace_evolution_bundle(
    image_bytes: bytes,
    *,
    stage_key: str,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
    force_egg: bool = False,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> dict[str, Any]:
    """前処理線画 trace ベースで current / next / hero。"""
    _ = character_profile
    if force_egg:
        stage_key = "egg"
    else:
        stage_key = stage_key if stage_key in STAGES_ORDER else "baby"
        if stage_key == "egg":
            stage_key = "baby"

    base_sprite, base_meta = line_trace_from_bytes(image_bytes, sprite_size=sprite_size)

    current_sprite = _decorate_stage(base_sprite, stage_key)
    current_display = _upscale_nearest(current_sprite, DISPLAY_SIZE)

    nxt = next_stage_after(stage_key)
    next_display = None
    if nxt and nxt != "egg":
        next_sprite = _decorate_stage(base_sprite, nxt)
        next_display = _upscale_nearest(next_sprite, DISPLAY_SIZE)

    hero_sprite = _decorate_stage(base_sprite, "hero")
    hero_display = _upscale_nearest(hero_sprite, DISPLAY_SIZE)

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"line_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")
        hero_display.save(dest / f"line_hero_{tag}.png", format="PNG")
        if next_display is not None and nxt:
            next_display.save(dest / f"line_{nxt}_{tag}.png", format="PNG")

    understanding = {
        "source": LINE_TRACE_MODE,
        "raw_features": {"preprocess_ink_ratio": (base_meta.get("preprocess") or {}).get("inkRatio")},
        "vision_api_status": "skipped",
        "render_mode": LINE_TRACE_MODE,
    }

    meta: dict[str, Any] = {
        **base_meta,
        "stage": stage_key,
        "next_stage": nxt,
        "signature_features_ja": LINE_TRACE_FEATURES_JA,
        "image_understanding": understanding,
        "vision_result": None,
        "character_dna": None,
        "parts_dna": None,
        "saved_path": saved_path,
    }

    return {
        "image_understanding": understanding,
        "character_dna": None,
        "parts_dna": None,
        "current_sprite": current_sprite,
        "current_display": current_display,
        "next_stage_preview": next_display,
        "final_hero_preview": hero_display,
        "current_stage_image": current_display,
        "meta": meta,
        "saved_path": saved_path,
    }


def _upscale_nearest(img: Image.Image, output_size: int) -> Image.Image:
    return img.resize((output_size, output_size), Image.Resampling.NEAREST)


def _palette_hex_list(img: Image.Image) -> list[str]:
    used = sorted({img.getpixel((x, y)) for y in range(img.size[1]) for x in range(img.size[0])})
    return [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in used]


def _draw_star(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
) -> None:
    import math

    pts: list[tuple[int, int]] = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.42
        pts.append((int(cx + r * math.cos(ang)), int(cy - r * math.sin(ang))))
    draw.polygon(pts, fill=fill, outline=outline)


def _decorate_stage(sprite: Image.Image, stage: str) -> Image.Image:
    """同一 trace ベース + 最小装飾（8 色パレット内）。"""
    if stage in ("egg", "baby"):
        return sprite

    out = sprite.copy()
    s = out.size[0]
    draw = ImageDraw.Draw(out)

    if stage == "child":
        _draw_star(draw, s - 3, 2, 2, GREEN, BLACK)

    elif stage == "student":
        cap_w = max(4, s // 5)
        cap_h = max(2, s // 14)
        top = 1
        left = (s - cap_w) // 2
        draw.rectangle([left, top + cap_h, left + cap_w, top + cap_h * 2], fill=BLACK)
        draw.rectangle([left - 1, top, left + cap_w + 1, top + cap_h], fill=BLACK)
        bx0, by0 = s - 5, s - 6
        draw.rectangle([bx0, by0, bx0 + 3, by0 + 4], fill=BLUE, outline=BLACK)

    elif stage == "hero":
        _draw_star(draw, s // 2, s - 4, 2, GREEN, BLACK)
        cape_y0 = int(s * 0.42)
        cape_y1 = s - 2
        draw.polygon([(0, cape_y0), (s // 5, cape_y1), (s // 5, cape_y0)], fill=BLUE)
        draw.polygon([(s, cape_y0), (s - s // 5, cape_y1), (s - s // 5, cape_y0)], fill=BLUE)

    return _snap_to_palette(_add_exterior_outline(out))


def trace_pixelize_pil(
    img: Image.Image,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
    output_size: int = DISPLAY_SIZE,
) -> tuple[Image.Image, Image.Image]:
    """PIL Image → (sprite RGB, display RGB)。"""
    rgb = _normalize_work_size(_rgba_to_rgb_white(img))
    rgb = _brighten_background(rgb)
    traced = _trace_rgb(rgb)
    traced = _square_pad(_content_bbox(traced))
    sprite = _downscale_trace(traced, sprite_size)
    display = _upscale_nearest(sprite, output_size)
    return sprite, display


def trace_pixelize_from_bytes(
    image_bytes: bytes,
    *,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
    output_size: int = DISPLAY_SIZE,
) -> tuple[Image.Image, Image.Image, dict[str, Any]]:
    img = Image.open(io.BytesIO(image_bytes))
    sprite, display = trace_pixelize_pil(
        img,
        sprite_size=sprite_size,
        output_size=output_size,
    )
    meta = {
        "generation_mode": "trace_pixelize",
        "render_mode": "trace_pixelize",
        "sprite_size": sprite.size[0],
        "display_size": output_size,
        "max_colors": MAX_PALETTE_COLORS,
        "palette_hex": _palette_hex_list(sprite),
        "famicom_spec": {
            "canvas_px": sprite.size[0],
            "outline": "#000000",
            "background": "#FFFFFF",
            "upscale": "nearest_neighbor",
        },
        "pipeline": [
            "white_background",
            "trace_structure_preserve",
            "8_color_quantize",
            "32px_downscale",
            "1px_black_outline",
            "nearest_upscale_512",
        ],
    }
    return sprite, display, meta


def trace_pixelize_character(
    input_image_path: str,
    output_dir: str,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
    output_size: int = DISPLAY_SIZE,
) -> str:
    """
    元画像の構造を保持したまま、ファミコン風ドット画像に変換する。
    保存先 PNG のパスを返す。
    """
    img = Image.open(input_image_path)
    sprite, display = trace_pixelize_pil(
        img,
        sprite_size=sprite_size,
        output_size=output_size,
    )
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    tag = uuid.uuid4().hex[:12]
    out_path = dest / f"trace_{tag}.png"
    display.save(out_path, format="PNG")
    sprite.save(dest / f"trace_sprite_{tag}.png", format="PNG")
    return str(out_path)


def _minimal_understanding() -> dict[str, Any]:
    return {
        "source": "trace_pixelize",
        "raw_features": {},
        "vision_api_status": "skipped",
        "render_mode": "trace_pixelize",
    }


TRACE_FEATURES_JA: list[str] = [
    "元の絵の構図を残したドット化",
    "32×32 ファミコン風",
    "8色・1px黒アウトライン",
    "白背景 #FFFFFF",
]


def generate_trace_evolution_bundle(
    image_bytes: bytes,
    *,
    stage_key: str,
    character_profile: dict | None = None,
    save_file: bool = False,
    output_dir: str | Path | None = None,
    force_egg: bool = False,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
) -> dict[str, Any]:
    """trace_pixelize ベースで current / next / hero（同一構図 + 最小装飾）。"""
    _ = character_profile
    if force_egg:
        stage_key = "egg"
    else:
        stage_key = stage_key if stage_key in STAGES_ORDER else "baby"
        if stage_key == "egg":
            stage_key = "baby"

    base_sprite, _, base_meta = trace_pixelize_from_bytes(
        image_bytes,
        sprite_size=sprite_size,
    )

    current_sprite = _decorate_stage(base_sprite, stage_key)
    current_display = _upscale_nearest(current_sprite, DISPLAY_SIZE)

    nxt = next_stage_after(stage_key)
    next_display = None
    if nxt and nxt != "egg":
        next_sprite = _decorate_stage(base_sprite, nxt)
        next_display = _upscale_nearest(next_sprite, DISPLAY_SIZE)

    hero_sprite = _decorate_stage(base_sprite, "hero")
    hero_display = _upscale_nearest(hero_sprite, DISPLAY_SIZE)

    saved_path: str | None = None
    if save_file and output_dir:
        dest = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        tag = uuid.uuid4().hex[:12]
        saved_path = str(dest / f"trace_{stage_key}_{tag}.png")
        current_display.save(saved_path, format="PNG")
        hero_display.save(dest / f"trace_hero_{tag}.png", format="PNG")
        if next_display is not None and nxt:
            next_display.save(dest / f"trace_{nxt}_{tag}.png", format="PNG")

    understanding = _minimal_understanding()
    meta: dict[str, Any] = {
        **base_meta,
        "stage": stage_key,
        "next_stage": nxt,
        "signature_features_ja": TRACE_FEATURES_JA,
        "image_understanding": understanding,
        "vision_result": None,
        "character_dna": None,
        "parts_dna": None,
        "saved_path": saved_path,
    }

    return {
        "image_understanding": understanding,
        "character_dna": None,
        "parts_dna": None,
        "current_sprite": current_sprite,
        "current_display": current_display,
        "next_stage_preview": next_display,
        "final_hero_preview": hero_display,
        "current_stage_image": current_display,
        "meta": meta,
        "saved_path": saved_path,
    }


__all__ = [
    "DISPLAY_SIZE",
    "DEFAULT_SPRITE_SIZE",
    "FAMICOM_PALETTE",
    "LINE_TRACE_MODE",
    "MAX_PALETTE_COLORS",
    "generate_line_trace_evolution_bundle",
    "generate_trace_evolution_bundle",
    "line_trace_from_bytes",
    "trace_pixelize_character",
    "trace_pixelize_from_bytes",
    "trace_pixelize_line_art",
    "trace_pixelize_pil",
]
