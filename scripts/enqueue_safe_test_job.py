#!/usr/bin/env python3
"""Enqueue a safe internal test job against a running async stack.

Uses Redis + Mongo directly (no external providers). Useful for Docker compose QA:

  docker compose exec backend python /app/../scripts/...  # or run from host with env

From repo root with local Redis/Mongo:

  REDIS_URL=redis://127.0.0.1:6379/0 MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=assistify \\
    python scripts/enqueue_safe_test_job.py

Modes:
  --mode noop   (default) succeed
  --mode fail   intentional failure for dead-letter QA
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("noop", "fail"), default="noop")
    parser.add_argument("--wait", type=float, default=8.0, help="Seconds to wait for worker to process")
    args = parser.parse_args()

    # Minimal env for settings
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("JWT_SECRET", "local-dev-secret-change-me-32chars!!")
    from dotenv import load_dotenv
    # Prefer existing process env / dotenv so DB_NAME matches the running worker.
    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env", override=False)

    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
    os.environ.setdefault("DB_NAME", "assistify")
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
    os.environ.setdefault("WORKER_ENABLED", "true")
    os.environ.setdefault("STORAGE_PROVIDER", "local")
    os.environ.setdefault("AI_PROVIDER", "openai")
    os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY") or "")
    print(f"using MONGO_URL={os.environ.get('MONGO_URL')} DB_NAME={os.environ.get('DB_NAME')} REDIS_URL={os.environ.get('REDIS_URL')}")

    from config import load_settings
    load_settings(strict=True)
    import jobs.handlers  # noqa: F401
    from jobs import enqueue, QUEUE_KEY, FAILED_KEY
    from redis_client import get_redis, ping_redis
    from core import db

    rp = ping_redis()
    if not rp.get("ok"):
        print("FAIL: Redis unavailable", rp.get("error"))
        return 1

    job_type = "test_noop" if args.mode == "noop" else "test_fail"
    key = f"s27-safe:{args.mode}:{uuid.uuid4().hex[:10]}"
    doc = await enqueue(
        job_type,
        organization_id=None,
        payload={"echo": "sprint27", "source": "enqueue_safe_test_job"},
        idempotency_key=key,
        max_attempts=2 if args.mode == "fail" else 3,
    )
    job_id = doc["id"]
    print(f"enqueued type={job_type} id={job_id} status={doc.get('status')}")

    deadline = time.time() + args.wait
    final = None
    while time.time() < deadline:
        final = await db.job_runs.find_one({"id": job_id}, {"_id": 0})
        if final and final.get("status") in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.25)

    r = get_redis()
    qdepth = int(r.llen(QUEUE_KEY) or 0) if r else -1
    fdepth = int(r.llen(FAILED_KEY) or 0) if r else -1

    if not final:
        print("FAIL: job not finished within wait window")
        return 1

    status = final.get("status")
    print(f"final status={status} attempts={final.get('attempts')} queueDepth={qdepth} failedDepth={fdepth}")
    err = final.get("lastError") or ""
    if "sk-" in err.lower() or "api_key" in err.lower():
        print("FAIL: error appears to contain secret material")
        return 1

    if args.mode == "noop" and status != "succeeded":
        print("FAIL: expected succeeded")
        return 1
    if args.mode == "fail" and status != "failed":
        print("FAIL: expected failed")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
