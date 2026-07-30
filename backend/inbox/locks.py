"""Per-mailbox sync locking — Redis when available, in-process otherwise."""
from __future__ import annotations

from contextlib import asynccontextmanager

from distributed_locks import distributed_lock


@asynccontextmanager
async def mailbox_sync_lock(org_id: str, mailbox_id: str, *, timeout: float = 0.01):
    """Acquire exclusive sync lock or raise RuntimeError if busy."""
    try:
        async with distributed_lock(
            f"{org_id}:{mailbox_id}",
            ttl_seconds=300,
            wait_timeout=timeout,
            prefix="inbox-sync",
        ):
            yield
    except RuntimeError as e:
        raise RuntimeError("Sync already in progress for this mailbox") from e


def is_syncing(org_id: str, mailbox_id: str) -> bool:
    """Best-effort check — Redis GET or local lock state."""
    from distributed_locks import _redis, _local_locks
    key = f"assistify:inbox-sync:{org_id}:{mailbox_id}"
    r = _redis()
    if r is not None:
        try:
            return bool(r.get(key))
        except Exception:
            return False
    lock = _local_locks.get(key)
    return bool(lock and lock.locked())
