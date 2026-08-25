"""互換ラッパ: scripts/upload_question_bank.py を推奨。"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "scripts" / "upload_question_bank.py"
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
