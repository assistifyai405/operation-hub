"""Per-mailbox sync locking (in-process; safe for single-worker API)."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict

_locks: Dict[str, asyncio.Lock] = {}
_holders: Dict[str, float] = {}
_meta_lock = asyncio.Lock()


def _key(org_id: str, mailbox_id: str) -> str:
    return f"{org_id}:{mailbox_id}"


@asynccontextmanager
async def mailbox_sync_lock(org_id: str, mailbox_id: str, *, timeout: float = 0.01):
    """Acquire exclusive sync lock or raise RuntimeError if busy."""
    key = _key(org_id, mailbox_id)
    async with _meta_lock:
        lock = _locks.setdefault(key, asyncio.Lock())
    if lock.locked():
        raise RuntimeError("Sync already in progress for this mailbox")
    await asyncio.wait_for(lock.acquire(), timeout=timeout)
    _holders[key] = time.time()
    try:
        yield
    finally:
        lock.release()
        _holders.pop(key, None)


def is_syncing(org_id: str, mailbox_id: str) -> bool:
    key = _key(org_id, mailbox_id)
    lock = _locks.get(key)
    return bool(lock and lock.locked())
