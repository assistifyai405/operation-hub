"""Stuck email reconciliation — never blindly resend confirmed provider messages."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from audit import write_audit
from core import db, now_iso

logger = logging.getLogger(__name__)

STALE_SENDING_MINUTES = 15


async def reconcile_stuck_emails(*, organization_id: str = None, stale_minutes: int = STALE_SENDING_MINUTES) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)).isoformat()
    q = {"status": "sending", "lastSendAttemptAt": {"$lt": cutoff}}
    if organization_id:
        q["organizationId"] = organization_id

    stuck = await db.outbound_emails.find(q, {"_id": 0}).to_list(200)
    marked_failed = 0
    marked_review = 0
    for doc in stuck:
        org_id = doc["organizationId"]
        # If provider already confirmed a message id, do not resend — needs human review
        if doc.get("providerMessageId") or doc.get("internetMessageId"):
            await db.outbound_emails.update_one(
                {"id": doc["id"], "organizationId": org_id, "status": "sending"},
                {"$set": {
                    "status": "needs_review",
                    "failureReason": "Send left in sending after provider acceptance — confirm in mailbox before retry",
                    "failureCode": "ambiguous_delivery",
                    "failureActionable": "Check the provider mailbox; do not retry until confirmed",
                    "updatedAt": now_iso(),
                }},
            )
            marked_review += 1
            await write_audit(
                org_id, "email_reconciliation",
                actor_id="system", actor_email="system",
                meta={"emailId": doc["id"], "decision": "needs_review", "reason": "provider_id_present"},
            )
        else:
            await db.outbound_emails.update_one(
                {"id": doc["id"], "organizationId": org_id, "status": "sending"},
                {"$set": {
                    "status": "failed",
                    "failureReason": "Send attempt timed out without provider confirmation — safe to retry",
                    "failureCode": "stale_sending",
                    "failureActionable": "Retry send when ready",
                    "failedAt": now_iso(),
                    "updatedAt": now_iso(),
                }},
            )
            marked_failed += 1
            await write_audit(
                org_id, "email_reconciliation",
                actor_id="system", actor_email="system",
                meta={"emailId": doc["id"], "decision": "failed_retryable", "reason": "stale_no_provider_id"},
            )

    # Count ambiguous states for ops
    amb_q = {"status": {"$in": ["needs_review", "delivery_unknown"]}}
    if organization_id:
        amb_q["organizationId"] = organization_id
    ambiguous = await db.outbound_emails.count_documents(amb_q)

    return {
        "scanned": len(stuck),
        "markedFailed": marked_failed,
        "markedNeedsReview": marked_review,
        "ambiguousCount": ambiguous,
    }


async def stuck_email_count(organization_id: str = None) -> int:
    q = {"status": {"$in": ["sending", "needs_review", "delivery_unknown"]}}
    if organization_id:
        q["organizationId"] = organization_id
    return await db.outbound_emails.count_documents(q)
