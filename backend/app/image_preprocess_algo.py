"""手書き画像の前処理アルゴリズム（API/CLI 共通）。"""
from __future__ import annotations

from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

DEFAULT_MAX_EDGE = 512
# ファミコン風: 内部を粗いグリッドに落としてから NEAREST で拡大
DEFAULT_FAMICOM_PIXEL_GRID = 128
# 巨大なカメラ写真は先に縮小（閾値推定の安定化・処理速度）
MAX_INPUT_EDGE = 1600

ALGORITHM_ID = "binary_scribble_v3_famicom"


def _otsu_threshold(hist: list[int], total: int) -> int:
    """ヒストグラムから Otsu 法で最適しきい値を求める。"""
    if total <= 0:
        return 128
    sum_total = sum(i * hist[i] for i in range(256))
    sum_b = 0.0
    w_b = 0
    max_var = -1.0
    threshold = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = t
    return int(threshold)


def _estimate_threshold(g: Image.Image) -> int:
    """Otsu + 平均輝度のブレンド（白紙写真で過剰に黒くならないようクランプ）。"""
    hist = g.histogram()
    total = max(1, sum(hist))
    otsu = _otsu_threshold(hist, total)
    stat = ImageStat.Stat(g)
    mean_l = float(stat.mean[0] if stat.mean else 128.0)
    mean_based = mean_l * 0.9
    if mean_l > 200:
        blended = min(otsu, mean_based)
    else:
        blended = 0.55 * otsu + 0.45 * mean_based
    return int(max(85, min(195, blended)))


def _gamma_correct(g: Image.Image, gamma: float = 1.12) -> Image.Image:
    """薄い鉛筆線をしきい値前に少し濃くする。"""
    inv_gamma = 1.0 / gamma
    table = [int(((i / 255.0) ** inv_gamma) * 255) for i in range(256)]
    return g.point(table)


def _normalize_input_rgb(rgb_img: Image.Image) -> Image.Image:
    w, h = rgb_img.size
    long_edge = max(w, h)
    if long_edge <= MAX_INPUT_EDGE:
        return rgb_img
    scale = MAX_INPUT_EDGE / long_edge
    return rgb_img.resize(
        (max(1, int(w * scale)), max(1, int(h * scale))),
        Image.Resampling.LANCZOS,
    )


def _clean_binary_bw(bw: Image.Image) -> Image.Image:
    """
    二値画像のノイズ除去と線の保全。
    - MaxFilter: 背景上の孤立黒点（椒塩）を除去
    - MinFilter: 線をわずかに太らせピクセル化で消えにくくする
    """
    cleaned = bw.filter(ImageFilter.MaxFilter(size=3))
    cleaned = cleaned.filter(ImageFilter.MinFilter(size=3))
    return cleaned


def _content_aware_pixel_grid(
    content_w: int,
    content_h: int,
    canvas_side: int,
    max_edge: int,
    default_grid: int,
) -> int:
    """絵の占有率に応じて内部ドット解像度を調整（小さく写った絵はやや粗く）。"""
    fill = (content_w * content_h) / max(1, canvas_side * canvas_side)
    if fill < 0.12:
        target = int(default_grid * 0.62)
    elif fill < 0.28:
        target = int(default_grid * 0.8)
    else:
        target = default_grid
    return max(40, min(max_edge, target))


def _famicom_pixelize(
    bw_square: Image.Image,
    max_edge: int,
    pixel_grid: int,
) -> tuple[Image.Image, int]:
    """白黒正方形を低解像度ドットに落とし、NEAREST でブロック拡大する。"""
    inner = max(32, min(pixel_grid, max_edge))
    # BOX でセル平均 → 再二値化で均一なドット境界
    small = bw_square.resize((inner, inner), Image.Resampling.BOX)
    small = small.point(lambda p: 0 if p < 140 else 255, mode="L")
    out = small.resize((max_edge, max_edge), Image.Resampling.NEAREST)
    return out, inner


def build_binary_scribble(
    rgb_img: Image.Image,
    max_edge: int = DEFAULT_MAX_EDGE,
    *,
    famicom_pixels: bool = True,
    pixel_grid: int = DEFAULT_FAMICOM_PIXEL_GRID,
) -> tuple[Image.Image, dict[str, Any]]:
    """
    手書き写真 → 線画ピクセルアート PNG（L モード）。

    パイプライン:
    1. 長辺制限で入力正規化
    2. グレースケール + オートコントラスト + メディアン + ガンマ
    3. Otsu ブレンドしきい値で二値化
    4. 形態学的クリーンアップ
    5. 余白トリム → 正方形パディング
    6. 占有率に応じた低解像度グリッド → NEAREST 拡大（ドット絵）
    """
    rgb_img = _normalize_input_rgb(rgb_img)
    g = ImageOps.autocontrast(rgb_img.convert("L"), cutoff=1)
    g = g.filter(ImageFilter.MedianFilter(size=3))
    g = _gamma_correct(g)
    g = ImageEnhance.Contrast(g).enhance(1.06)

    threshold = _estimate_threshold(g)
    bw = g.point(lambda p: 0 if p < threshold else 255, mode="L")
    bw = _clean_binary_bw(bw)

    hist = bw.histogram()
    total = max(1, bw.width * bw.height)
    black = hist[0] if hist else 0
    ink_ratio = black / total

    inv = ImageOps.invert(bw)
    bbox = inv.getbbox()
    if bbox:
        bw = bw.crop(bbox)
        content_w = bbox[2] - bbox[0]
        content_h = bbox[3] - bbox[1]
    else:
        content_w, content_h = bw.width, bw.height

    side = max(bw.width, bw.height)
    square = Image.new("L", (side, side), 255)
    ox = (side - bw.width) // 2
    oy = (side - bw.height) // 2
    square.paste(bw, (ox, oy))

    if famicom_pixels:
        grid = _content_aware_pixel_grid(
            content_w, content_h, side, max_edge, pixel_grid
        )
        out, inner = _famicom_pixelize(square, max_edge, grid)
        meta = {
            "threshold": threshold,
            "thresholdMethod": "otsu_blend",
            "inkRatio": round(float(ink_ratio), 4),
            "hasContent": bool(bbox),
            "contentWidth": int(content_w),
            "contentHeight": int(content_h),
            "maxEdge": int(max_edge),
            "pixelGrid": int(inner),
            "renderStyle": "famicom_nearest",
            "algorithm": ALGORITHM_ID,
        }
    else:
        out = square.resize((max_edge, max_edge), Image.Resampling.LANCZOS)
        meta = {
            "threshold": threshold,
            "thresholdMethod": "otsu_blend",
            "inkRatio": round(float(ink_ratio), 4),
            "hasContent": bool(bbox),
            "contentWidth": int(content_w),
            "contentHeight": int(content_h),
            "maxEdge": int(max_edge),
            "renderStyle": "smooth",
            "algorithm": ALGORITHM_ID,
        }
    return out, meta
