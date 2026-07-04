"""ローカルで JawsDB / MySQL 接続を試すスクリプト。認証情報は環境変数のみ。"""
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("JAWSDB_URL")
print("JAWSDB_URL set:", bool(url))

if not url:
    print("Set JAWSDB_URL in .env or the environment, then run again.")
    raise SystemExit(1)

# mysql://user:pass@host:port/db → SQLAlchemy で mysql+pymysql に変換
# Heroku JawsDB は mysql:// 形式。簡易チェックのみ。
if url.startswith("mysql://"):
    print("Tip: SQLAlchemy では mysql+pymysql:// に置換済み (app/db.py)。")

try:
    from sqlalchemy import create_engine

    db_url = url.replace("mysql://", "mysql+pymysql://", 1)
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT 1 AS ok").fetchone()
        print("DB Test Result:", row)
except Exception as e:
    print("Connection failed:", e)
    raise
