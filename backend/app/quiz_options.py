"""クイズ選択肢の共通ヘルパー。"""
from __future__ import annotations

import hashlib


def four_string_options(correct: str, candidates: list[str], seed: str) -> list[str]:
    """正解を含む4択（重複除去・seed で順序を固定）。"""
    correct = (correct or "").strip()
    seen: set[str] = set()
    pool: list[str] = []
    for o in [correct, *candidates]:
        o = (o or "").strip()
        if not o or o in seen:
            continue
        seen.add(o)
        pool.append(o)
        if len(pool) >= 4:
            break
    while len(pool) < 4:
        pad = f"（選択肢{len(pool) + 1}）"
        if pad not in seen:
            seen.add(pad)
            pool.append(pad)
        else:
            break
    return sorted(pool[:4], key=lambda o: hashlib.sha256(f"{seed}|{o}".encode()).hexdigest())
