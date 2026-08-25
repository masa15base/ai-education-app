"""問題バンク CSV 投入 CLI。

使い方（backend ディレクトリで）:
  export JAWSDB_URL="$(heroku config:get JAWSDB_URL -a ai-edu-app-backend)"
  . .venv/bin/activate
  python scripts/upload_question_bank.py --dry-run
  python scripts/upload_question_bank.py --mode upsert
  python scripts/upload_question_bank.py --mode replace --csv app/data/questions_level_10_final.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# backend/ を path に
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap_env import load_backend_env  # noqa: E402

load_backend_env()

# mysql:// → mysql+pymysql:// （create_engine 前に）
_raw = os.environ.get("JAWSDB_URL") or os.environ.get("DATABASE_URL")
if _raw and _raw.startswith("mysql://"):
    os.environ["JAWSDB_URL"] = _raw.replace("mysql://", "mysql+pymysql://", 1)

from app import db as dbmod  # noqa: E402
from app.question_bank import bank_stats, import_questions, load_questions_csv  # noqa: E402


def main() -> None:
    default_csv = ROOT / "app" / "data" / "questions_level_10_final.csv"
    parser = argparse.ArgumentParser(description="Upload questions CSV to JawsDB")
    parser.add_argument(
        "--csv",
        type=Path,
        default=default_csv,
        help=f"CSV path (default: {default_csv})",
    )
    parser.add_argument(
        "--mode",
        choices=("upsert", "replace"),
        default="upsert",
        help="upsert=追記/更新, replace=全消し後に投入",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="検証のみ（DB 書き込みなし）",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="投入せずカバレッジ統計だけ表示",
    )
    args = parser.parse_args()

    if args.stats_only:
        stats = bank_stats()
        print(stats)
        return

    if not args.dry_run and dbmod.SessionLocal is None:
        raise SystemExit("JAWSDB_URL が未設定、または DB エンジンを作成できません")

    print(f"CSV: {args.csv}")
    rows = load_questions_csv(args.csv)
    print(f"Loaded {len(rows)} questions")

    result = import_questions(rows, mode=args.mode, dry_run=args.dry_run)
    print(result)
    if not args.dry_run:
        print("Bank stats after import:")
        print(bank_stats())


if __name__ == "__main__":
    main()
