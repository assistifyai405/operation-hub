"""Lightweight Redis heartbeats for worker and scheduler processes.

Stores only non-sensitive metadata (role, pid, timestamp). TTL-based stale detection.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

WORKER_KEY = "assistify:heartbeat:worker"
SCHEDULER_KEY = "assistify:heartbeat:scheduler"
DEFAULT_TTL_SECONDS = 90  # worker/scheduler should refresh more often than this


def _redis():
    from redis_client import get_redis
    return get_redis()


def beat(role: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS, extra: Optional[dict] = None) -> bool:
    """Write/refresh a heartbeat. Returns True if Redis accepted it."""
    key = WORKER_KEY if role == "worker" else SCHEDULER_KEY if role == "scheduler" else None
    if not key:
        return False
    r = _redis()
    if not r:
        return False
    payload = {
        "role": role,
        "ts": str(int(time.time())),
        "pid": str(os.getpid()),
    }
    if extra:
        for k, v in extra.items():
            if v is None:
                continue
            lk = str(k).lower()
            if any(x in lk for x in ("token", "secret", "password", "key", "credential")):
                continue
            payload[str(k)] = str(v)[:80]
    try:
        r.hset(key, mapping=payload)
        r.expire(key, max(15, int(ttl_seconds)))
        return True
    except Exception:
        return False


def read_status(role: str, *, stale_after_seconds: int = 75) -> dict[str, Any]:
    """Return heartbeat status for a role.

    status values: running | stale | unavailable | disabled
    (disabled is decided by the caller based on config flags.)
    """
    key = WORKER_KEY if role == "worker" else SCHEDULER_KEY if role == "scheduler" else None
    if not key:
        return {"status": "unavailable", "ageSeconds": None}
    r = _redis()
    if not r:
        return {"status": "unavailable", "ageSeconds": None, "error": "redis_unavailable"}
    try:
        data = r.hgetall(key) or {}
        if not data:
            return {"status": "unavailable", "ageSeconds": None}
        ts = int(data.get("ts") or 0)
        age = max(0, int(time.time()) - ts) if ts else None
        if age is None:
            return {"status": "unavailable", "ageSeconds": None}
        status = "running" if age <= stale_after_seconds else "stale"
        return {
            "status": status,
            "ageSeconds": age,
            "pid": data.get("pid"),
        }
    except Exception as e:
        return {"status": "unavailable", "ageSeconds": None, "error": str(e)[:80]}


def clear(role: str) -> None:
    key = WORKER_KEY if role == "worker" else SCHEDULER_KEY if role == "scheduler" else None
    if not key:
        return
    r = _redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
