"""問題バンク統計 API。"""
from __future__ import annotations

from fastapi import APIRouter

from ..question_bank import bank_stats

router = APIRouter(tags=["questions"])


@router.get("/questions/bank-stats")
def questions_bank_stats():
    """教科×レベルごとの問題数と不足（推奨 5 問未満）を返す。認証不要（運用・接続テスト用）。"""
    return bank_stats()
