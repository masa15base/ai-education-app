from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from fastapi import HTTPException

from .bootstrap_env import load_backend_env

load_backend_env()

raw_url = os.getenv("JAWSDB_URL")
DATABASE_URL = raw_url
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

engine = None
SessionLocal = None
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=0,
        pool_recycle=280,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def disable_database() -> None:
    """起動時 DB 接続失敗時にメモリフォールバックへ切り替える。"""
    global engine, SessionLocal
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            pass
    engine = None
    SessionLocal = None


def get_db():
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured (set JAWSDB_URL)",
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional():
    """DB 未設定時は None（503 にしない）。"""
    if SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
