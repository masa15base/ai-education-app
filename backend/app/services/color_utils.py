"""RGB パレット補助（Vision 検出色 → 描画色）。"""
from __future__ import annotations

from typing import Any


def clamp_rgb(rgb: Any, default: tuple[int, int, int] = (85, 221, 204)) -> tuple[int, int, int]:
    if not isinstance(rgb, (list, tuple)) or len(rgb) < 3:
        return default
    out: list[int] = []
    for i in range(3):
        try:
            out.append(max(0, min(255, int(rgb[i]))))
        except (TypeError, ValueError):
            out.append(default[i])
    return (out[0], out[1], out[2])


def lighten(rgb: tuple[int, int, int], amount: float = 0.22) -> tuple[int, int, int]:
    return tuple(min(255, int(c + (255 - c) * amount)) for c in rgb)


def darken(rgb: tuple[int, int, int], amount: float = 0.18) -> tuple[int, int, int]:
    return tuple(max(0, int(c * (1.0 - amount))) for c in rgb)


def is_near_white(rgb: tuple[int, int, int], threshold: int = 235) -> bool:
    return rgb[0] >= threshold and rgb[1] >= threshold and rgb[2] >= threshold


def is_near_black(rgb: tuple[int, int, int], threshold: int = 48) -> bool:
    return rgb[0] <= threshold and rgb[1] <= threshold and rgb[2] <= threshold


def pick_salient_color(
    *candidates: tuple[int, int, int] | None,
    fallback: tuple[int, int, int],
) -> tuple[int, int, int]:
    for c in candidates:
        if c is None:
            continue
        rgb = clamp_rgb(c, fallback)
        if not is_near_white(rgb) and not is_near_black(rgb):
            return rgb
    return fallback
