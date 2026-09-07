"""ファミコン 8 色パレットとスプライト共通処理。"""
from __future__ import annotations

from PIL import Image, ImageDraw

FAMICOM_PALETTE: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "skin": (255, 224, 189),
    "orange": (255, 167, 51),
    "brown": (204, 122, 46),
    "blue": (77, 141, 245),
    "gray": (107, 107, 107),
    "green": (46, 204, 113),
}

BLACK = FAMICOM_PALETTE["black"]
WHITE = FAMICOM_PALETTE["white"]
SKIN = FAMICOM_PALETTE["skin"]
ORANGE = FAMICOM_PALETTE["orange"]
BROWN = FAMICOM_PALETTE["brown"]
BLUE = FAMICOM_PALETTE["blue"]
GRAY = FAMICOM_PALETTE["gray"]
GREEN = FAMICOM_PALETTE["green"]
RED = (220, 72, 72)

PALETTE_COLORS: tuple[tuple[int, int, int], ...] = tuple(FAMICOM_PALETTE.values())
MAX_PALETTE_COLORS = 8
DISPLAY_SIZE = 512
DEFAULT_SPRITE_SIZE = 32


def _color_dist(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> int:
    return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2


def snap_to_palette(img: Image.Image) -> Image.Image:
    w, h = img.size
    out = Image.new("RGB", (w, h), WHITE)
    src = img.load()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            src_c = src[x, y]
            best = WHITE
            best_d = 10**9
            for c in PALETTE_COLORS:
                d = _color_dist(src_c, c)
                if d < best_d:
                    best_d = d
                    best = c
            dst[x, y] = best
    return out


def add_exterior_outline(sprite: Image.Image) -> Image.Image:
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


def upscale_nearest(img: Image.Image, output_size: int = DISPLAY_SIZE) -> Image.Image:
    return img.resize((output_size, output_size), Image.Resampling.NEAREST)


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int]) -> None:
    import math

    pts: list[tuple[int, int]] = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else max(1, r * 0.42)
        pts.append((int(cx + rad * math.cos(ang)), int(cy - rad * math.sin(ang))))
    draw.polygon(pts, fill=fill, outline=BLACK)


def decorate_stage(sprite: Image.Image, stage: str) -> Image.Image:
    """ステージ装飾（進化の違いが一目でわかるよう強調）。"""
    if stage in ("egg", "baby"):
        return sprite
    out = sprite.copy()
    s = out.size[0]
    draw = ImageDraw.Draw(out)
    if stage == "child":
        # 頭上に大きめの星（進化の目印）
        cx = s // 2
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.point((cx + dx, 1 + dy), fill=GREEN)
        draw.point((cx, 0), fill=GREEN)
        # ほっぺ横に小さなキラキラ
        draw.point((4, s // 2), fill=GREEN)
        draw.point((s - 5, s // 2), fill=GREEN)
    elif stage == "student":
        cap_w = max(6, s // 4)
        cap_h = max(3, s // 10)
        left = (s - cap_w) // 2
        # 学士帽
        draw.rectangle([left, 1 + cap_h, left + cap_w, 1 + cap_h * 2], fill=BLACK)
        draw.rectangle([left - 1, 0, left + cap_w + 1, 1 + cap_h], fill=BLACK)
        draw.point((left + cap_w // 2, 0), fill=BLACK)
        # 本（赤表紙）
        draw.rectangle([s - 6, s - 8, s - 2, s - 3], fill=RED, outline=BLACK)
        draw.line([s - 5, s - 7, s - 3, s - 7], fill=WHITE)
    elif stage == "hero":
        # 王冠
        mid = s // 2
        for x in range(mid - 3, mid + 4):
            draw.point((x, 0), fill=ORANGE)
        draw.point((mid - 2, 1), fill=ORANGE)
        draw.point((mid, 0), fill=ORANGE)
        draw.point((mid + 2, 1), fill=ORANGE)
        # マント（左右を広めに）
        cape_y0 = int(s * 0.38)
        draw.polygon([(0, cape_y0), (s // 4, s - 1), (s // 4, cape_y0)], fill=BLUE)
        draw.polygon([(s - 1, cape_y0), (s - s // 4, s - 1), (s - s // 4, cape_y0)], fill=BLUE)
        # 胸バッジ + 足元の星
        draw.rectangle([mid - 2, s // 2, mid + 2, s // 2 + 3], fill=ORANGE, outline=BLACK)
        _draw_star(draw, mid, s - 3, 2, GREEN)
    return add_exterior_outline(snap_to_palette(out))
