"""クイズ選択肢の共通ヘルパー。"""
from __future__ import annotations

import hashlib
import re

_PLACEHOLDER_RE = re.compile(r"^（選択肢\d+）$")

# 文字列の誤答が足りないときの予備（日本語）
_FALLBACK_JA = [
    "ねこ",
    "いぬ",
    "りんご",
    "くるま",
    "ほん",
    "みず",
    "やま",
    "うみ",
    "そら",
    "はな",
    "ペン",
    "ボール",
    "学校",
    "ともだち",
    "あお",
]


def _is_placeholder(s: str) -> bool:
    return bool(_PLACEHOLDER_RE.match(s)) or s.startswith("（選択肢")


def _numeric_distractors(correct: str, seen: set[str], need: int) -> list[str]:
    try:
        n = int(str(correct).strip())
    except ValueError:
        return []
    out: list[str] = []
    for delta in range(1, 80):
        for v in (n + delta, n - delta):
            s = str(v)
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
            if len(out) >= need:
                return out
    return out


def _string_distractors(correct: str, seen: set[str], need: int, seed: str) -> list[str]:
    ranked = sorted(
        _FALLBACK_JA,
        key=lambda o: hashlib.sha256(f"{seed}|pad|{o}".encode()).hexdigest(),
    )
    out: list[str] = []
    for o in ranked:
        if o == correct or o in seen:
            continue
        seen.add(o)
        out.append(o)
        if len(out) >= need:
            break
    i = 1
    while len(out) < need:
        pad = f"こたえ{i}"
        i += 1
        if pad in seen or pad == correct:
            continue
        seen.add(pad)
        out.append(pad)
    return out


def four_string_options(correct: str, candidates: list[str], seed: str) -> list[str]:
    """正解を含む4択（重複除去・プレースホルダー除外・seed で順序を固定）。"""
    correct = (correct or "").strip()
    seen: set[str] = set()
    pool: list[str] = []

    def _add(o: str) -> None:
        o = (o or "").strip()
        if not o or o in seen or _is_placeholder(o):
            return
        seen.add(o)
        pool.append(o)

    _add(correct)
    for o in candidates:
        _add(o)
        if len(pool) >= 4:
            break

    need = 4 - len(pool)
    if need > 0:
        for o in _numeric_distractors(correct, seen, need):
            pool.append(o)
            if len(pool) >= 4:
                break
    need = 4 - len(pool)
    if need > 0:
        for o in _string_distractors(correct, seen, need, seed):
            pool.append(o)
            if len(pool) >= 4:
                break

    return sorted(pool[:4], key=lambda o: hashlib.sha256(f"{seed}|{o}".encode()).hexdigest())
