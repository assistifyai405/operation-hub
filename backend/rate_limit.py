"""Rate limiting — Redis-backed in production, in-memory fallback for development."""
from __future__ import annotations

import time
from typing import Optional, Tuple

from fastapi import HTTPException

_rl_store: dict = {}  # kept for tests that clear it


def _redis():
    from redis_client import get_redis
    return get_redis()


def rate_limit(key: str, max_calls: int, window_s: int, *, retry_after: Optional[int] = None):
    """Raise HTTP 429 when over limit. Org/user-aware keys supplied by callers."""
    now = time.time()
    r = _redis()
    if r is not None:
        rk = f"assistify:rl:{key}"
        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(rk, 0, now - window_s)
            pipe.zcard(rk)
            pipe.zadd(rk, {str(now): now})
            pipe.expire(rk, window_s + 1)
            results = pipe.execute()
            count = int(results[1] or 0)
            if count >= max_calls:
                # undo add
                r.zrem(rk, str(now))
                ra = retry_after if retry_after is not None else window_s
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "rate_limited",
                        "message": "Too many requests. Please try again later.",
                        "retryAfter": ra,
                    },
                    headers={"Retry-After": str(ra)},
                )
            return
        except HTTPException:
            raise
        except Exception:
            # fall through to memory on redis errors
            pass

    calls = [t for t in _rl_store.get(key, []) if now - t < window_s]
    if len(calls) >= max_calls:
        ra = retry_after if retry_after is not None else window_s
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Too many requests. Please try again later.",
                "retryAfter": ra,
            },
            headers={"Retry-After": str(ra)},
        )
    calls.append(now)
    _rl_store[key] = calls


def check_rate_limit(key: str, max_calls: int, window_s: int) -> Tuple[bool, int]:
    """Return (allowed, remaining) without raising — for health/ops."""
    now = time.time()
    r = _redis()
    if r is not None:
        try:
            rk = f"assistify:rl:{key}"
            r.zremrangebyscore(rk, 0, now - window_s)
            count = int(r.zcard(rk) or 0)
            return count < max_calls, max(0, max_calls - count)
        except Exception:
            pass
    calls = [t for t in _rl_store.get(key, []) if now - t < window_s]
    return len(calls) < max_calls, max(0, max_calls - len(calls))
