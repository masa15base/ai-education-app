"""手書き画像を線画変換して保存する CLI。

Usage:
  python -m app.scripts.convert_handdrawn_image input.jpg output.png
  python -m app.scripts.convert_handdrawn_image input.jpg output.png --meta
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from app.image_preprocess_algo import (
    DEFAULT_FAMICOM_PIXEL_GRID,
    DEFAULT_MAX_EDGE,
    build_binary_scribble,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert hand-drawn image to binary scribble PNG.",
    )
    p.add_argument("input", type=Path, help="input image path")
    p.add_argument("output", type=Path, help="output PNG path")
    p.add_argument(
        "--max-edge",
        type=int,
        default=DEFAULT_MAX_EDGE,
        help=f"output square size (default: {DEFAULT_MAX_EDGE})",
    )
    p.add_argument(
        "--meta",
        action="store_true",
        help="print metadata JSON",
    )
    p.add_argument(
        "--smooth",
        action="store_true",
        help="disable Famicom-style chunky pixels (LANCZOS resize instead)",
    )
    p.add_argument(
        "--pixel-grid",
        type=int,
        default=DEFAULT_FAMICOM_PIXEL_GRID,
        metavar="N",
        help=(
            "internal square size before NEAREST upscale (default: "
            f"{DEFAULT_FAMICOM_PIXEL_GRID}; ignored with --smooth)"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")
    if args.max_edge < 64 or args.max_edge > 2048:
        raise SystemExit("--max-edge must be between 64 and 2048")
    if not args.smooth and (args.pixel_grid < 16 or args.pixel_grid > args.max_edge):
        raise SystemExit("--pixel-grid must be between 16 and --max-edge")

    img = Image.open(args.input).convert("RGB")
    out, meta = build_binary_scribble(
        img,
        max_edge=args.max_edge,
        famicom_pixels=not args.smooth,
        pixel_grid=args.pixel_grid,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output, format="PNG")

    print(f"Saved: {args.output}")
    if args.meta:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

