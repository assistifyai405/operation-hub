"""Per-workspace daily AI request limits (Sprint 28).

Enforcement is server-side only. Counters use Redis when available, else MongoDB.
Org context is bound via contextvars from authenticated request dependencies
(or explicitly in background jobs).
"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_ai_org_id: ContextVar[Optional[str]] = ContextVar("ai_org_id", default=None)

# In-memory fallback for tests / no Redis / no Mongo yet
_memory_counts: dict[str, int] = {}


def bind_ai_org(org_id: Optional[str]):
    """Bind the current workspace for AI usage accounting."""
    return _ai_org_id.set(org_id)


def reset_ai_org(token) -> None:
    _ai_org_id.reset(token)


def get_bound_ai_org() -> Optional[str]:
    return _ai_org_id.get()


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _counter_key(org_id: str, day: Optional[str] = None) -> str:
    return f"{org_id}:{day or _utc_day()}"


def clear_ai_usage_memory() -> None:
    """Test helper — clear in-memory / Redis / Mongo AI usage counters."""
    _memory_counts.clear()
    r = _redis()
    if r is not None:
        try:
            for k in list(r.scan_iter("assistify:ai-daily:*")):
                r.delete(k)
        except Exception:
            pass
    try:
        from pymongo import MongoClient
        from config import get_settings
        s = get_settings()
        client = MongoClient(s.mongo_url, serverSelectionTimeoutMS=1500)
        client[s.db_name]["ai_usage_daily"].delete_many({})
        client.close()
    except Exception:
        pass


async def get_ai_usage(org_id: str) -> dict:
    """Return {day, used, limit, remaining} for an organization."""
    from config import get_settings

    s = get_settings()
    limit = int(s.ai_daily_request_limit)
    day = _utc_day()
    used = await _read_count(org_id, day)
    remaining = max(0, limit - used) if limit > 0 else None
    return {
        "day": day,
        "used": used,
        "limit": limit if limit > 0 else None,
        "remaining": remaining,
        "unlimited": limit <= 0,
    }


async def enforce_ai_daily_limit(org_id: Optional[str] = None) -> None:
    """Increment usage and raise HTTP 429 when the daily workspace limit is exceeded.

    limit <= 0 disables enforcement (unlimited).
    """
    oid = org_id or get_bound_ai_org()
    if not oid:
        return

    from config import get_settings

    s = get_settings()
    limit = int(s.ai_daily_request_limit)
    if limit <= 0:
        return

    day = _utc_day()
    used_after = await _increment(oid, day)
    if used_after > limit:
        # Roll back the optimistic increment so the counter stays accurate
        await _decrement(oid, day)
        raise HTTPException(
            status_code=429,
            detail={
                "code": "ai_daily_limit",
                "message": (
                    "Daily AI request limit reached for this workspace. "
                    "Try again tomorrow, or ask an owner/admin to raise AI_DAILY_REQUEST_LIMIT."
                ),
                "limit": limit,
                "used": limit,
                "day": day,
            },
            headers={"Retry-After": "3600"},
        )


async def enforce_bound_ai_limit() -> None:
    """Enforce using the context-bound organization (no-op when unbound)."""
    await enforce_ai_daily_limit(get_bound_ai_org())


async def _read_count(org_id: str, day: str) -> int:
    r = _redis()
    if r is not None:
        try:
            val = r.get(f"assistify:ai-daily:{org_id}:{day}")
            if val is not None:
                return int(val)
        except Exception:
            pass
    try:
        from core import db
        doc = await db.ai_usage_daily.find_one(
            {"organizationId": org_id, "day": day},
            {"_id": 0, "count": 1},
        )
        if doc:
            return int(doc.get("count") or 0)
    except Exception:
        pass
    return int(_memory_counts.get(_counter_key(org_id, day), 0))


async def _increment(org_id: str, day: str) -> int:
    r = _redis()
    if r is not None:
        try:
            key = f"assistify:ai-daily:{org_id}:{day}"
            count = int(r.incr(key))
            if count == 1:
                r.expire(key, 60 * 60 * 36)  # ~1.5 days
            # Mirror to Mongo for ops visibility across restarts when Redis is primary
            try:
                from core import db
                await db.ai_usage_daily.update_one(
                    {"organizationId": org_id, "day": day},
                    {
                        "$set": {"count": count, "updatedAt": datetime.now(timezone.utc).isoformat()},
                        "$setOnInsert": {
                            "id": str(uuid.uuid4()),
                            "organizationId": org_id,
                            "day": day,
                            "createdAt": datetime.now(timezone.utc).isoformat(),
                        },
                    },
                    upsert=True,
                )
            except Exception:
                pass
            return count
        except Exception as e:
            logger.debug("AI usage Redis incr failed, falling back: %s", e)

    try:
        from core import db
        from pymongo import ReturnDocument
        doc = await db.ai_usage_daily.find_one_and_update(
            {"organizationId": org_id, "day": day},
            {
                "$inc": {"count": 1},
                "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()},
                "$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "organizationId": org_id,
                    "day": day,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int((doc or {}).get("count") or 1)
    except Exception as e:
        logger.debug("AI usage Mongo incr failed, using memory: %s", e)

    key = _counter_key(org_id, day)
    _memory_counts[key] = int(_memory_counts.get(key, 0)) + 1
    return _memory_counts[key]


async def _decrement(org_id: str, day: str) -> None:
    r = _redis()
    if r is not None:
        try:
            key = f"assistify:ai-daily:{org_id}:{day}"
            val = r.decr(key)
            if val is not None and int(val) < 0:
                r.set(key, 0)
        except Exception:
            pass
    try:
        from core import db
        await db.ai_usage_daily.update_one(
            {"organizationId": org_id, "day": day, "count": {"$gt": 0}},
            {"$inc": {"count": -1}, "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}},
        )
    except Exception:
        pass
    key = _counter_key(org_id, day)
    if key in _memory_counts:
        _memory_counts[key] = max(0, _memory_counts[key] - 1)


def _redis():
    try:
        from redis_client import get_redis
        return get_redis()
    except Exception:
        return None
