#!/usr/bin/env python3
"""Scheduler — enqueue periodic maintenance jobs.

  cd backend && python -m jobs.scheduler
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("jobs.scheduler")


async def _tick():
    from config import get_settings
    from core import db
    from distributed_locks import distributed_lock
    from jobs import enqueue
    import jobs.handlers  # noqa: F401

    s = get_settings()
    if not getattr(s, "scheduler_enabled", True):
        logger.info("Scheduler disabled")
        return False

    # Prevent overlapping scheduler ticks across instances
    try:
        async with distributed_lock("scheduler:tick", ttl_seconds=55, prefix="sched"):
            now = time.time()
            # Inbox sync
            interval = getattr(s, "inbox_sync_interval_minutes", 15) * 60
            mailboxes = await db.mailboxes.find({"syncEnabled": True}, {"_id": 0, "id": 1, "organizationId": 1, "lastSuccessfulSyncAt": 1}).to_list(500)
            for mb in mailboxes:
                await enqueue(
                    "inbox_sync",
                    organization_id=mb["organizationId"],
                    payload={"mailboxId": mb["id"]},
                    idempotency_key=f"sync:{mb['id']}:{int(now // interval)}",
                )

            # Scheduled emails due
            from core import now_iso
            due = await db.outbound_emails.find(
                {"status": "scheduled", "scheduledFor": {"$lte": now_iso()}},
                {"_id": 0, "id": 1, "organizationId": 1},
            ).to_list(100)
            for doc in due:
                await enqueue(
                    "send_scheduled_email",
                    organization_id=doc["organizationId"],
                    payload={"emailId": doc["id"]},
                    idempotency_key=f"send:{doc['id']}",
                )

            # Integration health
            health_interval = getattr(s, "integration_health_interval_minutes", 60) * 60
            integrations = await db.integrations.find(
                {"status": {"$in": ["connected", "error"]}},
                {"_id": 0, "id": 1, "organizationId": 1, "provider": 1},
            ).to_list(200)
            for integ in integrations:
                await enqueue(
                    "integration_health",
                    organization_id=integ["organizationId"],
                    payload={"provider": integ["provider"]},
                    idempotency_key=f"health:{integ['organizationId']}:{integ['provider']}:{int(now // health_interval)}",
                )

            # Reconcile stuck sends
            await enqueue(
                "reconcile_sending",
                payload={},
                idempotency_key=f"reconcile:{int(now // (getattr(s, 'email_reconciliation_interval_minutes', 10) * 60))}",
            )
            await enqueue("cleanup_expired", payload={}, idempotency_key=f"cleanup:{int(now // 3600)}")
            # Optional alert webhook delivery (disabled unless ALERT_DELIVERY_ENABLED=true)
            try:
                from alerts_delivery import deliver_alerts, delivery_enabled
                if delivery_enabled():
                    result = await deliver_alerts(force=False)
                    if result.get("delivered"):
                        logger.info("Alert delivery ok codes=%s", result.get("codes"))
            except Exception:
                logger.exception("Alert delivery tick failed")
            logger.info("Scheduler tick enqueued mailboxes=%d due_emails=%d integrations=%d", len(mailboxes), len(due), len(integrations))
    except RuntimeError:
        logger.info("Scheduler tick skipped — lock held")
    return True


async def main():
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    from config import load_settings, get_settings
    from redis_client import ping_redis, redis_required_for_production
    load_settings()
    s = get_settings()
    if not getattr(s, "scheduler_enabled", False):
        logger.error("SCHEDULER_ENABLED is false — refusing to start scheduler process")
        raise SystemExit(1)
    rp = ping_redis()
    if not rp.get("ok") and (redis_required_for_production() or s.is_production):
        logger.error("Redis unavailable and required — scheduler cannot start: %s", rp)
        raise SystemExit(1)
    logger.info("Scheduler started redis=%s", "ok" if rp.get("ok") else "unavailable")
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("Scheduler tick failed")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
