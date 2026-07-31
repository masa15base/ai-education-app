#!/usr/bin/env python3
"""JawsDB 向け SQL マイグレーション実行（Homebrew MySQL 9 クライアント回避用）。

使い方:
  export JAWSDB_URL="$(heroku config:get JAWSDB_URL -a ai-edu-app-backend)"
  cd backend && . .venv/bin/activate
  python scripts/run_jawsdb_sql.py scripts/heroku_add_growth_columns.sql
  python scripts/run_jawsdb_sql.py scripts/heroku_add_character_growth_stats.sql

既に存在する列・テーブルはスキップして続行します。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import pymysql


SKIP_ERRNOS = {
    1060,  # Duplicate column name
    1050,  # Table already exists
    1061,  # Duplicate key name
}


def parse_jaws_url(url: str) -> dict:
    u = urlparse(url)
    if u.scheme not in ("mysql", "mysql+pymysql"):
        raise SystemExit(f"Unsupported scheme: {u.scheme}")
    return {
        "host": u.hostname or "127.0.0.1",
        "port": u.port or 3306,
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
        "database": (u.path or "/").lstrip("/") or None,
    }


def split_statements(sql: str) -> list[str]:
    # 単純分割（このリポジトリの migration SQL 向け）
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                parts.append(stmt)
            buf = []
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";").strip()
        if stmt:
            parts.append(stmt)
    return parts


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)

    sql_path = Path(sys.argv[1])
    if not sql_path.is_file():
        # backend/ から相対でも、リポジトリルートからでも動くように
        alt = Path(__file__).resolve().parent / sql_path.name
        if alt.is_file():
            sql_path = alt
        else:
            raise SystemExit(f"SQL file not found: {sys.argv[1]}")

    raw = os.environ.get("JAWSDB_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raise SystemExit("Set JAWSDB_URL (or DATABASE_URL) in the environment.")

    cfg = parse_jaws_url(raw)
    sql_text = sql_path.read_text(encoding="utf-8")
    statements = split_statements(sql_text)
    if not statements:
        raise SystemExit(f"No SQL statements in {sql_path}")

    print(f"Connecting to {cfg['host']}:{cfg['port']}/{cfg['database']} …")
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        autocommit=True,
    )
    ok = 0
    skipped = 0
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                preview = re.sub(r"\s+", " ", stmt)[:120]
                try:
                    cur.execute(stmt)
                    print(f"OK  {preview}")
                    ok += 1
                except pymysql.err.OperationalError as e:
                    errno = e.args[0] if e.args else None
                    if errno in SKIP_ERRNOS:
                        print(f"SKIP ({errno}) {preview}")
                        skipped += 1
                    else:
                        raise
                except pymysql.err.ProgrammingError as e:
                    errno = e.args[0] if e.args else None
                    if errno in SKIP_ERRNOS:
                        print(f"SKIP ({errno}) {preview}")
                        skipped += 1
                    else:
                        raise
    finally:
        conn.close()

    print(f"Done: {ok} applied, {skipped} skipped ({sql_path.name})")


if __name__ == "__main__":
    main()
