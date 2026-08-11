"""Lightweight Redis job queue with synchronous development mode.

Payloads contain IDs only — never OAuth tokens or secrets.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

QUEUE_KEY = "assistify:jobs:queue"
PROCESSING_KEY = "assistify:jobs:processing"
FAILED_KEY = "assistify:jobs:failed"
HANDLERS: Dict[str, Callable] = {}


def register(job_type: str):
    def deco(fn):
        HANDLERS[job_type] = fn
        return fn
    return deco


def _redis():
    from redis_client import get_redis
    return get_redis()


def _sync_mode() -> bool:
    try:
        from config import get_settings
        s = get_settings()
        if not getattr(s, "worker_enabled", False):
            return True
        if not (getattr(s, "redis_url", None) or "").strip():
            return True
        return False
    except Exception:
        return True


async def enqueue(
    job_type: str,
    *,
    organization_id: Optional[str] = None,
    payload: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
    request_id: Optional[str] = None,
    max_attempts: int = 5,
) -> dict:
    """Enqueue a job or run inline in sync mode. Payload must be ID-safe."""
    from core import db, now_iso

    safe_payload = dict(payload or {})
    # Strip anything that looks like a secret
    for k in list(safe_payload.keys()):
        lk = k.lower()
        if any(x in lk for x in ("token", "secret", "password", "credential", "authorization")):
            safe_payload.pop(k, None)

    job_id = str(uuid.uuid4())
    if idempotency_key:
        existing = await db.job_runs.find_one({"idempotencyKey": idempotency_key}, {"_id": 0})
        if existing and existing.get("status") in ("queued", "running", "succeeded"):
            return existing

    doc = {
        "id": job_id,
        "type": job_type,
        "organizationId": organization_id,
        "payload": safe_payload,
        "status": "queued",
        "attempts": 0,
        "maxAttempts": max_attempts,
        "requestId": request_id,
        "lastError": None,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "startedAt": None,
        "finishedAt": None,
    }
    # Omit null idempotencyKey so unique sparse indexes allow multiple unset jobs
    if idempotency_key:
        doc["idempotencyKey"] = idempotency_key
    try:
        await db.job_runs.insert_one(dict(doc))
    except Exception:
        if idempotency_key:
            existing = await db.job_runs.find_one({"idempotencyKey": idempotency_key}, {"_id": 0})
            if existing:
                return existing
        raise

    if _sync_mode():
        return await run_job(job_id)

    r = _redis()
    if not r:
        return await run_job(job_id)
    r.lpush(QUEUE_KEY, json.dumps({"jobId": job_id}))
    return doc


async def run_job(job_id: str) -> dict:
    from core import db, now_iso

    doc = await db.job_runs.find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise ValueError("Job not found")
    if doc.get("status") == "succeeded":
        return doc

    handler = HANDLERS.get(doc["type"])
    if not handler:
        await db.job_runs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "lastError": f"Unknown job type {doc['type']}", "updatedAt": now_iso(), "finishedAt": now_iso()}},
        )
        return await db.job_runs.find_one({"id": job_id}, {"_id": 0})

    await db.job_runs.update_one(
        {"id": job_id},
        {"$set": {"status": "running", "startedAt": now_iso(), "updatedAt": now_iso()}, "$inc": {"attempts": 1}},
    )
    try:
        result = await handler(doc)
        await db.job_runs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "succeeded",
                "result": _safe_result(result),
                "finishedAt": now_iso(),
                "updatedAt": now_iso(),
                "lastError": None,
            }},
        )
    except Exception as e:
        logger.exception("Job %s failed type=%s", job_id, doc.get("type"))
        attempts = (doc.get("attempts") or 0) + 1
        max_a = doc.get("maxAttempts") or 5
        status = "failed" if attempts >= max_a else "queued"
        await db.job_runs.update_one(
            {"id": job_id},
            {"$set": {
                "status": status,
                "lastError": str(e)[:500],
                "updatedAt": now_iso(),
                "finishedAt": now_iso() if status == "failed" else None,
            }},
        )
        if status == "queued":
            # re-queue with backoff hint
            r = _redis()
            if r and not _sync_mode():
                delay = min(300, 2 ** min(attempts, 8))
                r.lpush(QUEUE_KEY, json.dumps({"jobId": job_id, "notBefore": time.time() + delay}))
            elif _sync_mode():
                pass  # sync mode does not auto-retry inline
        elif status == "failed":
            r = _redis()
            if r:
                r.lpush(FAILED_KEY, job_id)
    return await db.job_runs.find_one({"id": job_id}, {"_id": 0})


def _safe_result(result: Any) -> Any:
    if result is None:
        return None
    if isinstance(result, dict):
        out = {}
        for k, v in result.items():
            lk = str(k).lower()
            if any(x in lk for x in ("token", "secret", "password", "credential")):
                continue
            out[k] = v if not isinstance(v, (bytes, bytearray)) else "<bytes>"
        return out
    return str(result)[:500]


async def process_one_from_queue() -> Optional[dict]:
    r = _redis()
    if not r:
        return None
    raw = r.rpop(QUEUE_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    not_before = data.get("notBefore") or 0
    if not_before and time.time() < not_before:
        r.lpush(QUEUE_KEY, raw)
        return None
    job_id = data.get("jobId")
    if not job_id:
        return None
    return await run_job(job_id)


async def failed_job_count() -> int:
    from core import db
    return await db.job_runs.count_documents({"status": "failed"})


async def retry_job(job_id: str, org_id: Optional[str] = None) -> dict:
    from core import db, now_iso
    q = {"id": job_id}
    if org_id:
        q["organizationId"] = org_id
    doc = await db.job_runs.find_one(q, {"_id": 0})
    if not doc:
        raise ValueError("Job not found")
    await db.job_runs.update_one(
        {"id": job_id},
        {"$set": {"status": "queued", "updatedAt": now_iso(), "lastError": None}},
    )
    if _sync_mode():
        return await run_job(job_id)
    r = _redis()
    if r:
        r.lpush(QUEUE_KEY, json.dumps({"jobId": job_id}))
    else:
        return await run_job(job_id)
    return await db.job_runs.find_one({"id": job_id}, {"_id": 0})
