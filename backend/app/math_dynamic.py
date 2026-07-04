"""動的算数クイズ（レベル・問題番号から決定的に生成。採点と GET /api/questions で同一ルール）。"""
from __future__ import annotations


def _four_numeric_options(answer: int) -> list[str]:
    """正解と近い整数を4つ（重複・負数を避けて埋める）。"""
    seen: set[int] = set()
    out: list[int] = []
    for delta in (0, 1, -1, 2, 3, -2, 4, 5, -3):
        x = answer + delta
        if x < 0 or x in seen:
            continue
        seen.add(x)
        out.append(x)
        if len(out) >= 4:
            break
    return [str(v) for v in out[:4]]


def math_question_parts(level: int, idx: int) -> tuple[str, str, list[str], str]:
    """
    idx は 1 始まり。
    戻り値: (問題文, 正解文字列, 4択, ヒント)
    """
    lv = max(1, int(level))
    j = max(1, int(idx))
    j0 = j - 1  # 0..（CSV の idx に相当）

    # 6 パターンで「+ − × ÷」を混在（同レベルでも問題ごとに変化）
    v = (lv + j - 1) % 6

    if v in (0, 3):
        # たし算（語彙 CSV の a,b 定義に近い形）
        left = lv * 2 + j0
        right = j
        ans = left + right
        text = f"{left} + {right} は？"
        hint = "数を並べて足し算してみよう"
    elif v in (1, 4):
        # ひき算（答えは 0 以上の整数）
        left = lv * 3 + j + 5
        right = min(lv + j, left - 1)
        right = max(1, right)
        ans = left - right
        text = f"{left} - {right} は？"
        hint = "大きい方から小さい方を引いてみよう"
    elif v == 2:
        # かけ算（九九の範囲に収める）
        x = min(9, max(2, lv + j0))
        y = min(9, max(2, j + 1))
        ans = x * y
        text = f"{x} × {y} は？"
        hint = "九九の表や、ばらして足す考え方でもよいよ"
    else:
        # わり算（割り切れる式）
        divisor = min(9, max(2, j + 1))
        quotient = min(12, max(2, lv + j0))
        dividend = quotient * divisor
        ans = quotient
        text = f"{dividend} ÷ {divisor} は？"
        hint = "かけ算の逆だよ。何をかけたら上の数になる？"

    return text, str(ans), _four_numeric_options(ans), hint
