"""Redis client with safe development fallback."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client = None
_available: Optional[bool] = None


def redis_url() -> str:
    try:
        from config import get_settings
        s = get_settings()
        return (getattr(s, "redis_url", None) or "").strip()
    except Exception:
        import os
        return (os.environ.get("REDIS_URL") or "").strip()


def get_redis(force: bool = False):
    """Return sync Redis client or None when unavailable."""
    global _client, _available
    if _available is False and not force:
        return None
    if _client is not None and not force:
        return _client
    url = redis_url()
    if not url:
        _available = False
        return None
    try:
        import redis
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        _client = client
        _available = True
        return _client
    except Exception as e:
        logger.warning("Redis unavailable: %s", e)
        _available = False
        _client = None
        return None


def redis_required_for_production() -> bool:
    try:
        from config import get_settings
        s = get_settings()
        if not s.is_production:
            return bool(getattr(s, "require_redis", False))
        return bool(
            getattr(s, "require_redis", False)
            or getattr(s, "worker_enabled", False)
            or getattr(s, "scheduler_enabled", False)
        )
    except Exception:
        return False


def ping_redis() -> dict:
    url = redis_url()
    if not url:
        return {"configured": False, "ok": False, "error": "REDIS_URL not set"}
    try:
        r = get_redis(force=True)
        if not r:
            return {"configured": True, "ok": False, "error": "connection failed"}
        r.ping()
        return {"configured": True, "ok": True}
    except Exception as e:
        return {"configured": True, "ok": False, "error": str(e)[:120]}
