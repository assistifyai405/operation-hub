"""Distributed locks (Redis) with in-process fallback for single-worker development."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_local_locks: Dict[str, asyncio.Lock] = {}
_local_tokens: Dict[str, str] = {}
_meta = asyncio.Lock()

# Lua: release only if token matches
_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
else
  return 0
end
"""


def _redis():
    from redis_client import get_redis
    return get_redis()


@asynccontextmanager
async def distributed_lock(key: str, *, ttl_seconds: int = 120, wait_timeout: float = 0.05, prefix: str = "lock"):
    """Acquire exclusive lock. Raises RuntimeError if busy."""
    full = f"assistify:{prefix}:{key}"
    token = str(uuid.uuid4())
    r = _redis()
    if r is not None:
        ok = r.set(full, token, nx=True, ex=max(1, int(ttl_seconds)))
        if not ok:
            raise RuntimeError("Lock already held")
        try:
            yield token
        finally:
            try:
                r.eval(_RELEASE_LUA, 1, full, token)
            except Exception:
                logger.warning("Failed to release redis lock %s", full)
        return

    # In-memory fallback
    async with _meta:
        lock = _local_locks.setdefault(full, asyncio.Lock())
    if lock.locked():
        raise RuntimeError("Lock already held")
    await asyncio.wait_for(lock.acquire(), timeout=wait_timeout)
    _local_tokens[full] = token
    try:
        yield token
    finally:
        lock.release()
        _local_tokens.pop(full, None)


def try_acquire_sync(key: str, *, ttl_seconds: int = 60, prefix: str = "lock") -> Optional[str]:
    """Sync acquire; returns token or None."""
    full = f"assistify:{prefix}:{key}"
    token = str(uuid.uuid4())
    r = _redis()
    if r is not None:
        ok = r.set(full, token, nx=True, ex=max(1, int(ttl_seconds)))
        return token if ok else None
    # process-local sync fallback using token map only (best-effort)
    if full in _local_tokens:
        return None
    _local_tokens[full] = token
    return token


def release_sync(key: str, token: str, *, prefix: str = "lock") -> bool:
    full = f"assistify:{prefix}:{key}"
    r = _redis()
    if r is not None:
        try:
            return bool(r.eval(_RELEASE_LUA, 1, full, token))
        except Exception:
            return False
    if _local_tokens.get(full) == token:
        _local_tokens.pop(full, None)
        return True
    return False
