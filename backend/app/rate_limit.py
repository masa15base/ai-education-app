"""プロセス内スライディングウィンドウによる簡易レート制限（ユーザー単位）。"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException

from .deps import get_current_uid


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, period_seconds: float) -> None:
        self.max_calls = max_calls
        self.period = period_seconds
        self._data: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """許可なら True、超過なら False。"""
        now = time.monotonic()
        with self._lock:
            dq = self._data[key]
            while dq and dq[0] < now - self.period:
                dq.popleft()
            if len(dq) >= self.max_calls:
                return False
            dq.append(now)
            return True


_preprocess_limiter = SlidingWindowLimiter(45, 60.0)
_generate_limiter = SlidingWindowLimiter(10, 60.0)
_chat_limiter = SlidingWindowLimiter(50, 60.0)


def require_preprocess_rate_limit(uid: str = Depends(get_current_uid)) -> str:
    if not _preprocess_limiter.hit(f"pre:{uid}"):
        raise HTTPException(
            status_code=429,
            detail="Too many preprocess requests. Please wait a minute and try again.",
        )
    return uid


def require_generate_rate_limit(uid: str = Depends(get_current_uid)) -> str:
    if not _generate_limiter.hit(f"gen:{uid}"):
        raise HTTPException(
            status_code=429,
            detail="Too many character generation requests. Please wait a minute.",
        )
    return uid


def require_chat_rate_limit(uid: str = Depends(get_current_uid)) -> str:
    if not _chat_limiter.hit(f"chat:{uid}"):
        raise HTTPException(
            status_code=429,
            detail="Too many chat messages. Please wait a moment.",
        )
    return uid
