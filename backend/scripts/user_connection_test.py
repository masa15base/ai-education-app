#!/usr/bin/env python3
"""
ターミナルから API / DB 接続を確認するスクリプト。

使用例:
  cd backend && python scripts/user_connection_test.py
  python scripts/user_connection_test.py --base https://xxx.herokuapp.com/api

環境変数 JAWSDB_URL は backend/.env にあると自動で読み込みます（python-dotenv）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# backend 直下の .env を読む
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def fetch_json(url: str, headers: dict | None = None, timeout: float = 15.0) -> tuple[int, object]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:
        return -1, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description="まなとも ユーザー接続テスト（CLI）")
    parser.add_argument(
        "--base",
        default=os.getenv("API_BASE_URL", "http://localhost:8000/api"),
        help="API のベース URL（末尾 /api）",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print(f"API base: {base}\n")

    code, data = fetch_json(f"{base}/health")
    ok = code == 200 and isinstance(data, dict) and data.get("ok") is True
    print(f"[1] GET /health  → {code}  {'OK' if ok else 'NG'}")
    if not ok:
        print(f"    {data}")
        return 1

    diag_candidates = [
        ("GET /health?include_diagnostic=true", f"{base}/health?include_diagnostic=true"),
        ("GET /diagnostic", f"{base}/diagnostic"),
        ("GET /health/diagnostic", f"{base}/health/diagnostic"),
    ]
    diag_ok = False
    last_code, last_data = -1, None
    for label, url in diag_candidates:
        code, data = fetch_json(url)
        last_code, last_data = code, data
        ok_shape = isinstance(data, dict) and isinstance(
            data.get("database_configured"), bool
        )
        print(f"[2] {label} → {code}{' ✓ 詳細取得' if ok_shape else ''}")
        if isinstance(data, dict) and ok_shape:
            diag_ok = True
            for k, v in sorted(data.items()):
                print(f"    {k}: {v}")
            break
    if not diag_ok:
        print(f"[2] 診断取得NG（最終応答）: code={last_code}")
        print(f"    {last_data}")
        return 1

    # オプション: DB をローカルから直接 ping（バックエンドと別経路）
    url = os.getenv("JAWSDB_URL")
    if url:
        try:
            from sqlalchemy import create_engine, text

            db_url = url
            if db_url.startswith("mysql://"):
                db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
            eng = create_engine(db_url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("\n[3] PyMySQL + SQLAlchemy 直接接続 → OK")
        except Exception as e:
            print(f"\n[3] PyMySQL 直接接続 → NG: {e}")
            return 1
    else:
        print("\n[3] JAWSDB_URL 未設定 — DB 直接テストをスキップ")

    print("\nすべて基本チェック完了。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
